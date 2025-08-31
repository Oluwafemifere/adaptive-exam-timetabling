#!/usr/bin/env python3
#scripts\seed_data.py
import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional, Any, Type, Dict, TYPE_CHECKING
from datetime import datetime, date, time
import argparse
from dotenv import load_dotenv  # Add this import
from sqlalchemy import select, text, cast
from sqlalchemy.orm import Session as SyncSession
from sqlalchemy.dialects.postgresql import ARRAY, TEXT
# Ensure backend is in path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

# Fix the imports
from app.database import db_manager, init_db
from app.models import (
    User, UserRole, UserRoleAssignment,
    Building, RoomType, Room,
    AcademicSession, Faculty, Department, Programme,
    TimeSlot, ConstraintCategory, ConstraintRule,
    Course, Student, CourseRegistration, Exam
)


# Load environment variables from backend/.env
env_path = Path(__file__).parent.parent / "backend" / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded environment from: {env_path}")
else:
    print(f"Environment file not found at: {env_path}")



# Import services with proper error handling
if TYPE_CHECKING:
    from app.services.data_validation import CSVProcessor, DataMapper, DataIntegrityChecker
else:
    try:
        from app.services.data_validation import CSVProcessor, DataMapper, DataIntegrityChecker
    except ImportError as e:
        print(f"Warning: Could not import validation services: {e}")
        CSVProcessor: Optional[Type[Any]] = None
        DataMapper: Optional[Type[Any]] = None
        DataIntegrityChecker: Optional[Type[Any]] = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

class DatabaseSeeder:
    def __init__(self, database_url: Optional[str] = None) -> None:
        self.database_url = database_url
        if CSVProcessor is not None:
            self.csv_processor = CSVProcessor()
            self._setup_csv_schemas()

    def _setup_csv_schemas(self) -> None:
        if not self.csv_processor:
            return
            
        # Academic sessions
        self.csv_processor.register_schema("academic_sessions", {
            "required_columns": ["name", "start_date", "end_date", "semester_system"],
            "column_mappings": {"session_name": "name", "start": "start_date", "end": "end_date"},
            "transformers": {
                "start_date": lambda x: date.fromisoformat(str(x)) if x else None,
                "end_date": lambda x: date.fromisoformat(str(x)) if x else None
            }
        })
        
        # Faculties
        self.csv_processor.register_schema("faculties", {
            "required_columns": ["name", "code"],
            "column_mappings": {"faculty_name": "name", "faculty_code": "code"},
            "transformers": {"code": lambda x: str(x).upper(), "name": lambda x: str(x).strip()}
        })
        
        logger.info("CSV schemas configured")

    async def seed_all(self, drop_existing: bool = False, sample_data: bool = True) -> None:
        """Seed the database with initial data."""
        logger.info("Starting database seeding...")
        
        # Debug: Print the database URL being used
        actual_db_url = self.database_url or os.getenv("DATABASE_URL", "NOT_FOUND")
        logger.info(f"🔍 Using database URL: {actual_db_url}")
        
        # Initialize database
        await init_db(self.database_url, create_tables=True)
        
        if drop_existing:
            logger.info("Dropping existing tables...")
            await db_manager.drop_all_tables()
            await db_manager.create_all_tables()
        
        # Seed in order (respecting foreign key constraints)
        await self._seed_users_and_roles()
        await self._seed_infrastructure()
        await self._seed_academic_structure()
        await self._seed_constraint_system()
        await self._seed_time_slots()
        
        if sample_data:
            await self._seed_sample_data()
        
        logger.info("Database seeding completed successfully!")

    async def _seed_users_and_roles(self) -> None:
        """Seed user roles and admin user."""
        async with db_manager.get_db_transaction() as session:
            logger.info("Seeding users and roles...")

            # Define roles to seed
            roles_def = [
                ("super_admin", "System Super Admin", {"*": ["*"]}),
                ("admin", "Administrator", {"academic": ["*"], "scheduling": ["*"]}),
                ("dean", "Faculty Dean", {"academic": ["read"], "scheduling": ["read"]}),
                ("hod", "Head of Department", {"academic": ["read"], "scheduling": ["read"]}),
                ("scheduler", "Scheduler", {"scheduling": ["create", "read", "update"]}),
                ("staff", "Staff", {"academic": ["read"]}),
            ]

            # Insert roles only if they don't already exist
            for name, desc, perms in roles_def:
                result = await session.execute(
                    select(UserRole).where(UserRole.name == name)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    logger.debug(f"Role '{name}' already exists, skipping.")
                    continue

                role = UserRole(name=name, description=desc, permissions=perms)
                session.add(role)

            await session.flush()

            # Create admin user if not exists
            result = await session.execute(
                select(User).where(User.email == "admin@baze.edu.ng")
            )
            admin_user = result.scalar_one_or_none()
            if not admin_user:
                admin_user = User(
                    email="admin@baze.edu.ng",
                    first_name="System",
                    last_name="Administrator",
                    password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewniM1YpKPXW5a5i",
                    is_active=True
                )
                session.add(admin_user)
                await session.flush()
                logger.debug("Created admin user.")

            # Ensure super_admin role assigned
            result = await session.execute(
                select(UserRole).where(UserRole.name == "super_admin")
            )
            super_role = result.scalar_one()
            # Check existing assignment
            assign_query = select(UserRoleAssignment).where(
                UserRoleAssignment.user_id == admin_user.id,
                UserRoleAssignment.role_id == super_role.id
            )
            assignment = (await session.execute(assign_query)).scalar_one_or_none()
            if not assignment:
                session.add(UserRoleAssignment(user_id=admin_user.id, role_id=super_role.id))
                logger.debug("Assigned super_admin role to admin user.")

            logger.info("✓ Users and roles seeded")

    async def _seed_infrastructure(self) -> None:
        """Seed buildings, room types, and rooms."""
        async with db_manager.get_db_transaction() as session:
            logger.info("Seeding infrastructure...")

            # Room types
            room_types_data = [
                ("Lecture Hall", "Large lecture hall for exams"),
                ("Classroom",     "Regular classroom"),
                ("Computer Lab",  "Computer laboratory"),
                ("Laboratory",    "Science laboratory")
            ]
            room_types = {}
            for name, desc in room_types_data:
                existing = (await session.execute(
                    select(RoomType).where(RoomType.name == name)
                )).scalars().first()
                if existing:
                    room_types[name] = existing
                else:
                    rt = RoomType(name=name, description=desc)
                    session.add(rt)
                    await session.flush()  # flush to get rt.id
                    room_types[name] = rt

            # Buildings
            buildings_data = [
                ("Engineering Block", "ENG"),
                ("Science Block",     "SCI"),
                ("Management Block",  "MGT")
            ]
            buildings = {}
            for bname, bcode in buildings_data:
                existing = (await session.execute(
                    select(Building).where(Building.code == bcode)
                )).scalars().first()
                if existing:
                    buildings[bcode] = existing
                else:
                    b = Building(name=bname, code=bcode)
                    session.add(b)
                    await session.flush()
                    buildings[bcode] = b

            # Rooms
            room_configs = [
                ("ENG","ENG01","Engineering Room 1",100,70),
                ("ENG","ENG02","Engineering Room 2",80,60),
                ("ENG","ENG03","Engineering Room 3",120,90),
                ("SCI","SCI01","Science Hall 1",150,100),
                ("SCI","SCI02","Science Hall 2",100,75),
                ("MGT","MGT01","Management Hall",200,150),
            ]
            for bcode, code, name, cap, exam_cap in room_configs:
                existing = (await session.execute(
                    select(Room).where(Room.code == code)
                )).scalars().first()
                if existing:
                    continue
                room = Room(
                    code=code,
                    name=name,
                    capacity=cap,
                    exam_capacity=exam_cap,
                    building_id=buildings[bcode].id,
                    room_type_id=room_types["Lecture Hall"].id
                )
                session.add(room)

            logger.info("✓ Infrastructure seeded")


    async def _seed_academic_structure(self) -> None:
        """Seed academic sessions, faculties, departments, and programmes."""
        async with db_manager.get_db_transaction() as session:
            logger.info("Seeding academic structure...")
            
            # Academic sessions
            current_year = datetime.now().year
            sessions_data = [
                (f"{current_year-1}/{current_year}", date(current_year-1, 9, 1), date(current_year, 8, 31), False),
                (f"{current_year}/{current_year+1}", date(current_year, 9, 1), date(current_year+1, 8, 31), True),
                (f"{current_year+1}/{current_year+2}", date(current_year+1, 9, 1), date(current_year+2, 8, 31), False),
            ]

            for name, start_date, end_date, is_active in sessions_data:
                existing = (await session.execute(
                    select(AcademicSession).where(AcademicSession.name == name)
                )).scalars().first()
                if existing:
                    continue
                session_obj = AcademicSession(
                    name=name,
                    start_date=start_date,
                    end_date=end_date,
                    semester_system="trimester",
                    is_active=is_active
                )
                session.add(session_obj)
            await session.flush()
            
            # Faculties
            faculties_data = [
                ("Engineering", "ENG"),
                ("Science",     "SCI"),
                ("Management & Social Sciences", "MGT")
            ]
            faculties = []
            for name, code in faculties_data:
                existing = (await session.execute(
                    select(Faculty).where(Faculty.code == code)
                )).scalars().first()
                if existing:
                    faculties.append(existing)
                else:
                    faculty = Faculty(name=name, code=code)
                    session.add(faculty)
                    await session.flush()
                    faculties.append(faculty)

            
            # Departments
            departments_data = [
                ("Computer Engineering", "CPE", "ENG"),
                ("Electrical Engineering", "EEE", "ENG"),
                ("Computer Science",       "CSC", "SCI"),
                ("Mathematics",            "MTH", "SCI"),
                ("Business Administration","BUS", "MGT")
            ]

            departments = []
            for name, code, faculty_code in departments_data:
                # Find the faculty object
                faculty = next(f for f in faculties if f.code == faculty_code)

                # Check if department with same code under that faculty exists
                existing = (await session.execute(
                    select(Department).where(
                        Department.code == code,
                        Department.faculty_id == faculty.id
                    )
                )).scalars().first()

                if existing:
                    departments.append(existing)
                else:
                    dept = Department(name=name, code=code, faculty_id=faculty.id)
                    session.add(dept)
                    await session.flush()
                    departments.append(dept)

            
            # Programmes
            programmes_data = [
                ("B.Eng Computer Engineering",    "BCPE", "CPE", "undergraduate", 5),
                ("B.Eng Electrical Engineering",  "BEEE", "EEE", "undergraduate", 5),
                ("B.Sc Computer Science",         "BCSC", "CSC", "undergraduate", 4),
                ("B.Sc Mathematics",              "BMTH", "MTH", "undergraduate", 4),
                ("B.Sc Business Administration",  "BBUS", "BUS", "undergraduate", 4)
            ]

            for name, code, dept_code, degree_type, duration in programmes_data:
                # Find the department object
                department = next(d for d in departments if d.code == dept_code)

                # Skip if a programme with this code already exists
                existing = (await session.execute(
                    select(Programme).where(Programme.code == code)
                )).scalars().first()
                if existing:
                    continue

                programme = Programme(
                    name=name,
                    code=code,
                    department_id=department.id,
                    degree_type=degree_type,
                    duration_years=duration
                )
                session.add(programme)

            logger.info("✓ Academic structure seeded")


    async def _seed_constraint_system(self) -> None:
        """Seed constraint categories and rules."""
        async with db_manager.get_db_transaction() as session:
            logger.info("Seeding constraint system...")

            # Constraint categories
            categories_data = [
                ("Hard Constraints", "Must be satisfied", "CP_SAT"),
                ("Soft Constraints", "Preferences to optimize", "GA")
            ]

            categories = []
            for name, desc, layer in categories_data:
                existing_cat = (await session.execute(
                    select(ConstraintCategory).where(ConstraintCategory.name == name)
                )).scalars().first()
                if existing_cat:
                    categories.append(existing_cat)
                else:
                    category = ConstraintCategory(
                        name=name,
                        description=desc,
                        enforcement_layer=layer
                    )
                    session.add(category)
                    await session.flush()
                    categories.append(category)

            # Constraint rules
            hard_category = next(c for c in categories if c.name == "Hard Constraints")

            rules_data = [
                ("NO_STUDENT_CONFLICT", "No Student Conflicts", "hard", 1.0,
                {"type": "no_overlap", "scope": "student"}),
                ("ROOM_CAPACITY", "Room Capacity", "soft", 1.0,
                {"type": "capacity_check", "scope": "room"}),
                ("TIME_AVAILABILITY", "Time Slot Availability", "hard", 1.0,
                {"type": "availability_check", "scope": "timeslot"})
            ]

            for code, name, constraint_type, weight, definition in rules_data:
                existing_rule = (await session.execute(
                    select(ConstraintRule).where(ConstraintRule.code == code)
                )).scalars().first()
                if existing_rule:
                    continue

                rule = ConstraintRule(
                    code=code,
                    name=name,
                    constraint_type=constraint_type,
                    category_id=hard_category.id,
                    constraint_definition=definition,
                    default_weight=weight
                )
                session.add(rule)

            logger.info("✓ Constraint system seeded")


    async def _seed_time_slots(self) -> None:
        """Seed time slots for exams."""
        async with db_manager.get_db_transaction() as session:
            logger.info("Seeding time slots...")
            
            slots_data = [
                ("Morning Slot", time(8, 0), time(11, 0), 180),
                ("Afternoon Slot", time(12, 0), time(15, 0), 180),
                ("Evening Slot", time(16, 0), time(19, 0), 180)
            ]
            
            for name, start_time, end_time, duration in slots_data:
                slot = TimeSlot(
                    name=name,
                    start_time=start_time,
                    end_time=end_time,
                    duration_minutes=duration
                )
                session.add(slot)
            
            logger.info("✓ Time slots seeded")

    async def _seed_sample_data(self) -> None:
        """Seed sample courses, students, and exams."""
        async with db_manager.get_db_transaction() as session:
            logger.info("Seeding sample data...")

            # Get active session
            result = await session.execute(
                select(AcademicSession).where(AcademicSession.is_active.is_(True))
            )
            current_session = result.scalars().first()
            if not current_session:
                logger.warning("No active session found, skipping sample data")
                return

            # Get first department for courses
            result = await session.execute(select(Department).limit(1))
            department = result.scalars().first()  # type: ignore
            if not department:
                logger.warning("No departments found, skipping sample data")
                return

            # Sample courses
            courses_data = [
                ("CSC101", "Introduction to Computer Science", 3, 100, 1),
                ("CSC201", "Data Structures and Algorithms", 3, 200, 1),
                ("MTH101", "General Mathematics I", 3, 100, 1),
                ("ENG101", "Use of English", 2, 100, 1)
            ]

            courses = []
            for code, title, units, level, semester in courses_data:
                course = Course(
                    code=code,
                    title=title,
                    credit_units=units,
                    course_level=level,
                    semester=semester,
                    department_id=department.id
                )
                session.add(course)
                courses.append(course)

            await session.flush()

            # Get first programme for students
            result = await session.execute(select(Programme).limit(1))
            programme = result.scalars().first()  # type: ignore
            if not programme:
                logger.warning("No programmes found, skipping students")
                return

            # Sample students
            students_data = [
                ("BU/2024/CSC/001", 2024, 100),
                ("BU/2024/CSC/002", 2024, 100),
                ("BU/2023/CSC/001", 2023, 200),
                ("BU/2023/CSC/002", 2023, 200)
            ]

            students = []
            for matric, entry_year, level in students_data:
                student = Student(
                    matric_number=matric,
                    entry_year=entry_year,
                    current_level=level,
                    student_type="regular",
                    special_needs=cast([], ARRAY(TEXT)),
                    programme_id=programme.id
                )
                session.add(student)
                students.append(student)

            await session.flush()

            # Course registrations
            for student in students:
                for course in courses:
                    if course.course_level <= student.current_level:
                        registration = CourseRegistration(
                            student_id=student.id,
                            course_id=course.id,
                            session_id=current_session.id
                        )
                        session.add(registration)

            await session.flush()

            # Sample exams
            for course in courses:
                exam = Exam(
                    course_id=course.id,
                    session_id=current_session.id,
                    expected_students=2,
                    duration_minutes=180
                )
                session.add(exam)

            logger.info("✓ Sample data seeded")

def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the exam scheduling database")
    parser.add_argument("--database-url", help="Database URL")
    parser.add_argument("--drop-existing", action="store_true", 
                       help="Drop existing tables before seeding")
    parser.add_argument("--no-sample-data", action="store_true",
                       help="Skip seeding sample data")
    parser.add_argument("--csv-import", help="CSV file path for import")
    parser.add_argument("--entity-type", help="Entity type for CSV import")
    
    args = parser.parse_args()
    
    seeder = DatabaseSeeder(args.database_url)
    
    async def run_seeding():
        try:
            if args.csv_import:
                if not args.entity_type:
                    logger.error("--entity-type is required for CSV import")
                    return
                # CSV import functionality (if validation services are available)
                logger.info(f"CSV import not fully implemented yet: {args.csv_import}")
            else:
                await seeder.seed_all(
                    drop_existing=args.drop_existing,
                    sample_data=not args.no_sample_data
                )
        except Exception as e:
            logger.error(f"Seeding failed: {e}")
            raise
    
    asyncio.run(run_seeding())

if __name__ == "__main__":
    main()
