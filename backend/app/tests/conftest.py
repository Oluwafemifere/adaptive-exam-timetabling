# backend/app/tests/conftest.py

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Dict, Any
from uuid import uuid4
from datetime import datetime, date, time
import random
import string

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import IntegrityError

from ..main import app
from ..database import get_db
from ..models import Base
from ..config import get_settings

# Import all models to ensure proper table creation
from ..models.users import User, UserRole, SystemConfiguration
from ..models.academic import (
    AcademicSession,
    Faculty,
    Department,
    Programme,
    Course,
    Student,
    CourseRegistration,
)
from ..models.infrastructure import Building, Room, RoomType
from ..models.constraints import (
    ConstraintCategory,
    ConstraintRule,
    ConfigurationConstraint,
)
from ..models.scheduling import Exam, Staff, StaffUnavailability
from ..models.jobs import TimetableJob
from ..models.timetable_edits import TimetableEdit
from ..models.audit_logs import AuditLog
from ..models.file_uploads import FileUploadSession, UploadedFile

# Load settings from config.py (which reads .env)
settings = get_settings()
ASYNC_DATABASE_URL = settings.DATABASE_URL

assert ASYNC_DATABASE_URL, "DATABASE_URL must be set in .env"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create database engine using the existing database"""
    engine = create_async_engine(
        ASYNC_DATABASE_URL,
        echo=False,  # Set to True for SQL debugging
        poolclass=NullPool,
    )

    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name = 'exam_system'"
            )
        )
        schema_exists = result.scalar()
        assert schema_exists is not None, "exam_system schema does not exist"

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session with proper cleanup and isolation."""
    async_session = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )

    async with async_session() as session:
        # Start a transaction
        transaction = await session.begin()
        try:
            yield session
        finally:
            # Always rollback to ensure test isolation
            try:
                if not transaction.is_active:
                    # Transaction already closed, no need to rollback
                    pass
                else:
                    await transaction.rollback()
            except Exception:
                # Ignore rollback errors on already closed transactions
                pass


@pytest_asyncio.fixture
async def client(test_session) -> AsyncGenerator:
    """Create test HTTP client with database override."""

    async def override_get_db():
        try:
            yield test_session
        finally:
            # Session cleanup handled by test_session fixture
            pass

    app.dependency_overrides[get_db] = override_get_db

    from httpx import AsyncClient, ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def generate_unique_string(prefix: str = "", length: int = 8) -> str:
    """Generate unique string to avoid constraint violations"""
    random_suffix = "".join(
        random.choices(string.ascii_uppercase + string.digits, k=length)
    )
    return f"{prefix}_{random_suffix}_{uuid4().hex[:6]}"


@pytest_asyncio.fixture
async def complete_test_data(test_session: AsyncSession) -> Dict[str, Any]:
    """Create complete test data respecting all foreign key constraints with unique values."""

    # Generate unique identifiers to avoid constraint violations
    unique_suffix = uuid4().hex[:8]

    # Level 1: Independent entities
    user = User(
        id=uuid4(),
        email=f"test-{unique_suffix}@example.com",
        first_name="Test",
        last_name="User",
        is_active=True,
        is_superuser=False,
    )
    test_session.add(user)

    faculty = Faculty(
        id=uuid4(),
        code=generate_unique_string("FAC"),
        name=f"Test Faculty {unique_suffix}",
        is_active=True,
    )
    test_session.add(faculty)

    academic_session = AcademicSession(
        id=uuid4(),
        name=f"Test Session {unique_suffix}",
        semester_system="semester",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        is_active=True,
    )
    test_session.add(academic_session)

    building = Building(
        id=uuid4(),
        code=generate_unique_string("BLD"),
        name=f"Test Building {unique_suffix}",
        is_active=True,
    )
    test_session.add(building)

    constraint_category = ConstraintCategory(
        id=uuid4(),
        name=f"Test Constraints {unique_suffix}",
        description="Test constraint category",
        enforcement_layer="database",
    )
    test_session.add(constraint_category)

    user_role = UserRole(
        id=uuid4(),
        name=f"test_admin_{unique_suffix}",
        description="Test administrator role",
        permissions={"read": True, "write": True},
    )
    test_session.add(user_role)

    # Level 2: Entities with single dependencies
    department = Department(
        id=uuid4(),
        code=generate_unique_string("DEPT"),
        name=f"Test Department {unique_suffix}",
        faculty_id=faculty.id,
        is_active=True,
    )
    test_session.add(department)

    room_type = RoomType(
        id=uuid4(),
        name=f"Lecture Hall {unique_suffix}",
        description="Standard lecture hall",
        is_active=True,
    )
    test_session.add(room_type)

    constraint_rule = ConstraintRule(
        id=uuid4(),
        code=generate_unique_string("TEST_CONSTRAINT"),
        name=f"Test Constraint Rule {unique_suffix}",
        description="Test constraint for testing",
        constraint_type="hard",
        constraint_definition={"type": "test"},
        category_id=constraint_category.id,
        default_weight=1.0,
        is_active=True,
        is_configurable=True,
    )
    test_session.add(constraint_rule)

    await test_session.flush()  # Get IDs for Level 3

    # Level 2 continued
    room = Room(
        id=uuid4(),
        code=generate_unique_string("R"),
        name=f"Test Room {unique_suffix}",
        building_id=building.id,
        room_type_id=room_type.id,
        capacity=100,
        exam_capacity=80,
        floor_number=1,
        has_projector=True,
        has_ac=True,
        has_computers=False,
        is_active=True,
    )
    test_session.add(room)

    await test_session.flush()

    # Level 3: Entities with multiple dependencies
    system_configuration = SystemConfiguration(
        id=uuid4(),
        name=f"Test Config {unique_suffix}",
        description="Test configuration",
        created_by=user.id,
        is_default=False,
    )
    test_session.add(system_configuration)

    course = Course(
        id=uuid4(),
        code=generate_unique_string("CS"),
        title=f"Test Course {unique_suffix}",
        credit_units=3,
        course_level=200,
        semester=1,
        is_practical=False,
        morning_only=False,
        exam_duration_minutes=180,
        department_id=department.id,
        is_active=True,
    )
    test_session.add(course)

    programme = Programme(
        id=uuid4(),
        name=f"Test Programme {unique_suffix}",
        code=generate_unique_string("TPROG"),
        degree_type="bachelor",
        duration_years=4,
        department_id=department.id,
        is_active=True,
    )
    test_session.add(programme)

    await test_session.flush()  # Get IDs for Level 4

    # Level 4: Complex dependencies
    student = Student(
        id=uuid4(),
        matric_number=generate_unique_string("TST"),
        entry_year=2024,
        current_level=200,
        student_type="regular",
        programme_id=programme.id,
        is_active=True,
    )
    test_session.add(student)

    staff = Staff(
        id=uuid4(),
        staff_number=generate_unique_string("STF"),
        staff_type="academic",
        position="Lecturer",
        department_id=department.id,
        can_invigilate=True,
        max_daily_sessions=2,
        max_consecutive_sessions=2,
        is_active=True,
    )
    test_session.add(staff)

    await test_session.flush()

    # Level 5: Most complex dependencies
    course_registration = CourseRegistration(
        id=uuid4(),
        student_id=student.id,
        course_id=course.id,
        session_id=academic_session.id,
        registration_type="regular",
    )
    test_session.add(course_registration)

    configuration_constraint = ConfigurationConstraint(
        id=uuid4(),
        configuration_id=system_configuration.id,
        constraint_id=constraint_rule.id,
        custom_parameters={},
        weight=1.0,
        is_enabled=True,
    )
    test_session.add(configuration_constraint)

    timetable_job = TimetableJob(
        id=uuid4(),
        session_id=academic_session.id,
        configuration_id=system_configuration.id,
        initiated_by=user.id,
        status="queued",
        progress_percentage=0,
    )
    test_session.add(timetable_job)

    await test_session.flush()

    # Commit all changes
    await test_session.commit()

    return {
        "user": user,
        "faculty": faculty,
        "department": department,
        "academic_session": academic_session,
        "building": building,
        "room_type": room_type,
        "room": room,
        "constraint_category": constraint_category,
        "constraint_rule": constraint_rule,
        "system_configuration": system_configuration,
        "course": course,
        "programme": programme,
        "student": student,
        "staff": staff,
        "course_registration": course_registration,
        "configuration_constraint": configuration_constraint,
        "timetable_job": timetable_job,
        "user_role": user_role,
    }


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for session scope."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# Simplified fixture for backward compatibility
@pytest_asyncio.fixture
async def setup_test_data(complete_test_data):
    """Simplified interface to complete test data for backward compatibility."""
    return {
        "user": complete_test_data["user"],
        "config": complete_test_data["system_configuration"],
        "session": complete_test_data["academic_session"],
        "exam": complete_test_data["exam"],
    }
