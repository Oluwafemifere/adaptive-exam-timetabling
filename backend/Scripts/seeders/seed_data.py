#!/usr/bin/env python3

# backend/Scripts/seeders/seed_data.py

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional, Any, Type, Dict, TYPE_CHECKING, List, Union, cast as tycast
from datetime import datetime, date, time
import argparse
from dotenv import load_dotenv

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select, cast
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import ARRAY, TEXT
from app.database import init_db

# Import from the backend app
from app.database import db_manager
from app.models import (
    User,
    UserRole,
    UserRoleAssignment,
    Building,
    RoomType,
    Room,
    AcademicSession,
    Faculty,
    Department,
    Programme,
    ConstraintCategory,
    ConstraintRule,
    Course,
    Student,
    CourseRegistration,
    Exam,
)

# Conditional imports
if TYPE_CHECKING:
    from app.services.data_validation import (
        CSVProcessor,
        DataMapper,
        DataIntegrityChecker,
    )
else:
    try:
        from app.services.data_validation import (
            CSVProcessor,
            DataMapper,
            DataIntegrityChecker,
        )
    except ImportError as e:
        print(f"Warning: Could not import validation services: {e}")
        CSVProcessor = None
        DataMapper = None
        DataIntegrityChecker = None

# Load environment variables from backend/.env
env_path = BACKEND_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded environment from: {env_path}")
else:
    print(f"Environment file not found at: {env_path}")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class EnhancedDatabaseSeeder:
    """
    Enhanced database seeder that integrates with the data validation services
    and works with Alembic migrations. Handles both CSV imports and structured seeding.
    """

    def __init__(self, database_url: Optional[str] = None) -> None:
        # Use environment variable for database URL
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is not set")

        if CSVProcessor is not None:
            self.csv_processor = CSVProcessor()
            self._setup_csv_schemas()
        else:
            self.csv_processor = None
            logger.warning(
                "CSV processing not available - validation services not imported"
            )

    def _setup_csv_schemas(self) -> None:
        """Setup CSV processing schemas for different entity types"""
        if not self.csv_processor:
            return

        # Academic sessions schema
        self.csv_processor.register_schema(
            "academic_sessions",
            {
                "required_columns": [
                    "name",
                    "start_date",
                    "end_date",
                    "semester_system",
                ],
                "column_mappings": {
                    "session_name": "name",
                    "start": "start_date",
                    "end": "end_date",
                },
                "transformers": {
                    "start_date": lambda x: date.fromisoformat(str(x)) if x else None,
                    "end_date": lambda x: date.fromisoformat(str(x)) if x else None,
                },
            },
        )

        # Faculties schema
        self.csv_processor.register_schema(
            "faculties",
            {
                "required_columns": ["name", "code"],
                "column_mappings": {"faculty_name": "name", "faculty_code": "code"},
                "transformers": {
                    "code": lambda x: str(x).upper(),
                    "name": lambda x: str(x).strip(),
                },
            },
        )

        # Departments schema
        self.csv_processor.register_schema(
            "departments",
            {
                "required_columns": ["name", "code", "faculty_code"],
                "column_mappings": {
                    "department_name": "name",
                    "department_code": "code",
                    "parent_faculty": "faculty_code",
                },
                "transformers": {
                    "code": lambda x: str(x).upper(),
                    "faculty_code": lambda x: str(x).upper(),
                    "name": lambda x: str(x).strip(),
                },
            },
        )

        # Students schema
        self.csv_processor.register_schema(
            "students",
            {
                "required_columns": ["matric_number", "programme_code", "entry_year"],
                "column_mappings": {
                    "matric": "matric_number",
                    "program": "programme_code",
                },
                "transformers": {
                    "entry_year": lambda x: int(x) if x else None,
                    "matric_number": lambda x: str(x).upper().strip(),
                },
            },
        )

        # Courses schema
        self.csv_processor.register_schema(
            "courses",
            {
                "required_columns": [
                    "code",
                    "title",
                    "credit_units",
                    "department_code",
                ],
                "column_mappings": {
                    "course_code": "code",
                    "course_title": "title",
                    "credits": "credit_units",
                    "dept_code": "department_code",
                },
                "transformers": {
                    "code": lambda x: str(x).upper().strip(),
                    "credit_units": lambda x: int(x) if x else 3,
                    "department_code": lambda x: str(x).upper().strip(),
                },
            },
        )

        logger.info("CSV schemas configured for data validation")

    async def seed_all(
        self, drop_existing: bool = False, sample_data: bool = True
    ) -> None:
        """Main seeding method with comprehensive error handling"""
        logger.info("🚀 Starting database seeding with Alembic integration...")

        await init_db(database_url=self.database_url, create_tables=False)
        logger.info("✅ Database initialized")
        # Debug: Print the database URL being used
        logger.info(f"🔍 Using database URL: {self.database_url}")

        # Seed in dependency order (respecting foreign key constraints)
        await self._seed_users_and_roles()
        await self._seed_infrastructure()
        await self._seed_academic_structure()
        await self._seed_constraint_system()
        # await self._seed_time_slots()

        if sample_data:
            await self._seed_sample_data()

        logger.info("✅ Database seeding completed successfully!")

    async def import_csv_data(self, file_path: str, entity_type: str) -> Dict[str, Any]:
        """Import data from CSV file with validation"""
        if not self.csv_processor:
            raise ValueError("CSV processing not available")

        logger.info(f"📁 Importing {entity_type} data from {file_path}")

        try:
            # Process the CSV file
            processed_data = self.csv_processor.process_csv_file(file_path, entity_type)

            # Validate the processed data
            validation_results = await self._validate_csv_data(
                processed_data, entity_type
            )

            if validation_results.get("errors"):
                logger.error(f"❌ Validation failed: {validation_results['errors']}")
                return {"success": False, "errors": validation_results["errors"]}

            # Import the validated data
            import_results = await self._import_validated_data(
                processed_data, entity_type
            )

            logger.info(
                f"✅ Successfully imported {import_results.get('count', 0)} {entity_type} records"
            )
            return {"success": True, "count": import_results.get("count", 0)}

        except Exception as e:
            logger.error(f"❌ Failed to import {entity_type} data: {e}")
            return {"success": False, "error": str(e)}

    async def _validate_csv_data(
        self, data: Union[List[Dict], Dict[str, Any]], entity_type: str
    ) -> Dict[str, Any]:
        """Validate CSV data before import"""
        if isinstance(data, dict) and "data" in data:
            data_to_validate = data["data"]
        else:
            data_to_validate = data

        # normalize to list[dict]
        if isinstance(data_to_validate, dict):
            data_list: List[Dict[str, Any]] = [data_to_validate]
        else:
            data_list = data_to_validate  # type: ignore[assignment]

        try:
            async with db_manager.get_db_transaction() as session:
                # session.sync_session exists on AsyncSession; tell static checker it's a Session
                sync_session: Session = tycast(
                    Session, getattr(session, "sync_session")
                )
                checker = DataIntegrityChecker(sync_session)
                result = checker.check_integrity({entity_type: data_list})

                errors = [
                    f"{error.entity_type} {error.record_id}: {error.message}"
                    for error in result.errors
                ]

                return {"errors": errors}
        except Exception as e:
            logger.error(f"Error during validation: {e}")
            return {"errors": [f"Validation error: {str(e)}"]}

    async def _import_validated_data(
        self, data: Union[List[Dict], Dict[str, Any]], entity_type: str
    ) -> Dict[str, Any]:
        """Import validated data into the database"""
        if isinstance(data, dict) and "data" in data:
            data_to_import = data["data"]
        else:
            data_to_import = data

        # normalize to list[dict]
        if isinstance(data_to_import, dict):
            data_list: List[Dict[str, Any]] = [data_to_import]
        else:
            data_list = data_to_import  # type: ignore[assignment]

        async with db_manager.get_db_transaction() as session:
            count = 0

            if entity_type == "faculties":
                count = await self._import_faculties(session, data_list)
            elif entity_type == "departments":
                count = await self._import_departments(session, data_list)
            elif entity_type == "students":
                count = await self._import_students(session, data_list)
            elif entity_type == "courses":
                count = await self._import_courses(session, data_list)
            elif entity_type == "academic_sessions":
                count = await self._import_academic_sessions(session, data_list)
            else:
                raise ValueError(f"Unsupported entity type: {entity_type}")

            return {"count": count}

    async def _import_faculties(self, session, data: List[Dict]) -> int:
        """Import faculty records"""
        count = 0
        for record in data:
            existing = (
                (
                    await session.execute(
                        select(Faculty).where(Faculty.code == record["code"])
                    )
                )
                .scalars()
                .first()
            )

            if not existing:
                faculty = Faculty(
                    code=record["code"],
                    name=record["name"],
                    is_active=record.get("is_active", True),
                )
                session.add(faculty)
                count += 1
            else:
                logger.debug(f"Faculty {record['code']} already exists, skipping")

        return count

    async def _import_departments(self, session, data: List[Dict]) -> int:
        """Import department records"""
        count = 0
        for record in data:
            # Find the parent faculty
            faculty = (
                (
                    await session.execute(
                        select(Faculty).where(Faculty.code == record["faculty_code"])
                    )
                )
                .scalars()
                .first()
            )

            if not faculty:
                logger.error(
                    f"Faculty {record['faculty_code']} not found for department {record['code']}"
                )
                continue

            existing = (
                (
                    await session.execute(
                        select(Department).where(
                            Department.code == record["code"],
                            Department.faculty_id == faculty.id,
                        )
                    )
                )
                .scalars()
                .first()
            )

            if not existing:
                department = Department(
                    code=record["code"],
                    name=record["name"],
                    faculty_id=faculty.id,
                    is_active=record.get("is_active", True),
                )
                session.add(department)
                count += 1
            else:
                logger.debug(f"Department {record['code']} already exists, skipping")

        return count

    async def _import_students(self, session, data: List[Dict]) -> int:
        """Import student records"""
        count = 0
        for record in data:
            # Find the programme
            programme = (
                (
                    await session.execute(
                        select(Programme).where(
                            Programme.code == record["programme_code"]
                        )
                    )
                )
                .scalars()
                .first()
            )

            if not programme:
                logger.error(
                    f"Programme {record['programme_code']} not found for student {record['matric_number']}"
                )
                continue

            existing = (
                (
                    await session.execute(
                        select(Student).where(
                            Student.matric_number == record["matric_number"]
                        )
                    )
                )
                .scalars()
                .first()
            )

            if not existing:
                student = Student(
                    matric_number=record["matric_number"],
                    entry_year=record["entry_year"],
                    current_level=record.get("current_level", 100),
                    student_type=record.get("student_type", "regular"),
                    special_needs=cast(record.get("special_needs", []), ARRAY(TEXT)),
                    programme_id=programme.id,
                    is_active=record.get("is_active", True),
                )
                session.add(student)
                count += 1
            else:
                logger.debug(
                    f"Student {record['matric_number']} already exists, skipping"
                )

        return count

    async def _import_courses(self, session, data: List[Dict]) -> int:
        """Import course records"""
        count = 0
        for record in data:
            # Find the department
            department = (
                (
                    await session.execute(
                        select(Department).where(
                            Department.code == record["department_code"]
                        )
                    )
                )
                .scalars()
                .first()
            )

            if not department:
                logger.error(
                    f"Department {record['department_code']} not found for course {record['code']}"
                )
                continue

            existing = (
                (
                    await session.execute(
                        select(Course).where(Course.code == record["code"])
                    )
                )
                .scalars()
                .first()
            )

            if not existing:
                course = Course(
                    code=record["code"],
                    title=record["title"],
                    credit_units=record["credit_units"],
                    course_level=record.get("course_level", 100),
                    semester=record.get("semester", 1),
                    is_practical=record.get("is_practical", False),
                    morning_only=record.get("morning_only", False),
                    exam_duration_minutes=record.get("exam_duration_minutes", 180),
                    department_id=department.id,
                    is_active=record.get("is_active", True),
                )
                session.add(course)
                count += 1
            else:
                logger.debug(f"Course {record['code']} already exists, skipping")

        return count

    async def _import_academic_sessions(self, session, data: List[Dict]) -> int:
        """Import academic session records"""
        count = 0
        for record in data:
            existing = (
                (
                    await session.execute(
                        select(AcademicSession).where(
                            AcademicSession.name == record["name"]
                        )
                    )
                )
                .scalars()
                .first()
            )

            if not existing:
                session_obj = AcademicSession(
                    name=record["name"],
                    semester_system=record.get("semester_system", "semester"),
                    start_date=record["start_date"],
                    end_date=record["end_date"],
                    is_active=record.get("is_active", False),
                )
                session.add(session_obj)
                count += 1
            else:
                logger.debug(
                    f"Academic session {record['name']} already exists, skipping"
                )

        return count

    async def _seed_users_and_roles(self) -> None:
        """Seed user roles and admin user with enhanced error handling"""
        async with db_manager.get_db_transaction() as session:
            logger.info("👥 Seeding users and roles...")

            # Define roles to seed
            roles_def = [
                ("super_admin", "System Super Admin", {"*": ["*"]}),
                ("admin", "Administrator", {"academic": ["*"], "scheduling": ["*"]}),
                (
                    "dean",
                    "Faculty Dean",
                    {"academic": ["read"], "scheduling": ["read"]},
                ),
                (
                    "hod",
                    "Head of Department",
                    {"academic": ["read"], "scheduling": ["read"]},
                ),
                (
                    "scheduler",
                    "Scheduler",
                    {"scheduling": ["create", "read", "update"]},
                ),
                ("staff", "Staff", {"academic": ["read"]}),
            ]

            # Insert roles only if they don't already exist
            roles_created = 0
            for name, desc, perms in roles_def:
                result = await session.execute(
                    select(UserRole).where(UserRole.name == name)
                )
                existing = result.scalar_one_or_none()

                if not existing:
                    role = UserRole(name=name, description=desc, permissions=perms)
                    session.add(role)
                    roles_created += 1
                    logger.debug(f"Created role: {name}")
                else:
                    logger.debug(f"Role '{name}' already exists, skipping.")

            await session.flush()

            # Create admin user if not exists
            result = await session.execute(
                select(User).where(User.email == "admin@baze.edu.ng")
            )
            admin_user = result.scalar_one_or_none()

            if not admin_user:
                from app.core.security import hash_password

                admin_user = User(
                    email="admin@baze.edu.ng",
                    first_name="System",
                    last_name="Administrator",
                    password_hash=hash_password("admin123"),
                    is_active=True,
                    is_superuser=True,
                )
                session.add(admin_user)
                await session.flush()
                logger.info("Created admin user: admin@baze.edu.ng")

            # Ensure super_admin role assigned
            result = await session.execute(
                select(UserRole).where(UserRole.name == "super_admin")
            )
            super_role = result.scalar_one()

            # Check existing assignment
            assign_query = select(UserRoleAssignment).where(
                UserRoleAssignment.user_id == admin_user.id,
                UserRoleAssignment.role_id == super_role.id,
            )
            assignment = (await session.execute(assign_query)).scalar_one_or_none()

            if not assignment:
                session.add(
                    UserRoleAssignment(user_id=admin_user.id, role_id=super_role.id)
                )
                logger.info("Assigned super_admin role to admin user.")

            logger.info(f"✓ Users and roles seeded ({roles_created} new roles)")

    async def _seed_infrastructure(self) -> None:
        """Seed buildings, room types, and rooms with enhanced validation"""
        async with db_manager.get_db_transaction() as session:
            logger.info("🏢 Seeding infrastructure...")

            # Room types
            room_types_data = [
                ("Lecture Hall", "Large lecture hall for exams"),
                ("Classroom", "Regular classroom"),
                ("Computer Lab", "Computer laboratory"),
                ("Laboratory", "Science laboratory"),
                ("Auditorium", "Large auditorium"),
                ("Seminar Room", "Small seminar room"),
                ("Workshop", "Practical workshop space"),
                ("Conference Room", "Meeting/conference room"),
            ]

            room_types = {}
            room_types_created = 0
            for name, desc in room_types_data:
                existing = (
                    (
                        await session.execute(
                            select(RoomType).where(RoomType.name == name)
                        )
                    )
                    .scalars()
                    .first()
                )

                if not existing:
                    rt = RoomType(name=name, description=desc, is_active=True)
                    session.add(rt)
                    await session.flush()
                    room_types[name] = rt
                    room_types_created += 1
                else:
                    room_types[name] = existing

            # Buildings
            buildings_data = [
                ("Engineering Block", "ENG"),
                ("Science Block", "SCI"),
                ("Management Block", "MGT"),
                ("Law Block", "LAW"),
                ("Medical Block", "MED"),
                ("Arts Block", "ART"),
            ]

            buildings = {}
            buildings_created = 0
            for bname, bcode in buildings_data:
                existing = (
                    (
                        await session.execute(
                            select(Building).where(Building.code == bcode)
                        )
                    )
                    .scalars()
                    .first()
                )

                if not existing:
                    b = Building(name=bname, code=bcode, is_active=True)
                    session.add(b)
                    await session.flush()
                    buildings[bcode] = b
                    buildings_created += 1
                else:
                    buildings[bcode] = existing

            # Rooms with more realistic configurations
            room_configs = [
                ("ENG", "ENG01", "Engineering Room 1", 100, 70, "Classroom"),
                ("ENG", "ENG02", "Engineering Room 2", 80, 60, "Classroom"),
                ("ENG", "ENG03", "Engineering Lab 1", 50, 35, "Computer Lab"),
                ("ENG", "ENG04", "Engineering Workshop", 40, 30, "Workshop"),
                ("SCI", "SCI01", "Science Hall 1", 150, 100, "Lecture Hall"),
                ("SCI", "SCI02", "Science Hall 2", 100, 75, "Lecture Hall"),
                ("SCI", "SCI03", "Physics Lab", 30, 20, "Laboratory"),
                ("SCI", "SCI04", "Chemistry Lab", 35, 25, "Laboratory"),
                ("MGT", "MGT01", "Management Hall", 200, 150, "Auditorium"),
                ("MGT", "MGT02", "Business Classroom", 60, 45, "Classroom"),
                ("LAW", "LAW01", "Moot Court", 80, 60, "Auditorium"),
                ("MED", "MED01", "Anatomy Theatre", 100, 75, "Lecture Hall"),
                ("ART", "ART01", "Arts Studio", 40, 30, "Workshop"),
            ]

            rooms_created = 0
            for bcode, code, name, cap, exam_cap, room_type_name in room_configs:
                if bcode not in buildings:
                    continue

                existing = (
                    (await session.execute(select(Room).where(Room.code == code)))
                    .scalars()
                    .first()
                )

                if not existing:
                    room_type = room_types.get(room_type_name, room_types["Classroom"])
                    room = Room(
                        code=code,
                        name=name,
                        capacity=cap,
                        exam_capacity=exam_cap,
                        building_id=buildings[bcode].id,
                        room_type_id=room_type.id,
                        has_ac=True,
                        has_projector=True,
                        has_computers=(room_type_name == "Computer Lab"),
                        is_active=True,
                    )
                    session.add(room)
                    rooms_created += 1

            logger.info(
                f"✓ Infrastructure seeded: {buildings_created} buildings, {room_types_created} room types, {rooms_created} rooms"
            )

    async def _seed_academic_structure(self) -> None:
        """Seed academic sessions, faculties, departments, and programmes"""
        async with db_manager.get_db_transaction() as session:
            logger.info("🎓 Seeding academic structure...")

            # Academic sessions
            current_year = datetime.now().year
            sessions_data = [
                (
                    f"{current_year-1}/{current_year}",
                    date(current_year - 1, 9, 1),
                    date(current_year, 8, 31),
                    False,
                ),
                (
                    f"{current_year}/{current_year+1}",
                    date(current_year, 9, 1),
                    date(current_year + 1, 8, 31),
                    True,
                ),
                (
                    f"{current_year+1}/{current_year+2}",
                    date(current_year + 1, 9, 1),
                    date(current_year + 2, 8, 31),
                    False,
                ),
            ]

            sessions_created = 0
            for name, start_date, end_date, is_active in sessions_data:
                existing = (
                    (
                        await session.execute(
                            select(AcademicSession).where(AcademicSession.name == name)
                        )
                    )
                    .scalars()
                    .first()
                )

                if not existing:
                    session_obj = AcademicSession(
                        name=name,
                        start_date=start_date,
                        end_date=end_date,
                        semester_system="semester",
                        is_active=is_active,
                    )
                    session.add(session_obj)
                    sessions_created += 1

            await session.flush()

            # Faculties
            faculties_data = [
                ("Engineering", "ENG"),
                ("Science", "SCI"),
                ("Management & Social Sciences", "MGT"),
                ("Law", "LAW"),
                ("Medicine", "MED"),
                ("Arts", "ART"),
            ]

            faculties = []
            faculties_created = 0
            for name, code in faculties_data:
                existing = (
                    (await session.execute(select(Faculty).where(Faculty.code == code)))
                    .scalars()
                    .first()
                )

                if not existing:
                    faculty = Faculty(name=name, code=code, is_active=True)
                    session.add(faculty)
                    await session.flush()
                    faculties.append(faculty)
                    faculties_created += 1
                else:
                    faculties.append(existing)

            # Departments
            departments_data = [
                ("Computer Engineering", "CPE", "ENG"),
                ("Electrical Engineering", "EEE", "ENG"),
                ("Civil Engineering", "CVE", "ENG"),
                ("Computer Science", "CSC", "SCI"),
                ("Mathematics", "MTH", "SCI"),
                ("Physics", "PHY", "SCI"),
                ("Business Administration", "BUS", "MGT"),
                ("Accounting", "ACC", "MGT"),
                ("Economics", "ECO", "MGT"),
                ("Law", "LAW", "LAW"),
                ("Medicine", "MED", "MED"),
                ("English", "ENG", "ART"),
                ("History", "HIS", "ART"),
            ]

            departments = []
            departments_created = 0
            for name, code, faculty_code in departments_data:
                # Find the faculty object
                parent_faculty: Optional[Faculty] = next(
                    (f for f in faculties if f.code == faculty_code), None
                )
                if not parent_faculty:
                    continue

                existing = (
                    (
                        await session.execute(
                            select(Department).where(
                                Department.code == code,
                                Department.faculty_id == parent_faculty.id,
                            )
                        )
                    )
                    .scalars()
                    .first()
                )

                if not existing:
                    dept = Department(
                        name=name,
                        code=code,
                        faculty_id=parent_faculty.id,
                        is_active=True,
                    )
                    session.add(dept)
                    await session.flush()
                    departments.append(dept)
                    departments_created += 1
                else:
                    departments.append(existing)

            # Programmes
            programmes_data = [
                ("B.Eng Computer Engineering", "BCPE", "CPE", "undergraduate", 5),
                ("B.Eng Electrical Engineering", "BEEE", "EEE", "undergraduate", 5),
                ("B.Eng Civil Engineering", "BCVE", "CVE", "undergraduate", 5),
                ("B.Sc Computer Science", "BCSC", "CSC", "undergraduate", 4),
                ("B.Sc Mathematics", "BMTH", "MTH", "undergraduate", 4),
                ("B.Sc Physics", "BPHY", "PHY", "undergraduate", 4),
                ("B.Sc Business Administration", "BBUS", "BUS", "undergraduate", 4),
                ("B.Sc Accounting", "BACC", "ACC", "undergraduate", 4),
                ("B.Sc Economics", "BECO", "ECO", "undergraduate", 4),
                ("LL.B Law", "LLB", "LAW", "undergraduate", 5),
                ("MBBS Medicine", "MBBS", "MED", "undergraduate", 6),
                ("B.A English", "BAENG", "ENG", "undergraduate", 4),
                ("B.A History", "BAHIS", "HIS", "undergraduate", 4),
            ]

            programmes_created = 0
            for name, code, dept_code, degree_type, duration in programmes_data:
                # Find the department object
                department = next((d for d in departments if d.code == dept_code), None)
                if not department:
                    continue

                existing = (
                    (
                        await session.execute(
                            select(Programme).where(Programme.code == code)
                        )
                    )
                    .scalars()
                    .first()
                )

                if not existing:
                    programme = Programme(
                        name=name,
                        code=code,
                        department_id=department.id,
                        degree_type=degree_type,
                        duration_years=duration,
                        is_active=True,
                    )
                    session.add(programme)
                    programmes_created += 1

            logger.info(
                f"✓ Academic structure seeded: {sessions_created} sessions, {faculties_created} faculties, {departments_created} departments, {programmes_created} programmes"
            )

    async def _seed_constraint_system(self) -> None:
        """Seed constraint categories and rules"""
        async with db_manager.get_db_transaction() as session:
            logger.info("⚙️ Seeding constraint system...")

            # Skip if models don't exist
            try:
                # Constraint categories
                categories_data = [
                    ("Hard Constraints", "Must be satisfied", "CP_SAT"),
                    ("Soft Constraints", "Preferences to optimize", "GA"),
                ]

                categories = []
                categories_created = 0
                for name, desc, layer in categories_data:
                    existing_cat = (
                        (
                            await session.execute(
                                select(ConstraintCategory).where(
                                    ConstraintCategory.name == name
                                )
                            )
                        )
                        .scalars()
                        .first()
                    )

                    if not existing_cat:
                        category = ConstraintCategory(
                            name=name, description=desc, enforcement_layer=layer
                        )
                        session.add(category)
                        await session.flush()
                        categories.append(category)
                        categories_created += 1
                    else:
                        categories.append(existing_cat)

                # Constraint rules
                hard_category = next(
                    (c for c in categories if c.name == "Hard Constraints"), None
                )
                if hard_category:
                    rules_data = [
                        (
                            "NO_STUDENT_CONFLICT",
                            "No Student Conflicts",
                            "hard",
                            1.0,
                            {"type": "no_overlap", "scope": "student"},
                        ),
                        (
                            "ROOM_CAPACITY",
                            "Room Capacity",
                            "soft",
                            1.0,
                            {"type": "capacity_check", "scope": "room"},
                        ),
                        (
                            "TIME_AVAILABILITY",
                            "Time Slot Availability",
                            "hard",
                            1.0,
                            {"type": "availability_check", "scope": "timeslot"},
                        ),
                        (
                            "EXAM_DISTRIBUTION",
                            "Exam Distribution",
                            "soft",
                            0.8,
                            {"type": "distribution", "scope": "schedule"},
                        ),
                    ]

                    rules_created = 0
                    for code, name, constraint_type, weight, definition in rules_data:
                        existing_rule = (
                            (
                                await session.execute(
                                    select(ConstraintRule).where(
                                        ConstraintRule.code == code
                                    )
                                )
                            )
                            .scalars()
                            .first()
                        )

                        if not existing_rule:
                            rule = ConstraintRule(
                                code=code,
                                name=name,
                                constraint_type=constraint_type,
                                category_id=hard_category.id,
                                constraint_definition=definition,
                                default_weight=weight,
                                is_active=True,
                                is_configurable=True,
                            )
                            session.add(rule)
                            rules_created += 1

                    logger.info(
                        f"✓ Constraint system seeded: {categories_created} categories, {rules_created} rules"
                    )

            except Exception as e:
                logger.warning(
                    f"Constraint system seeding skipped (models may not exist): {e}"
                )

    # async def _seed_time_slots(self) -> None:
    #     """Seed time slots for exams"""
    #     async with db_manager.get_db_transaction() as session:
    #         logger.info("⏰ Seeding time slots...")

    #         slots_data = [
    #             ("Morning Slot", time(8, 0), time(11, 0), 180),
    #             ("Afternoon Slot", time(12, 0), time(15, 0), 180),
    #             ("Evening Slot", time(16, 0), time(19, 0), 180),
    #             ("Extended Morning", time(8, 0), time(12, 0), 240),
    #             ("Extended Afternoon", time(13, 0), time(17, 0), 240),
    #             ("Weekend Morning", time(9, 0), time(12, 0), 180),
    #             ("Weekend Afternoon", time(14, 0), time(17, 0), 180),
    #         ]

    #         slots_created = 0
    #         for name, start_time, end_time, duration in slots_data:
    #             existing = (
    #                 (
    #                     await session.execute(
    #                         select(TimeSlot).where(TimeSlot.name == name)
    #                     )
    #                 )
    #                 .scalars()
    #                 .first()
    #             )

    #             if not existing:
    #                 slot = TimeSlot(
    #                     name=name,
    #                     start_time=start_time,
    #                     end_time=end_time,
    #                     duration_minutes=duration,
    #                     is_active=True,
    #                 )
    #                 session.add(slot)
    #                 slots_created += 1

    #         logger.info(f"✓ Time slots seeded: {slots_created} slots")

    async def _seed_sample_data(self) -> None:
        """Seed sample courses, students, and exams for testing"""
        async with db_manager.get_db_transaction() as session:
            logger.info("📊 Seeding sample data...")

            # Get active session
            current_session = (
                (
                    await session.execute(
                        select(AcademicSession).where(
                            AcademicSession.is_active.is_(True)
                        )
                    )
                )
                .scalars()
                .first()
            )

            if not current_session:
                logger.warning("No active session found, skipping sample data")
                return

            # Get first department for courses
            department = (
                (await session.execute(select(Department).limit(1))).scalars().first()
            )
            if not department:
                logger.warning("No departments found, skipping sample data")
                return

            # Sample courses
            courses_data = [
                ("CSC101", "Introduction to Computer Science", 3, 100, 1),
                ("CSC201", "Data Structures and Algorithms", 3, 200, 1),
                ("MTH101", "General Mathematics I", 3, 100, 1),
                ("ENG101", "Use of English", 2, 100, 1),
                ("CSC301", "Software Engineering", 3, 300, 1),
                ("CSC401", "Final Year Project", 6, 400, 2),
            ]

            courses = []
            courses_created = 0
            for code, title, units, level, semester in courses_data:
                existing = (
                    (await session.execute(select(Course).where(Course.code == code)))
                    .scalars()
                    .first()
                )

                if not existing:
                    course = Course(
                        code=code,
                        title=title,
                        credit_units=units,
                        course_level=level,
                        semester=semester,
                        department_id=department.id,
                        exam_duration_minutes=180,
                        is_active=True,
                    )
                    session.add(course)
                    courses.append(course)
                    courses_created += 1
                else:
                    courses.append(existing)

            await session.flush()

            # Get first programme for students
            programme = (
                (await session.execute(select(Programme).limit(1))).scalars().first()
            )
            if not programme:
                logger.warning("No programmes found, skipping students")
                return

            # Sample students
            students_data = [
                ("BU/2024/CSC/001", 2024, 100),
                ("BU/2024/CSC/002", 2024, 100),
                ("BU/2023/CSC/001", 2023, 200),
                ("BU/2023/CSC/002", 2023, 200),
                ("BU/2022/CSC/001", 2022, 300),
                ("BU/2021/CSC/001", 2021, 400),
            ]

            students = []
            students_created = 0
            for matric, entry_year, level in students_data:
                existing = (
                    (
                        await session.execute(
                            select(Student).where(Student.matric_number == matric)
                        )
                    )
                    .scalars()
                    .first()
                )

                if not existing:
                    student = Student(
                        matric_number=matric,
                        entry_year=entry_year,
                        current_level=level,
                        student_type="regular",
                        special_needs=cast([], ARRAY(TEXT)),
                        programme_id=programme.id,
                        is_active=True,
                    )
                    session.add(student)
                    students.append(student)
                    students_created += 1
                else:
                    students.append(existing)

            await session.flush()

            # Course registrations
            registrations_created = 0
            for student in students:
                for course in courses:
                    if course.course_level <= student.current_level:
                        existing = (
                            (
                                await session.execute(
                                    select(CourseRegistration).where(
                                        CourseRegistration.student_id == student.id,
                                        CourseRegistration.course_id == course.id,
                                        CourseRegistration.session_id
                                        == current_session.id,
                                    )
                                )
                            )
                            .scalars()
                            .first()
                        )

                        if not existing:
                            registration = CourseRegistration(
                                student_id=student.id,
                                course_id=course.id,
                                session_id=current_session.id,
                                registration_type="regular",
                            )
                            session.add(registration)
                            registrations_created += 1

            await session.flush()

            # Sample exams
            exams_created = 0
            for course in courses:
                existing = (
                    (
                        await session.execute(
                            select(Exam).where(
                                Exam.course_id == course.id,
                                Exam.session_id == current_session.id,
                            )
                        )
                    )
                    .scalars()
                    .first()
                )

                if not existing:
                    # Count registered students for this course
                    student_count = len(
                        (
                            await session.execute(
                                select(CourseRegistration).where(
                                    CourseRegistration.course_id == course.id,
                                    CourseRegistration.session_id == current_session.id,
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )

                    exam = Exam(
                        course_id=course.id,
                        session_id=current_session.id,
                        expected_students=student_count or 1,
                        duration_minutes=course.exam_duration_minutes or 180,
                        requires_special_arrangements=False,
                        status="pending",
                    )
                    session.add(exam)
                    exams_created += 1

            logger.info(
                f"✓ Sample data seeded: {courses_created} courses, {students_created} students, {registrations_created} registrations, {exams_created} exams"
            )


async def main() -> None:
    """Main entry point with enhanced argument parsing"""
    parser = argparse.ArgumentParser(
        description="Seed the exam scheduling database with enhanced validation"
    )
    parser.add_argument("--database-url", help="Database URL override")
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Drop existing tables before seeding",
    )
    parser.add_argument(
        "--no-sample-data", action="store_true", help="Skip seeding sample data"
    )
    parser.add_argument("--csv-import", help="CSV file path for import")
    parser.add_argument(
        "--entity-type",
        help="Entity type for CSV import",
        choices=[
            "faculties",
            "departments",
            "students",
            "courses",
            "academic_sessions",
        ],
    )
    args = parser.parse_args()

    seeder = EnhancedDatabaseSeeder(args.database_url)

    try:
        if args.csv_import:
            if not args.entity_type:
                logger.error("--entity-type is required for CSV import")
                return

            logger.info(f"🔄 Importing {args.entity_type} from {args.csv_import}")
            result = await seeder.import_csv_data(args.csv_import, args.entity_type)

            if result["success"]:
                logger.info(
                    f"✅ Successfully imported {result.get('count', 0)} records"
                )
            else:
                logger.error(
                    f"❌ Import failed: {result.get('error', 'Unknown error')}"
                )
                if result.get("errors"):
                    for error in result["errors"]:
                        logger.error(f"  - {error}")
        else:
            await seeder.seed_all(
                drop_existing=args.drop_existing, sample_data=not args.no_sample_data
            )

    except Exception as e:
        logger.error(f"❌ Seeding failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
