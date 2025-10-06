# backend/app/tests/conftest.py

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Dict, Any
from uuid import uuid4
from datetime import date, datetime
import random
import string

from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from ..main import app
from ..api.deps import get_db, get_current_user
from ..models import Base
from ..core.config import settings
from ..database import db_manager

# Import all models to ensure proper table creation
from ..models import (
    User,
    UserRole,
    SystemConfiguration,
    AcademicSession,
    Faculty,
    Department,
    Programme,
    Course,
    Student,
    CourseRegistration,
    Building,
    Room,
    RoomType,
    ConstraintCategory,
    ConstraintRule,
    ConfigurationConstraint,
    Staff,
    TimetableJob,
)


ASYNC_DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)

assert ASYNC_DATABASE_URL, "DATABASE_URL must be set in .env for testing"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for our test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create a test database engine WITHOUT creating or dropping tables."""
    engine = create_async_engine(ASYNC_DATABASE_URL, echo=False, poolclass=NullPool)

    # --- FIX: REMOVED TABLE CREATION AND DELETION ---
    # The original code created and dropped all tables, which is not desired.
    # Now, the fixture only provides an engine to the existing database.
    #
    # # Create all tables (REMOVED)
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)

    yield engine

    # # Drop all tables (REMOVED)
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session for each test."""
    async_session_maker = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )
    async with async_session_maker() as session:
        # Each test runs inside a transaction which is rolled back.
        # This isolates tests from each other without dropping tables.
        await session.begin()
        try:
            yield session
        finally:
            await session.rollback()


@pytest_asyncio.fixture
async def client(
    test_engine,
    db_session: AsyncSession,
    complete_test_data: Dict[str, Any],
) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an authenticated test HTTP client with database and user auth overrides.
    """
    db_manager.engine = test_engine
    db_manager.AsyncSessionLocal = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )
    db_manager._is_initialized = True

    test_user = complete_test_data["user"]

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as test_client:
        yield test_client

    # Clear overrides and reset manager state
    app.dependency_overrides.clear()
    db_manager._is_initialized = False
    db_manager.engine = None
    db_manager.AsyncSessionLocal = None


def generate_unique_string(prefix: str = "", length: int = 4) -> str:
    """Generate a short, unique string for test data to avoid constraint violations."""
    random_suffix = "".join(
        random.choices(string.ascii_lowercase + string.digits, k=length)
    )
    return f"{prefix}{int(datetime.now().timestamp() * 1000)}_{random_suffix}"


@pytest_asyncio.fixture
async def complete_test_data(db_session: AsyncSession) -> Dict[str, Any]:
    """
    Create a complete set of test data respecting all FK constraints.
    This data lives only within the test's transaction and is rolled back.
    """
    data = {}

    data["user"] = User(
        email=f"testuser_{generate_unique_string()}@example.com",
        first_name="Test",
        last_name="User",
    )
    db_session.add(data["user"])

    data["academic_session"] = AcademicSession(
        name=f"Test Session {generate_unique_string()}",
        semester_system="dual",
        start_date=date(2024, 9, 1),
        end_date=date(2025, 6, 30),
        slot_generation_mode="fixed",  # Add missing non-nullable field
    )
    db_session.add(data["academic_session"])

    # Create other necessary data...
    data["faculty_sci"] = Faculty(
        code=generate_unique_string("SCI-FAC"), name="Science Faculty"
    )
    data["faculty_art"] = Faculty(
        code=generate_unique_string("ART-FAC"), name="Arts Faculty"
    )
    db_session.add_all([data["faculty_sci"], data["faculty_art"]])
    await db_session.flush()

    data["department"] = Department(
        code=generate_unique_string("DPT"),
        name="Test Department",
        faculty_id=data["faculty_sci"].id,  # Link to the flushed faculty
    )
    db_session.add(data["department"])

    # Commit the setup data to make it visible to the database function
    await db_session.commit()

    # Refresh objects to ensure they are attached to the session for use in the test
    for key, obj in data.items():
        if not db_session.is_modified(obj) and obj in db_session:
            await db_session.refresh(obj)

    return data
