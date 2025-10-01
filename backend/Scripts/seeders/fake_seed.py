#!/usr/bin/env python3

# Baze University Adaptive Exam Timetabling System - Comprehensive Fake Seeder


import os
import sys
import asyncio
import argparse
import logging
import math
import random
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Any, Dict, Set, List, Optional
from uuid import uuid4

from faker import Faker
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# --- Project Setup ---
# Add the backend directory to the Python path to import app modules.
# This might need adjustment based on your project structure.
try:
    BACKEND_DIR = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(BACKEND_DIR))
    from app.database import db_manager, init_db
    from app.models import (
        AcademicSession,
        AuditLog,
        Building,
        ConfigurationConstraint,
        ConstraintCategory,
        ConstraintRule,
        Course,
        CourseRegistration,
        CourseInstructor,
        Department,
        Exam,
        ExamAllowedRoom,
        ExamDepartment,
        ExamInvigilator,
        Faculty,
        FileUploadSession,
        Programme,
        Room,
        RoomType,
        SessionTemplate,
        Staff,
        StaffUnavailability,
        Student,
        StudentEnrollment,
        SystemConfiguration,
        SystemEvent,
        TimetableAssignment,
        TimetableEdit,
        TimetableJob,
        TimetableVersion,
        UploadedFile,
        User,
        UserNotification,
        UserRole,
        UserRoleAssignment,
        VersionDependency,
        VersionMetadata,
    )
    from app.core.security import hash_password
except ImportError as e:
    print(
        f"Error: Could not import project modules. Ensure this script is placed correctly."
    )
    print(f"Details: {e}")
    sys.exit(1)


# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# --- Global Faker Instance ---
fake = Faker()


# --- Data Scaling Configuration ---
# These values are adjusted by the --magnitude argument.
SCALE_LIMITS = {}


class ComprehensiveFakeSeeder:
    """
    Generates realistic fake data for the exam timetabling system.
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        seed: Optional[int] = None,
        magnitude: int = 3,
    ):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:password@localhost:5432/exam_system",
        )
        self.seed = seed
        self.magnitude = magnitude
        self.seeded_data: Dict[str, int] = {}
        self.generated_matrics: Set[str] = set()
        self._set_magnitude_level(self.magnitude)
        self._initialize_rng()

    def _initialize_rng(self):
        """Initializes random number generators for reproducibility."""
        if self.seed is not None:
            logger.info(f"🌱 Initializing RNG with seed: {self.seed}")
            random.seed(self.seed)
            Faker.seed(self.seed)

    def _set_magnitude_level(self, level: int):
        """
        Sets the data magnitude level, updating SCALE_LIMITS for the instance.
        Levels range from 1 (basic) to 5 (enterprise).
        """
        MAGNITUDE_LEVELS = {
            1: {  # Basic ~100 students
                "faculties": 3,
                "departments": 8,
                "programmes": 15,
                "courses": 80,
                "students": 100,
                "staff": 30,
                "users": 40,
                "buildings": 4,
                "rooms": 40,
                "exams": 50,
                "academic_sessions": 2,
            },
            2: {  # Small ~500 students
                "faculties": 4,
                "departments": 15,
                "programmes": 30,
                "courses": 200,
                "students": 500,
                "staff": 75,
                "users": 100,
                "buildings": 6,
                "rooms": 80,
                "exams": 150,
                "academic_sessions": 2,
            },
            3: {  # Medium ~2000 students (Default)
                "faculties": 6,
                "departments": 25,
                "programmes": 50,
                "courses": 500,
                "students": 2000,
                "staff": 200,
                "users": 250,
                "buildings": 10,
                "rooms": 150,
                "exams": 400,
                "academic_sessions": 3,
            },
            4: {  # Large ~5000 students
                "faculties": 8,
                "departments": 35,
                "programmes": 80,
                "courses": 800,
                "students": 5000,
                "staff": 400,
                "users": 500,
                "buildings": 12,
                "rooms": 250,
                "exams": 700,
                "academic_sessions": 3,
            },
            5: {  # Enterprise ~10,000 students
                "faculties": 10,
                "departments": 50,
                "programmes": 120,
                "courses": 1200,
                "students": 10000,
                "staff": 600,
                "users": 800,
                "buildings": 15,
                "rooms": 400,
                "exams": 1000,
                "academic_sessions": 4,
            },
        }

        if level not in MAGNITUDE_LEVELS:
            raise ValueError(
                f"Magnitude level must be one of {list(MAGNITUDE_LEVELS.keys())}, got {level}"
            )

        base_counts = MAGNITUDE_LEVELS[level]

        # Derive other counts based on ratios
        global SCALE_LIMITS
        SCALE_LIMITS = {
            **base_counts,
            "student_enrollments": base_counts["students"]
            * base_counts["academic_sessions"],
            "course_registrations": base_counts["students"]
            * 8,  # Avg 8 courses per student
            "course_instructors": int(base_counts["courses"] * 1.5),
            "exam_departments": int(base_counts["exams"] * 1.2),
            "exam_allowed_rooms": base_counts["exams"] * 3,
            "exam_prerequisites": int(base_counts["exams"] * 0.2),
            "user_roles": 8,
            "user_role_assignments": int(base_counts["users"] * 1.1),
            "staff_unavailability": int(base_counts["staff"] * 1.5),
            "timetable_jobs": 5,
            "timetable_versions": 10,
            "timetable_assignments": int(
                base_counts["exams"] * 1.5
            ),  # Exams might split into rooms
            "exam_invigilators": int(
                base_counts["exams"] * 2
            ),  # Avg 2 invigilators per exam
            "timetable_edits": 50,
            "audit_logs": 500,
            "system_configurations": 3,
            "constraint_categories": 5,
            "constraint_rules": 15,
            "configuration_constraints": 25,
            "system_events": 50,
            "user_notifications": 100,
            "file_upload_sessions": 10,
            "uploaded_files": 15,
            "session_templates": 5,
            "version_metadata": 10,
            "version_dependencies": 8,
        }
        logger.info(
            f"Seeding magnitude set to level {level} (students: {SCALE_LIMITS['students']})"
        )

    async def run_dry(self):
        """Prints the intended data counts without writing to the database."""
        logger.info("💨 Running in dry-run mode. No data will be written.")
        await self.print_summary(dry_run=True)

    async def run(self, drop_existing: bool = False):
        """Main seeding process to populate the database."""
        logger.info("🚀 Starting comprehensive fake data seeding...")

        try:
            await init_db(database_url=self.database_url, create_tables=False)
            logger.info("✅ Database connection established.")

            if drop_existing:
                logger.warning("🧹 Clearing all existing data from database...")
                await self._clear_all_data()

            # Seeding order is crucial to respect foreign key constraints.
            await self._seed_core_entities()
            await self._seed_academic_structure()
            await self._seed_people_and_users()
            await self._seed_scheduling_data()
            await self._seed_system_and_logging()

            logger.info("🎉 Comprehensive fake data seeding completed successfully!")
            await self.print_summary()

        except Exception as e:
            logger.error(
                f"💥 An unexpected error occurred during seeding: {e}", exc_info=True
            )
            logger.error("Performing rollback...")
            # Note: Transaction handling is within each seeder method.
            # This is a top-level catch for critical failures.
            raise

    async def _clear_all_data(self):
        """Clears all data from tables in reverse dependency order."""
        async with db_manager.get_db_transaction() as session:
            # The order here is critical to avoid foreign key violations.
            # Start from tables that are referenced by others and move inwards.
            tables_to_clear = [
                "audit_logs",
                "user_notifications",
                "system_events",
                "uploaded_files",
                "file_upload_sessions",
                "timetable_edits",
                "exam_invigilators",
                "timetable_assignments",
                "version_dependencies",
                "version_metadata",
                "exam_prerequisites_association",
                "exam_allowed_rooms",
                "exam_departments",
                "staff_unavailability",
                "timetable_versions",
                "timetable_jobs",
                "configuration_constraints",
                "constraint_rules",
                "constraint_categories",
                "system_configurations",
                "course_instructors",
                "course_registrations",
                "student_enrollments",
                "exams",
                "courses",
                "staff",
                "user_role_assignments",
                "user_roles",
                "users",
                "students",
                "programmes",
                "departments",
                "faculties",
                "rooms",
                "room_types",
                "buildings",
                "academic_sessions",
                "session_templates",
            ]
            for table in tables_to_clear:
                try:
                    # Using TRUNCATE ... CASCADE is efficient for clearing related tables.
                    await session.execute(
                        text(
                            f'TRUNCATE TABLE exam_system."{table}" RESTART IDENTITY CASCADE'
                        )
                    )
                    logger.info(f"  - Cleared table: {table}")
                except Exception as e:
                    logger.warning(f"  - Could not clear table {table}: {e}")
        logger.info("🧹 Database cleared.")

    # --- Seeding Phases ---

    async def _seed_core_entities(self):
        logger.info("Phase 1: Seeding Core Entities...")
        await self._seed_infrastructure()
        await self._seed_constraints_and_config()
        await self._seed_session_templates()

    async def _seed_academic_structure(self):
        logger.info("Phase 2: Seeding Academic Structure...")
        await self._seed_faculties_departments_programmes()
        await self._seed_academic_sessions()
        await self._seed_courses()

    async def _seed_people_and_users(self):
        logger.info("Phase 3: Seeding People and Users...")
        await self._seed_users_and_roles()
        await self._seed_students_and_enrollments()
        await self._seed_staff()
        await self._seed_course_instructors()

    async def _seed_scheduling_data(self):
        logger.info("Phase 4: Seeding Scheduling Data...")
        await self._seed_exams_and_registrations()
        await self._seed_exam_relations()
        await self._seed_timetable_jobs_and_versions()
        await self._seed_timetable_assignments_and_invigilators()

    async def _seed_system_and_logging(self):
        logger.info("Phase 5: Seeding System and Logging Entities...")
        await self._seed_timetable_edits()
        await self._seed_file_uploads()
        await self._seed_system_events_and_notifications()
        await self._seed_audit_logs()

    # --- Detailed Seeding Methods ---

    async def _seed_infrastructure(self):
        """Seed buildings, room types, and rooms."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  🏢 Seeding infrastructure (buildings, rooms)...")
            # Buildings
            building_codes = {
                "ENG",
                "SCI",
                "MGT",
                "LIB",
                "MED",
                "LAW",
                "ART",
                "SOC",
                "TECH",
                "ADMIN",
            }
            buildings = []
            for code in list(building_codes)[: SCALE_LIMITS["buildings"]]:
                b = Building(code=code, name=f"{code} Building", is_active=True)
                buildings.append(b)
            session.add_all(buildings)
            await session.flush()
            self.seeded_data["buildings"] = len(buildings)

            # Room Types
            room_type_names = [
                "Classroom",
                "Laboratory",
                "Auditorium",
                "Seminar Room",
                "Workshop",
                "Office",
            ]
            room_types = []
            for name in room_type_names:
                rt = RoomType(name=name, description=f"{name} space", is_active=True)
                room_types.append(rt)
            session.add_all(room_types)
            await session.flush()
            self.seeded_data["room_types"] = len(room_types)

            # Rooms
            rooms = []
            generated_room_codes = (
                set()
            )  # FIX: Track generated codes to ensure uniqueness
            for _ in range(SCALE_LIMITS["rooms"]):
                building = random.choice(buildings)
                room_type = random.choice(room_types)
                capacity = {
                    "Auditorium": random.randint(200, 500),
                    "Classroom": random.randint(30, 120),
                    "Laboratory": random.randint(20, 50),
                }.get(room_type.name, random.randint(15, 40))

                # FIX: Loop until a unique room code is generated
                while True:
                    code = f"{building.code}-{random.randint(100, 999)}"
                    if code not in generated_room_codes:
                        generated_room_codes.add(code)
                        break

                r = Room(
                    code=code,  # Use the guaranteed unique code
                    name=f"{building.name} Room {random.randint(1, 50)}",
                    building_id=building.id,
                    room_type_id=room_type.id,
                    capacity=capacity,
                    exam_capacity=max(
                        15, int(capacity * 0.7)
                    ),  # Social distancing capacity
                    has_projector=random.choice([True, False]),
                    has_computers=room_type.name == "Laboratory",
                    is_active=True,
                    has_ac=random.choice([True, True, False]),
                    max_inv_per_room=max(1, capacity // 100),
                )
                rooms.append(r)
            session.add_all(rooms)
            self.seeded_data["rooms"] = len(rooms)
            logger.info(
                f"  ✓ Seeded {len(buildings)} buildings, {len(room_types)} room types, {len(rooms)} rooms."
            )

    async def _seed_constraints_and_config(self):
        """Seed system configurations and constraints."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  ⚙️ Seeding system configurations and constraints...")
            # This requires a user, so we create a temporary admin user first.
            admin_user = User(
                email="config_admin@baze.edu.ng",
                first_name="Config",
                last_name="Admin",
                is_active=True,
                is_superuser=True,
                password_hash=hash_password("temp"),
            )
            session.add(admin_user)
            await session.flush()

            # System Configurations
            configs = []
            for name in ["Default", "Fast", "High-Quality"]:
                c = SystemConfiguration(
                    name=f"{name} Config",
                    description=f"{name} scheduling parameters",
                    created_by=admin_user.id,
                    is_default=(name == "Default"),
                )
                configs.append(c)
            session.add_all(configs)
            await session.flush()
            self.seeded_data["system_configurations"] = len(configs)

            # Constraint Categories & Rules
            categories = [
                ConstraintCategory(name=c)
                for c in ["Temporal", "Spatial", "Resource", "Pedagogical"]
            ]
            session.add_all(categories)
            await session.flush()
            self.seeded_data["constraint_categories"] = len(categories)

            rules_data = [
                (
                    "NO_EXAM_OVERLAP",
                    "No overlapping exams for students",
                    "hard",
                    categories[0].id,
                ),
                (
                    "ROOM_CAPACITY",
                    "Room capacity not exceeded",
                    "hard",
                    categories[1].id,
                ),
                (
                    "MAX_EXAMS_PER_DAY",
                    "Max exams per day for students",
                    "soft",
                    categories[0].id,
                ),
            ]
            rules = []
            for code, name, c_type, cat_id in rules_data:
                rule = ConstraintRule(
                    code=code,
                    name=name,
                    constraint_type=c_type,
                    category_id=cat_id,
                    is_active=True,
                    constraint_definition={},
                    default_weight=1.0,
                )
                rules.append(rule)
            session.add_all(rules)
            await session.flush()
            self.seeded_data["constraint_rules"] = len(rules)

            # Configuration Constraints
            config_constraints = []
            for config in configs:
                for rule in rules:
                    cc = ConfigurationConstraint(
                        configuration_id=config.id,
                        constraint_id=rule.id,
                        weight=1.0,
                        is_enabled=True,
                    )
                    config_constraints.append(cc)
            session.add_all(config_constraints)
            self.seeded_data["configuration_constraints"] = len(config_constraints)
            logger.info(f"  ✓ Seeded {len(configs)} configs and {len(rules)} rules.")

    async def _seed_session_templates(self):
        """Seed session templates."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  📄 Seeding session templates...")
            templates = []
            for name in ["Standard Semester", "Fast-Track", "Postgraduate"]:
                t = SessionTemplate(
                    name=name, description=f"Template for {name}", is_active=True
                )
                templates.append(t)
            session.add_all(templates)
            self.seeded_data["session_templates"] = len(templates)
            logger.info(f"  ✓ Seeded {len(templates)} session templates.")

    async def _seed_faculties_departments_programmes(self):
        """Seed faculties, departments, and programmes."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  🎓 Seeding academic structure (faculties, departments)...")
            faculty_data = {
                "ENG": "Engineering",
                "SCI": "Sciences",
                "MGT": "Management",
                "LAW": "Law",
                "ART": "Arts",
                "SOC": "Social Sciences",
                "EDU": "Education",
                "ENV": "Environmental Sci.",
                "BMS": "Basic Medical Sci.",
                "CSI": "Computing & Applied Sci.",
            }
            dept_data = {
                "ENG": ["CPE", "CVE", "MEE"],
                "SCI": ["CSC", "BIO", "PHY"],
                "MGT": ["ACC", "BUS", "ECO"],
                "CSI": ["IFT", "CYB", "SWE"],
            }

            # Faculties
            faculties = []
            for code, name in list(faculty_data.items())[: SCALE_LIMITS["faculties"]]:
                faculties.append(
                    Faculty(code=code, name=f"Faculty of {name}", is_active=True)
                )
            session.add_all(faculties)
            await session.flush()
            self.seeded_data["faculties"] = len(faculties)

            # Departments and Programmes
            departments, programmes = [], []
            for fac in faculties:
                if fac.code in dept_data:
                    for dept_code in dept_data[fac.code]:
                        if len(departments) >= SCALE_LIMITS["departments"]:
                            break
                        dept = Department(
                            code=dept_code,
                            name=f"Dept of {dept_code}",
                            faculty_id=fac.id,
                            is_active=True,
                        )
                        session.add(dept)
                        await session.flush()
                        departments.append(dept)

                        # Add a programme for the department
                        if len(programmes) < SCALE_LIMITS["programmes"]:
                            prog = Programme(
                                code=f"B.{dept.code}",
                                name=f"B.Sc. {dept_code}",
                                department_id=dept.id,
                                degree_type="undergraduate",
                                duration_years=4,
                            )
                            programmes.append(prog)
            session.add_all(programmes)
            self.seeded_data["departments"] = len(departments)
            self.seeded_data["programmes"] = len(programmes)
            logger.info(
                f"  ✓ Seeded {len(faculties)} faculties, {len(departments)} depts, {len(programmes)} programmes."
            )

    async def _seed_academic_sessions(self):
        """Seed academic sessions."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  🗓️ Seeding academic sessions...")
            sessions = []
            current_year = datetime.now().year
            for i in range(SCALE_LIMITS["academic_sessions"]):
                year = current_year - i
                s = AcademicSession(
                    name=f"{year}/{year+1}",
                    semester_system="semester",
                    start_date=date(year, 9, 15),
                    end_date=date(year + 1, 6, 30),
                    is_active=(i == 0),  # Only the most recent session is active
                )
                sessions.append(s)
            session.add_all(sessions)
            self.seeded_data["academic_sessions"] = len(sessions)
            logger.info(f"  ✓ Seeded {len(sessions)} academic sessions.")

    async def _seed_courses(self):
        """Seed courses."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  📚 Seeding courses...")
            departments = (await session.execute(select(Department))).scalars().all()
            courses = []

            # --- Start of fix ---
            generated_course_codes = set()  # Use a set for efficient lookups
            # --- End of fix ---

            for _ in range(SCALE_LIMITS["courses"]):
                dept = random.choice(departments)
                level = random.choice([100, 200, 300, 400])

                # --- Start of fix ---
                # Loop until a unique code is generated
                while True:
                    code = f"{dept.code}{level+random.randint(1, 99)}"  # Increased random range
                    if code not in generated_course_codes:
                        generated_course_codes.add(code)
                        break
                # --- End of fix ---

                c = Course(
                    code=code,  # Use the guaranteed unique code
                    title=fake.catch_phrase(),
                    department_id=dept.id,
                    credit_units=random.choice([2, 3, 4]),
                    course_level=level,
                    is_practical=random.choice(
                        [True, False, False]
                    ),  # 1/3 are practical
                    exam_duration_minutes=random.choice([120, 180]),
                )
                courses.append(c)
            session.add_all(courses)
            self.seeded_data["courses"] = len(courses)
            logger.info(f"  ✓ Seeded {len(courses)} courses.")

    async def _seed_users_and_roles(self):
        """Seed user roles, an admin user, and other fake users."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  👥 Seeding users and roles...")
            # User Roles
            roles_def = {
                "super_admin": {"*": ["*"]},
                "admin": {},
                "dean": {},
                "hod": {},
                "scheduler": {},
                "staff": {},
            }
            roles = [
                UserRole(name=name, permissions=perms)
                for name, perms in roles_def.items()
            ]
            session.add_all(roles)
            await session.flush()
            self.seeded_data["user_roles"] = len(roles)
            roles_map = {r.name: r for r in roles}

            # Admin User
            admin_user = User(
                email="admin@baze.edu.ng",
                first_name="System",
                last_name="Admin",
                password_hash=hash_password("admin123"),
                is_active=True,
                is_superuser=True,
            )
            session.add(admin_user)
            await session.flush()
            session.add(
                UserRoleAssignment(
                    user_id=admin_user.id, role_id=roles_map["super_admin"].id
                )
            )

            # Fake Users
            users = [admin_user]
            for _ in range(SCALE_LIMITS["users"] - 1):
                first_name, last_name = fake.first_name(), fake.last_name()
                users.append(
                    User(
                        email=f"{first_name}.{last_name}{random.randint(1,99)}@fake.baze.edu.ng".lower(),
                        first_name=first_name,
                        last_name=last_name,
                        password_hash=hash_password("password123"),
                        is_active=True,
                    )
                )
            session.add_all(users[1:])  # Add all except the admin that's already added
            self.seeded_data["users"] = len(users)
            logger.info(f"  ✓ Seeded {len(roles)} roles and {len(users)} users.")

    async def _seed_students_and_enrollments(self):
        """Seed students and their enrollments in academic sessions."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  👨‍🎓 Seeding students and enrollments...")

            # --- Start of FIX ---
            # Eagerly load the 'department' relationship to prevent lazy-loading issues.
            from sqlalchemy.orm import selectinload

            programmes = (
                (
                    await session.execute(
                        select(Programme).options(selectinload(Programme.department))
                    )
                )
                .scalars()
                .all()
            )
            # --- End of FIX ---

            sessions = (await session.execute(select(AcademicSession))).scalars().all()
            if not programmes or not sessions:
                logger.error("  Cannot seed students: No programmes or sessions exist.")
                return

            students, enrollments = [], []
            current_year = datetime.now().year
            for i in range(SCALE_LIMITS["students"]):
                prog = random.choice(programmes)
                entry_year = current_year - random.randint(0, prog.duration_years - 1)

                # This line will now work without causing an error.
                matric = f"BU/{str(entry_year)[-2:]}/{prog.department.code}/{i:04d}"

                s = Student(
                    matric_number=matric,
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                    entry_year=entry_year,
                    programme_id=prog.id,
                )
                session.add(s)
                await session.flush()
                students.append(s)

                for sess in sessions:
                    level = (int(sess.name.split("/")[0]) - s.entry_year + 1) * 100
                    if 100 <= level <= (prog.duration_years * 100):
                        enrollments.append(
                            StudentEnrollment(
                                student_id=s.id, session_id=sess.id, level=level
                            )
                        )

            session.add_all(enrollments)
            self.seeded_data["students"] = len(students)
            self.seeded_data["student_enrollments"] = len(enrollments)
            logger.info(
                f"  ✓ Seeded {len(students)} students and {len(enrollments)} enrollments."
            )

    async def _seed_staff(self):
        """Seed staff members."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  👨‍🏫 Seeding staff...")
            departments = (await session.execute(select(Department))).scalars().all()
            users = (await session.execute(select(User))).scalars().all()

            assigned_user_ids = set(
                (
                    await session.execute(
                        select(Staff.user_id).where(Staff.user_id.is_not(None))
                    )
                )
                .scalars()
                .all()
            )
            available_users = [u for u in users if u.id not in assigned_user_ids]

            staff_list = []
            for i in range(SCALE_LIMITS["staff"]):
                user = available_users.pop() if available_users else None
                staff = Staff(
                    staff_number=f"ST{1000+i}",
                    first_name=user.first_name if user else fake.first_name(),
                    last_name=user.last_name if user else fake.last_name(),
                    department_id=random.choice(departments).id,
                    user_id=user.id if user else None,
                    staff_type="academic",
                    can_invigilate=True,
                    is_active=True,
                    max_daily_sessions=2,
                    max_consecutive_sessions=2,
                    max_concurrent_exams=1,
                    max_students_per_invigilator=50,
                )
                staff_list.append(staff)
            session.add_all(staff_list)
            self.seeded_data["staff"] = len(staff_list)
            logger.info(f"  ✓ Seeded {len(staff_list)} staff members.")

    # MODIFIED: New method to handle course instructors
    async def _seed_course_instructors(self):
        """Seed the many-to-many relationship between courses and staff."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  🧑‍🏫 Seeding course instructors...")
            courses = (await session.execute(select(Course))).scalars().all()
            staff = (await session.execute(select(Staff))).scalars().all()

            if not courses or not staff:
                logger.warning("  Cannot seed instructors: No courses or staff exist.")
                return

            instructors = []
            for course in courses:
                # Assign 1 to 3 instructors per course
                num_instructors = random.randint(1, 3)
                assigned_staff = random.sample(staff, min(num_instructors, len(staff)))

                for staff_member in assigned_staff:
                    instructors.append(
                        CourseInstructor(course_id=course.id, staff_id=staff_member.id)
                    )

            # Ensure we don't exceed the defined magnitude limit
            if len(instructors) > SCALE_LIMITS["course_instructors"]:
                instructors = random.sample(
                    instructors, SCALE_LIMITS["course_instructors"]
                )

            session.add_all(instructors)
            self.seeded_data["course_instructors"] = len(instructors)
            logger.info(f"  ✓ Seeded {len(instructors)} course instructor links.")

    async def _seed_exams_and_registrations(self):
        """Seed exams and ensure course registrations meet minimums."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  📝 Seeding exams and course registrations...")
            active_session = (
                (
                    await session.execute(
                        select(AcademicSession).where(AcademicSession.is_active == True)
                    )
                )
                .scalars()
                .first()
            )
            if not active_session:
                logger.error("  Cannot seed exams: No active academic session found.")
                return

            courses = (
                (
                    await session.execute(
                        select(Course).options(selectinload(Course.department))
                    )
                )
                .scalars()
                .all()
            )
            students = (await session.execute(select(Student))).scalars().all()
            staff = (
                (await session.execute(select(Staff))).scalars().all()
            )  # Fetch staff for instructor assignment

            if not courses or not students or not staff:
                logger.error("Cannot seed exams: Missing courses, students, or staff.")
                return

            student_dept_map = {}
            prog_dept_map_result = await session.execute(
                select(Programme.id, Programme.department_id)
            )
            prog_dept_map = {
                prog_id: dept_id for prog_id, dept_id in prog_dept_map_result
            }
            for s in students:
                student_dept_map[s.id] = prog_dept_map.get(s.programme_id)

            exams, registrations = [], []

            for student in students:
                student_level = (
                    int(active_session.name.split("/")[0]) - student.entry_year + 1
                ) * 100
                student_dept = student_dept_map.get(student.id)
                eligible_courses = [
                    c
                    for c in courses
                    if c.department_id == student_dept
                    and c.course_level == student_level
                ]
                num_courses = random.randint(6, 10)
                for course in random.sample(
                    eligible_courses, min(num_courses, len(eligible_courses))
                ):
                    registrations.append(
                        CourseRegistration(
                            student_id=student.id,
                            course_id=course.id,
                            session_id=active_session.id,
                        )
                    )
            session.add_all(registrations)
            await session.flush()

            courses_with_regs = (
                await session.execute(
                    select(
                        CourseRegistration.course_id,
                        func.count(CourseRegistration.id).label("reg_count"),
                    )
                    .where(CourseRegistration.session_id == active_session.id)
                    .group_by(CourseRegistration.course_id)
                )
            ).all()
            course_reg_counts = {c[0]: c[1] for c in courses_with_regs}
            all_course_map = {c.id: c for c in courses}

            for course_id, reg_count in list(course_reg_counts.items())[
                : SCALE_LIMITS["exams"]
            ]:
                course = all_course_map[course_id]
                final_reg_count = reg_count
                if 0 < reg_count < 30:
                    needed = 30 - reg_count
                    registered_students = set(
                        (
                            await session.execute(
                                select(CourseRegistration.student_id).where(
                                    CourseRegistration.course_id == course.id
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )
                    eligible_students = [
                        s.id
                        for s in students
                        if student_dept_map.get(s.id) == course.department_id
                        and s.id not in registered_students
                    ]
                    if len(eligible_students) >= needed:
                        new_regs = [
                            CourseRegistration(
                                student_id=sid,
                                course_id=course.id,
                                session_id=active_session.id,
                            )
                            for sid in random.sample(eligible_students, needed)
                        ]
                        session.add_all(new_regs)
                        registrations.extend(new_regs)
                        final_reg_count = 30

                if final_reg_count > 0:
                    exams.append(
                        Exam(
                            course_id=course.id,
                            session_id=active_session.id,
                            duration_minutes=course.exam_duration_minutes,
                            expected_students=final_reg_count,
                            status="pending",
                            is_practical=course.is_practical or False,
                            morning_only=random.choice([True, False]),
                            requires_projector=random.choice([True, False, False]),
                            # MODIFIED: Removed obsolete instructor_id assignment
                        )
                    )
            session.add_all(exams)
            self.seeded_data["course_registrations"] = len(registrations)
            self.seeded_data["exams"] = len(exams)
            logger.info(
                f"  ✓ Seeded {len(registrations)} registrations and {len(exams)} exams."
            )

    async def _seed_exam_relations(self):
        """Seed exam_departments, allowed_rooms, and prerequisites."""
        async with db_manager.get_db_transaction() as session:
            logger.info(
                "  🔗 Seeding exam relations (departments, rooms, prerequisites)..."
            )
            exams = (
                (
                    await session.execute(
                        select(Exam).options(
                            selectinload(Exam.course),
                            selectinload(
                                Exam.prerequisites
                            ),  # Eager load prerequisites
                        )
                    )
                )
                .scalars()
                .all()
            )
            rooms = (await session.execute(select(Room))).scalars().all()
            if not exams or not rooms:
                return

            exam_depts, allowed_rooms = [], []
            prereqs_count = 0

            # Group exams by department and level for prerequisite logic
            dept_level_exams = {}
            for exam in exams:
                dept_id = exam.course.department_id
                level = exam.course.course_level
                if (dept_id, level) not in dept_level_exams:
                    dept_level_exams[(dept_id, level)] = []
                dept_level_exams[(dept_id, level)].append(exam)

            for exam in exams:
                # Exam Departments
                exam_depts.append(
                    ExamDepartment(
                        exam_id=exam.id, department_id=exam.course.department_id
                    )
                )

                # Allowed Rooms
                num_rooms = random.randint(1, 5)
                for room in random.sample(rooms, min(num_rooms, len(rooms))):
                    allowed_rooms.append(
                        ExamAllowedRoom(exam_id=exam.id, room_id=room.id)
                    )

                # Exam Prerequisites - FIXED: Use direct relationship assignment
                if prereqs_count < SCALE_LIMITS["exam_prerequisites"]:
                    level = exam.course.course_level
                    if level > 100:
                        prereq_level = level - 100
                        dept_id = exam.course.department_id
                        potential_prereqs = dept_level_exams.get(
                            (dept_id, prereq_level), []
                        )
                        if potential_prereqs:
                            prereq_exam = random.choice(potential_prereqs)

                            # FIX: Check if prerequisite already exists to avoid duplicates
                            existing_prereqs = {p.id for p in exam.prerequisites}
                            if prereq_exam.id not in existing_prereqs:
                                exam.prerequisites.append(prereq_exam)
                                prereqs_count += 1

            session.add_all(exam_depts + allowed_rooms)
            # No need to manually add prerequisites since they're handled by the relationship
            self.seeded_data["exam_departments"] = len(exam_depts)
            self.seeded_data["exam_allowed_rooms"] = len(allowed_rooms)
            self.seeded_data["exam_prerequisites_association"] = prereqs_count
            logger.info(
                f"  ✓ Seeded {len(exam_depts)} exam depts, {len(allowed_rooms)} allowed rooms, {prereqs_count} prerequisites."
            )

    async def _seed_timetable_jobs_and_versions(self):
        """Seed timetable jobs and versions."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  ⏳ Seeding timetable jobs and versions...")
            sessions = (await session.execute(select(AcademicSession))).scalars().all()
            configs = (
                (await session.execute(select(SystemConfiguration))).scalars().all()
            )
            users = (await session.execute(select(User))).scalars().all()
            if not all([sessions, configs, users]):
                return

            jobs, versions = [], []
            for _ in range(SCALE_LIMITS["timetable_jobs"]):
                job = TimetableJob(
                    session_id=random.choice(sessions).id,
                    configuration_id=random.choice(configs).id,
                    initiated_by=random.choice(users).id,
                    status=random.choice(["completed", "failed"]),
                    progress_percentage=(
                        100 if random.choice([True, False]) else random.randint(0, 99)
                    ),
                    hard_constraint_violations=random.randint(0, 5),
                    soft_constraint_score=random.uniform(0.8, 1.0),
                    room_utilization_percentage=random.uniform(60, 95),
                )
                session.add(job)
                await session.flush()
                jobs.append(job)

                for i in range(random.randint(1, 3)):  # 1-3 versions per job
                    v = TimetableVersion(
                        job_id=job.id,
                        version_number=i + 1,
                        version_type="primary",
                        is_active=(i == 0),  # Only the first version is active
                        is_published=True,
                    )
                    versions.append(v)

            session.add_all(versions)
            self.seeded_data["timetable_jobs"] = len(jobs)
            self.seeded_data["timetable_versions"] = len(versions)
            logger.info(f"  ✓ Seeded {len(jobs)} jobs and {len(versions)} versions.")

    async def _seed_timetable_assignments_and_invigilators(self):
        """Seed timetable assignments and exam invigilators."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  ✍️ Seeding timetable assignments and invigilators...")

            # Eagerly load all required relationships to avoid lazy loading issues
            versions = (
                (
                    await session.execute(
                        select(TimetableVersion).options(
                            selectinload(TimetableVersion.job).selectinload(
                                TimetableJob.session
                            )
                        )
                    )
                )
                .scalars()
                .all()
            )
            rooms = (await session.execute(select(Room))).scalars().all()
            exams = (
                (await session.execute(select(Exam).options(selectinload(Exam.course))))
                .scalars()
                .all()
            )
            staff = (
                (
                    await session.execute(
                        select(Staff).where(Staff.can_invigilate == True)
                    )
                )
                .scalars()
                .all()
            )

            if not all([versions, rooms, exams, staff]):
                logger.warning(
                    "  Skipping timetable assignments: missing required data"
                )
                return

            assignments, invigilators = [], []
            time_slots = ["Morning", "Afternoon", "Evening"]

            for version in versions:
                # Access the eagerly loaded session directly
                session_start_date = version.job.session.start_date
                exam_day_offset = random.randint(60, 90)

                # Get exams for this version's session
                session_exams = [
                    e for e in exams if e.session_id == version.job.session_id
                ]

                # Limit the number of assignments per version to avoid excessive data
                max_assignments_per_version = min(
                    len(session_exams),
                    max(
                        1,
                        SCALE_LIMITS["timetable_assignments"] // max(1, len(versions)),
                    ),
                )

                for exam in random.sample(session_exams, max_assignments_per_version):
                    exam_date = session_start_date + timedelta(
                        days=exam_day_offset + random.randint(0, 14)
                    )

                    students_left = exam.expected_students
                    is_primary = True
                    rooms_used = 0

                    while students_left > 0 and rooms_used < 5:  # Limit rooms per exam
                        # Smart room selection based on exam requirements
                        if exam.is_practical:
                            room_pool = [r for r in rooms if r.has_computers]
                        elif exam.requires_projector:
                            room_pool = [r for r in rooms if r.has_projector]
                        else:
                            room_pool = rooms

                        # If no suitable rooms, use any room
                        if not room_pool:
                            room_pool = rooms

                        room = random.choice(room_pool)
                        room_capacity = room.exam_capacity or (room.capacity * 2 // 3)
                        assigned_count = min(students_left, room_capacity)

                        if assigned_count <= 0:
                            break  # Skip if room has no capacity

                        assign = TimetableAssignment(
                            exam_id=exam.id,
                            room_id=room.id,
                            version_id=version.id,
                            exam_date=exam_date,
                            time_slot_period=random.choice(time_slots),
                            student_count=assigned_count,
                            allocated_capacity=assigned_count,
                            is_primary=is_primary,
                            is_confirmed=True,
                        )
                        session.add(assign)
                        await session.flush()
                        assignments.append(assign)

                        is_primary = False
                        students_left -= assigned_count
                        rooms_used += 1

                        # Assign invigilators - ensure we don't exceed limits
                        num_invigilators = max(1, math.ceil(assigned_count / 50))
                        available_staff = [
                            s for s in staff if s.max_concurrent_exams > 0
                        ]

                        if available_staff:
                            invigilator_count = min(
                                num_invigilators,
                                len(available_staff),
                                room.max_inv_per_room,
                            )
                            for i, inv_staff in enumerate(
                                random.sample(available_staff, invigilator_count)
                            ):
                                invigilators.append(
                                    ExamInvigilator(
                                        timetable_assignment_id=assign.id,
                                        staff_id=inv_staff.id,
                                        is_chief_invigilator=(i == 0),
                                    )
                                )

            session.add_all(invigilators)
            self.seeded_data["timetable_assignments"] = len(assignments)
            self.seeded_data["exam_invigilators"] = len(invigilators)
            logger.info(
                f"  ✓ Seeded {len(assignments)} assignments and {len(invigilators)} invigilators."
            )

    async def _seed_timetable_edits(self):
        """Seed timetable edits."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  ✏️ Seeding timetable edits...")

            # Eagerly load assignments with version relationships
            assignments = (
                (
                    await session.execute(
                        select(TimetableAssignment).options(
                            selectinload(TimetableAssignment.version)
                        )
                    )
                )
                .scalars()
                .all()
            )
            users = (await session.execute(select(User))).scalars().all()

            if not assignments or not users:
                logger.warning(
                    "  Skipping timetable edits: missing assignments or users"
                )
                return

            edits = []
            max_edits = min(len(assignments), SCALE_LIMITS["timetable_edits"])

            for assign in random.sample(assignments, max_edits):
                exam_date = assign.exam_date

                # Normalize type: ensure it's a Python date
                if isinstance(exam_date, datetime):
                    exam_date = exam_date.date()
                elif not isinstance(exam_date, date):
                    try:
                        exam_date = datetime.strptime(str(exam_date), "%Y-%m-%d").date()
                    except ValueError:
                        exam_date = date.today()  # Fallback

                edit = TimetableEdit(
                    version_id=assign.version_id,
                    exam_id=assign.exam_id,
                    edited_by=random.choice(users).id,
                    edit_type=random.choice(
                        ["reschedule", "room_change", "time_change"]
                    ),
                    reason=random.choice(
                        [
                            "Administrative adjustment",
                            "Room maintenance",
                            "Staff availability",
                            "Student conflict",
                        ]
                    ),
                    validation_status=random.choice(
                        ["approved", "pending", "rejected"]
                    ),
                    old_values={
                        "date": str(exam_date),
                        "time_slot": assign.time_slot_period,
                        "room_id": str(assign.room_id),
                    },
                    new_values={
                        "date": str(exam_date + timedelta(days=random.randint(1, 3))),
                        "time_slot": random.choice(["Morning", "Afternoon", "Evening"]),
                        "room_id": str(
                            assign.room_id
                        ),  # Same room or could be different
                    },
                )
                edits.append(edit)

            session.add_all(edits)
            self.seeded_data["timetable_edits"] = len(edits)
            logger.info(f"  ✓ Seeded {len(edits)} timetable edits.")

    async def _seed_file_uploads(self):
        """Seed file upload sessions and files."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  📤 Seeding file uploads...")
            users = (await session.execute(select(User))).scalars().all()
            if not users:
                logger.warning("  Skipping file uploads: no users available")
                return

            upload_sessions, uploaded_files = [], []
            upload_types = ["students", "courses", "staff", "exams", "rooms"]

            for _ in range(
                min(SCALE_LIMITS["file_upload_sessions"], len(upload_types))
            ):
                upload_type = random.choice(upload_types)
                upload_session = FileUploadSession(
                    upload_type=upload_type,
                    uploaded_by=random.choice(users).id,
                    status=random.choice(["completed", "processing", "failed"]),
                    total_records=random.randint(50, 500),
                    processed_records=random.randint(50, 500),
                    validation_errors=(
                        []
                        if random.choice([True, False])
                        else [
                            {"row": 1, "error": "Missing required field"},
                            {"row": 5, "error": "Invalid format"},
                        ]
                    ),
                )
                session.add(upload_session)
                await session.flush()
                upload_sessions.append(upload_session)

                # Create 1-2 files per upload session
                for file_num in range(random.randint(1, 2)):
                    uploaded_files.append(
                        UploadedFile(
                            upload_session_id=upload_session.id,
                            file_name=f"{upload_type}_batch_{file_num + 1}.csv",
                            file_path=f"/uploads/{upload_type}/batch_{file_num + 1}.csv",
                            file_size=random.randint(1024, 1048576),  # 1KB to 1MB
                            file_type="csv",
                            mime_type="text/csv",
                            row_count=random.randint(50, 500),
                            validation_status=random.choice(
                                ["valid", "invalid", "partial"]
                            ),
                            validation_errors=(
                                []
                                if random.choice([True, False])
                                else ["Header mismatch", "Duplicate records found"]
                            ),
                        )
                    )

            session.add_all(uploaded_files)
            self.seeded_data["file_upload_sessions"] = len(upload_sessions)
            self.seeded_data["uploaded_files"] = len(uploaded_files)
            logger.info(
                f"  ✓ Seeded {len(upload_sessions)} upload sessions and {len(uploaded_files)} files."
            )

    async def _seed_system_events_and_notifications(self):
        """Seed system events and user notifications."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  🔔 Seeding system events and notifications...")
            users = (await session.execute(select(User))).scalars().all()
            if not users:
                logger.warning("  Skipping system events: no users available")
                return

            events, notifications = [], []
            event_types = ["info", "warning", "error", "success"]
            priorities = ["low", "medium", "high", "critical"]
            entities = ["exam", "timetable", "room", "staff", "student", "system"]

            for _ in range(SCALE_LIMITS["system_events"]):
                event = SystemEvent(
                    title=fake.sentence(),
                    message=fake.paragraph(),
                    event_type=random.choice(event_types),
                    priority=random.choice(priorities),
                    entity_type=random.choice(
                        entities + [None]
                    ),  # Some events may not have entity
                    entity_id=uuid4() if random.choice([True, False]) else None,
                    event_metadata={
                        "source": random.choice(
                            ["scheduler", "upload", "manual", "system"]
                        ),
                        "affected_components": random.sample(
                            entities, random.randint(1, 3)
                        ),
                    },
                    affected_users=(
                        random.sample([u.id for u in users], min(5, len(users)))
                        if random.choice([True, False])
                        else []
                    ),
                    is_resolved=random.choice([True, False]),
                    resolved_by=(
                        random.choice(users).id
                        if random.choice([True, False])
                        else None
                    ),
                    resolved_at=(
                        datetime.now() if random.choice([True, False]) else None
                    ),
                )
                session.add(event)
                await session.flush()
                events.append(event)

                # Create notifications for some events
                if len(notifications) < SCALE_LIMITS["user_notifications"]:
                    num_notifications = random.randint(1, min(5, len(users)))
                    for user in random.sample(users, num_notifications):
                        if len(notifications) < SCALE_LIMITS["user_notifications"]:
                            notifications.append(
                                UserNotification(
                                    user_id=user.id,
                                    event_id=event.id,
                                    is_read=random.choice([True, False]),
                                    read_at=(
                                        datetime.now()
                                        if random.choice([True, False])
                                        else None
                                    ),
                                )
                            )

            session.add_all(notifications)
            self.seeded_data["system_events"] = len(events)
            self.seeded_data["user_notifications"] = len(notifications)
            logger.info(
                f"  ✓ Seeded {len(events)} events and {len(notifications)} notifications."
            )

    async def _seed_audit_logs(self):
        """Seed audit logs."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  🛡️ Seeding audit logs...")
            users = (await session.execute(select(User))).scalars().all()
            if not users:
                logger.warning("  Skipping audit logs: no users available")
                return

            logs = []
            actions = [
                "login",
                "logout",
                "create",
                "update",
                "delete",
                "view",
                "export",
            ]
            entities = [
                "user",
                "student",
                "course",
                "exam",
                "timetable",
                "room",
                "system",
            ]

            for _ in range(SCALE_LIMITS["audit_logs"]):
                user = random.choice(users)
                action = random.choice(actions)
                entity_type = random.choice(entities)

                log = AuditLog(
                    user_id=user.id,
                    action=action,
                    entity_type=entity_type,
                    entity_id=uuid4() if random.choice([True, False]) else None,
                    old_values=(
                        {"previous_value": "old_data"}
                        if random.choice([True, False])
                        else None
                    ),
                    new_values=(
                        {"new_value": "new_data"}
                        if random.choice([True, False])
                        else None
                    ),
                    ip_address=fake.ipv4(),
                    user_agent=fake.user_agent(),
                    session_id=fake.uuid4() if random.choice([True, False]) else None,
                    notes=fake.sentence() if random.choice([True, False]) else None,
                )
                logs.append(log)

            session.add_all(logs)
            self.seeded_data["audit_logs"] = len(logs)
            logger.info(f"  ✓ Seeded {len(logs)} audit logs.")

    async def print_summary(self, dry_run=False):
        """Prints a summary of intended or actual data counts and key ratios."""
        logger.info("\n" + "=" * 60)
        logger.info("📊 SEEDING SUMMARY")
        logger.info("=" * 60)

        data = SCALE_LIMITS if dry_run else self.seeded_data

        # Display counts
        for entity in sorted(data.keys()):
            count = data.get(entity, 0)
            logger.info(f"{entity.replace('_', ' ').title():<35}: {count:>{10},}")

        logger.info("-" * 60)
        logger.info("📊 KEY RATIOS & METRICS")
        logger.info("-" * 60)

        # Calculate and display ratios
        students = data.get("students", 0)
        exams = data.get("exams", 0)
        rooms = data.get("rooms", 0)
        registrations = data.get("course_registrations", 0)

        total_seats = 0
        if not dry_run:
            async with db_manager.get_session() as session:
                total_seats_result = await session.execute(
                    select(func.sum(Room.exam_capacity))
                )
                total_seats = total_seats_result.scalar_one_or_none() or 0
        else:
            # Estimate for dry run
            total_seats = rooms * 60  # Assuming average exam capacity of 60

        logger.info(f"{'Total Students':<35}: {students:>{10},}")
        logger.info(f"{'Total Exams':<35}: {exams:>{10},}")
        logger.info(f"{'Total Rooms':<35}: {rooms:>{10},}")
        logger.info(f"{'Total Exam Seats Available':<35}: {total_seats:>{10},}")

        avg_students_per_exam = registrations / exams if exams > 0 else 0
        logger.info(f"{'Avg. Students per Exam':<35}: {avg_students_per_exam:>{10}.2f}")

        # Estimate peak concurrency
        exam_period_days = 14
        slots_per_day = 3
        total_slots = exam_period_days * slots_per_day
        peak_concurrent_exams = math.ceil(exams / total_slots) if total_slots > 0 else 0
        logger.info(
            f"{'Est. Peak Concurrent Exams':<35}: {peak_concurrent_exams:>{10},}"
        )

        logger.info("=" * 60)


async def main():
    """Main entry point to run the seeder from the command line."""
    parser = argparse.ArgumentParser(
        description="Seed the database with comprehensive fake data for the Exam Timetabling System.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--database-url",
        help="Database connection URL (overrides DATABASE_URL env var).",
    )
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Drop all existing data from tables before seeding.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing to the DB.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="A seed for the random number generator for reproducible results.",
    )
    parser.add_argument(
        "--magnitude",
        type=int,
        choices=[1, 2, 3, 4, 5],
        default=3,
        help="Data size magnitude: 1=Basic, 2=Small, 3=Medium, 4=Large, 5=Enterprise.",
    )
    args = parser.parse_args()

    seeder = ComprehensiveFakeSeeder(
        database_url=args.database_url, seed=args.seed, magnitude=args.magnitude
    )

    if args.dry_run:
        await seeder.run_dry()
    else:
        try:
            await seeder.run(drop_existing=args.drop_existing)
        except Exception:
            logger.critical("Seeding process failed. See error details above.")
            sys.exit(1)


if __name__ == "__main__":
    # Ensure the script can be run directly.
    # It assumes an asyncio-compatible environment.
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⏹️ Seeding interrupted by user.")
        sys.exit(1)
