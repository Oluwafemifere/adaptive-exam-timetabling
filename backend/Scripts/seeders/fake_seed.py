#!/usr/bin/env python3

# backend/Scripts/seeders/fake_seed.py
from uuid import uuid4
import uuid
import os
import sys
import asyncio
import logging
from pathlib import Path
from datetime import time, timedelta, datetime as dt_datetime, date
from random import choice, randint, sample
from typing import Any, Dict, Set, List, cast
from faker import Faker
from typing import TYPE_CHECKING
from sqlalchemy.exc import IntegrityError


if TYPE_CHECKING:
    from datetime import date
# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select, text, cast, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import ARRAY, TEXT
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload

# Import from the backend app
from app.database import db_manager
from app.models import (
    # Infrastructure
    Building,
    RoomType,
    Room,
    ExamRoom,
    ExamAllowedRoom,
    # Academic
    AcademicSession,
    Faculty,
    Department,
    Programme,
    TimeSlot,
    Course,
    Student,
    CourseRegistration,
    Exam,
    ExamDepartment,
    # Users and Staff
    User,
    UserRole,
    UserRoleAssignment,
    Staff,
    ExamInvigilator,
    StaffUnavailability,
    # System
    SystemConfiguration,
    SystemEvent,
    UserNotification,
    # Constraints
    ConstraintCategory,
    ConstraintRule,
    ConfigurationConstraint,
    # Jobs
    TimetableJob,
    TimetableVersion,
    # File uploads
    FileUploadSession,
    UploadedFile,
    # Audit and edits
    AuditLog,
    TimetableEdit,
    TimetableAssignment,
)

# Import core security functions
from app.core.security import hash_password
from app.database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

fake = Faker()

# REALISTIC SCALE LIMITS - Configurable based on environment
SCALE_LIMITS = {
    "faculties": int(os.getenv("SEED_FACULTIES", "8")),
    "departments": int(os.getenv("SEED_DEPARTMENTS", "35")),
    "programmes": int(os.getenv("SEED_PROGRAMMES", "80")),
    "buildings": int(os.getenv("SEED_BUILDINGS", "12")),
    "room_types": int(os.getenv("SEED_ROOM_TYPES", "8")),
    "rooms": int(os.getenv("SEED_ROOMS", "300")),
    "time_slots": int(os.getenv("SEED_TIME_SLOTS", "15")),
    "academic_sessions": int(os.getenv("SEED_SESSIONS", "3")),
    "courses": int(os.getenv("SEED_COURSES", "800")),
    "students": int(os.getenv("SEED_STUDENTS", "8000")),
    "course_registrations": int(os.getenv("SEED_REGISTRATIONS", "50000")),
    "exams": int(os.getenv("SEED_EXAMS", "800")),
    "staff": int(os.getenv("SEED_STAFF", "400")),
    "users": int(os.getenv("SEED_USERS", "500")),
    "user_roles": int(os.getenv("SEED_ROLES", "10")),
    "user_role_assignments": int(os.getenv("SEED_ROLE_ASSIGNMENTS", "600")),
    "audit_logs": int(os.getenv("SEED_AUDIT_LOGS", "500")),
    "timetable_edits": int(os.getenv("SEED_TIMETABLE_EDITS", "200")),
    "timetable_versions": int(os.getenv("SEED_VERSIONS", "5")),
    "system_configurations": int(os.getenv("SEED_CONFIGURATIONS", "3")),
    "constraint_categories": int(os.getenv("SEED_CONSTRAINT_CATEGORIES", "5")),
    "constraint_rules": int(os.getenv("SEED_CONSTRAINT_RULES", "20")),
    "configuration_constraints": int(os.getenv("SEED_CONFIG_CONSTRAINTS", "30")),
    "system_events": int(os.getenv("SEED_SYSTEM_EVENTS", "50")),
    "user_notifications": int(os.getenv("SEED_NOTIFICATIONS", "100")),
    "file_upload_sessions": int(os.getenv("SEED_UPLOAD_SESSIONS", "10")),
    "uploaded_files": int(os.getenv("SEED_UPLOADED_FILES", "20")),
    "exam_departments": int(os.getenv("SEED_EXAM_DEPARTMENTS", "400")),
    "exam_invigilators": int(os.getenv("SEED_INVIGILATORS", "500")),
    "staff_unavailability": int(os.getenv("SEED_UNAVAILABILITY", "200")),
    "timetable_assignments": int(os.getenv("SEED_ASSIGNMENTS", "300")),
    "exam_allowed_rooms": int(os.getenv("SEED_ALLOWED_ROOMS", "400")),
    "exam_rooms": int(os.getenv("SEED_EXAM_ROOMS", "500")),
    "timetable_jobs": int(os.getenv("SEED_TIMETABLE_JOBS", "5")),
}


def _to_date(value: Any) -> date:
    """Convert a value that may be a date or ISO string to a date."""
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except Exception:
            pass
        try:
            return dt_datetime.fromisoformat(value).date()
        except Exception:
            pass
        parts = value.split("-")
        try:
            if len(parts) >= 3:
                y, m, d = map(int, parts[:3])
                return date(y, m, d)
            if len(parts) == 1:
                y = int(parts[0])
                return date(y, 1, 1)
        except Exception:
            pass
    raise ValueError(f"Cannot convert {value!r} to date")


class ComprehensiveFakeSeeder:
    """
    Enhanced seeder that works with Alembic and the new model structure.
    Generates realistic fake data for testing and development.
    """

    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:password@localhost:5432/exam_system",
        )
        self.seeded_data: Dict[str, int] = {}
        self.generated_matrics: Set[str] = set()

    async def run(self, drop_existing: bool = False):
        """Main seeding process with Alembic integration"""
        logger.info("🚀 Starting comprehensive fake data seeding...")
        try:
            await init_db(database_url=self.database_url, create_tables=False)
            logger.info("✅ Database initialized")

            if drop_existing:
                logger.info("🧹 Clearing existing data...")
                await self._clear_all_data()

            # Seed in dependency order
            await self._seed_users_and_roles()
            await self._seed_system_configurations()
            await self._seed_constraints()
            await self._seed_infrastructure()
            await self._seed_academic_structure()
            await self._seed_time_slots()
            await self._seed_courses()
            await self._seed_students_and_registrations()
            await self._seed_staff()
            await self._seed_exams()
            await self._seed_exam_departments()
            await self._seed_exam_allowed_rooms()
            await self._seed_exam_rooms()
            await self._seed_exam_invigilators()
            await self._seed_staff_unavailability()
            await self._seed_timetable_jobs()
            await self._seed_timetable_versions()
            await self._seed_timetable_assignments()
            await self._seed_timetable_edits()
            await self._seed_file_uploads()
            await self._seed_system_events()
            await self._seed_user_notifications()
            await self._seed_audit_logs()

            logger.info("🎉 Comprehensive fake data seeding completed!")
            await self.print_summary()

        except IntegrityError as e:
            logger.error(f"Integrity error during seeding: {e}")
            # rollback only if you are in a session context
            async with db_manager.get_db_transaction() as session:
                await session.rollback()
            logger.info("Continuing with other seeding operations...")

        except Exception as e:
            logger.error(f"Unexpected error during seeding: {e}")
            raise

    async def _clear_all_data(self):
        """Clear all existing data to start fresh"""
        async with db_manager.get_db_transaction() as session:
            # Delete in reverse dependency order to respect foreign keys
            tables_to_clear = [
                "user_role_assignments",
                "user_notifications",
                "configuration_constraints",
                "constraint_rules",
                "constraint_categories",
                "system_configurations",
                "system_events",
                "exam_invigilators",
                "staff_unavailability",
                "staff",
                "timetable_assignments",
                "exam_rooms",
                "exam_allowed_rooms",
                "exam_departments",
                "course_registrations",
                "exams",
                "students",
                "courses",
                "programmes",
                "departments",
                "faculties",
                "time_slots",
                "rooms",
                "room_types",
                "buildings",
                "academic_sessions",
                "users",
                "user_roles",
                "file_upload_sessions",
                "uploaded_files",
                "timetable_jobs",
                "timetable_versions",
                "timetable_edits",
                "audit_logs",
            ]

            for table in tables_to_clear:
                try:
                    await session.execute(
                        text(f"TRUNCATE TABLE exam_system.{table} CASCADE")
                    )
                    logger.info(f"✓ Cleared {table}")
                except Exception as e:
                    logger.warning(f"Could not clear {table}: {e}")

        logger.info("🧹 Database cleared successfully")

    async def _get_count(self, session: AsyncSession, model_class) -> int:
        """Get current count of records for a model"""
        result = await session.execute(select(model_class))
        return len(result.scalars().all())

    async def _seed_users_and_roles(self):
        """Seed user roles and create admin user"""
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

            # Create roles
            roles = {}
            for name, desc, perms in roles_def:
                existing = (
                    await session.execute(select(UserRole).where(UserRole.name == name))
                ).scalar_one_or_none()

                if not existing:
                    role = UserRole(name=name, description=desc, permissions=perms)
                    session.add(role)
                    await session.flush()
                    roles[name] = role
                else:
                    roles[name] = existing

            # Create admin user
            admin_password_hash = hash_password("admin123")
            existing_admin = (
                await session.execute(
                    select(User).where(User.email == "admin@baze.edu.ng")
                )
            ).scalar_one_or_none()

            if not existing_admin:
                admin_user = User(
                    email="admin@baze.edu.ng",
                    first_name="System",
                    last_name="Administrator",
                    password_hash=admin_password_hash,
                    is_active=True,
                    is_superuser=True,
                )
                session.add(admin_user)
                await session.flush()

                # Assign super_admin role
                assignment = UserRoleAssignment(
                    user_id=admin_user.id, role_id=roles["super_admin"].id
                )
                session.add(assignment)

            # Generate additional fake users
            user_count = 0
            target_users = min(SCALE_LIMITS["users"], 500)

            for _ in range(target_users):
                if user_count >= target_users:
                    break

                email = fake.unique.email()
                existing = (
                    await session.execute(select(User).where(User.email == email))
                ).scalar_one_or_none()

                if not existing:
                    user = User(
                        email=email,
                        first_name=fake.first_name(),
                        last_name=fake.last_name(),
                        phone=fake.phone_number(),
                        password_hash=hash_password("password123"),
                        is_active=choice([True, True, True, False]),  # 75% active
                        is_superuser=False,
                    )
                    session.add(user)
                    user_count += 1

            self.seeded_data["users"] = user_count + 1  # +1 for admin
            self.seeded_data["user_roles"] = len(roles)
            logger.info(
                f"✓ Users and roles: {user_count + 1} users, {len(roles)} roles"
            )

    async def _seed_system_configurations(self):
        """Seed system configurations"""
        async with db_manager.get_db_transaction() as session:
            logger.info("⚙️ Seeding system configurations...")

            # Get admin user
            admin_user = (
                await session.execute(
                    select(User).where(User.email == "admin@baze.edu.ng")
                )
            ).scalar_one_or_none()

            if not admin_user:
                logger.error("Admin user not found for system configurations")
                return

            configs_created = 0
            config_names = [
                "Default Configuration",
                "High Priority Configuration",
                "Balanced Configuration",
                "Fast Scheduling Configuration",
            ]

            for name in config_names:
                if configs_created >= SCALE_LIMITS["system_configurations"]:
                    break

                existing = (
                    await session.execute(
                        select(SystemConfiguration).where(
                            SystemConfiguration.name == name
                        )
                    )
                ).scalar_one_or_none()

                if not existing:
                    config = SystemConfiguration(
                        name=name,
                        description=f"{name} for exam scheduling",
                        created_by=admin_user.id,
                        is_default=(name == "Default Configuration"),
                        solver_parameters={
                            "timeout": randint(300, 1800),
                            "optimization_level": choice(["high", "medium", "low"]),
                            "max_iterations": randint(1000, 10000),
                        },
                    )
                    session.add(config)
                    configs_created += 1

            self.seeded_data["system_configurations"] = configs_created
            logger.info(f"✓ System configurations: {configs_created} created")

    async def _seed_constraints(self):
        """Seed constraint categories, rules, and configuration constraints"""
        async with db_manager.get_db_transaction() as session:
            logger.info("🔒 Seeding constraints...")

            # Get configurations
            configs = (
                (await session.execute(select(SystemConfiguration))).scalars().all()
            )
            if not configs:
                logger.warning("No system configurations found for constraints")
                return

            # Constraint categories
            categories_created = 0
            category_data = [
                ("Temporal", "Time-related constraints"),
                ("Spatial", "Room and location constraints"),
                ("Resource", "Resource allocation constraints"),
                ("Pedagogical", "Educational constraints"),
                ("Administrative", "Administrative constraints"),
            ]

            categories = {}
            for name, desc in category_data:
                if categories_created >= SCALE_LIMITS["constraint_categories"]:
                    break

                existing = (
                    await session.execute(
                        select(ConstraintCategory).where(
                            ConstraintCategory.name == name
                        )
                    )
                ).scalar_one_or_none()

                if not existing:
                    category = ConstraintCategory(
                        name=name,
                        description=desc,
                        enforcement_layer=choice(["solver", "validation", "both"]),
                    )
                    session.add(category)
                    await session.flush()
                    categories[name] = category
                    categories_created += 1
                else:
                    categories[name] = existing

            # Constraint rules
            rules_created = 0
            rule_data = [
                # Temporal constraints
                (
                    "NO_EXAM_OVERLAP",
                    "No overlapping exams for students",
                    "hard",
                    "Temporal",
                ),
                (
                    "MAX_EXAMS_PER_DAY",
                    "Maximum exams per day for students",
                    "soft",
                    "Temporal",
                ),
                (
                    "MIN_GAP_BETWEEN_EXAMS",
                    "Minimum gap between exams",
                    "soft",
                    "Temporal",
                ),
                # Spatial constraints
                ("ROOM_CAPACITY", "Room capacity not exceeded", "hard", "Spatial"),
                (
                    "ROOM_AVAILABILITY",
                    "Room available at scheduled time",
                    "hard",
                    "Spatial",
                ),
                (
                    "SPECIAL_ROOM_REQUIREMENTS",
                    "Special room requirements met",
                    "hard",
                    "Spatial",
                ),
                # Resource constraints
                (
                    "INVIGILATOR_AVAILABILITY",
                    "Invigilator available",
                    "soft",
                    "Resource",
                ),
                (
                    "MAX_INVIGILATOR_LOAD",
                    "Maximum invigilator load",
                    "soft",
                    "Resource",
                ),
                # Pedagogical constraints
                (
                    "COMMON_EXAMS_SAME_TIME",
                    "Common exams at same time",
                    "hard",
                    "Pedagogical",
                ),
                (
                    "SAME_DEPARTMENT_SPACING",
                    "Spacing for same department exams",
                    "soft",
                    "Pedagogical",
                ),
                # Administrative constraints
                (
                    "PREFERRED_TIME_SLOTS",
                    "Preferred time slots",
                    "soft",
                    "Administrative",
                ),
                (
                    "AVOID_CERTAIN_TIMES",
                    "Avoid certain times",
                    "soft",
                    "Administrative",
                ),
            ]

            rules = {}
            for code, name, c_type, category_name in rule_data:
                if rules_created >= SCALE_LIMITS["constraint_rules"]:
                    break

                category = categories.get(category_name)
                if not category:
                    continue

                existing = (
                    await session.execute(
                        select(ConstraintRule).where(ConstraintRule.code == code)
                    )
                ).scalar_one_or_none()

                if not existing:
                    rule = ConstraintRule(
                        code=code,
                        name=name,
                        constraint_type=c_type,
                        constraint_definition={
                            "parameters": {
                                "weight": round(randint(1, 10) / 10, 1),
                                "priority": choice(["high", "medium", "low"]),
                            }
                        },
                        category_id=category.id,
                        default_weight=round(randint(1, 10) / 10, 1),
                        is_active=True,
                        is_configurable=choice([True, False]),
                    )
                    session.add(rule)
                    await session.flush()
                    rules[code] = rule
                    rules_created += 1
                else:
                    rules[code] = existing

            # Configuration constraints
            config_constraints_created = 0
            for config in configs:
                for rule_code, rule in rules.items():
                    if (
                        config_constraints_created
                        >= SCALE_LIMITS["configuration_constraints"]
                    ):
                        break

                    existing = (
                        await session.execute(
                            select(ConfigurationConstraint).where(
                                ConfigurationConstraint.configuration_id == config.id,
                                ConfigurationConstraint.constraint_id == rule.id,
                            )
                        )
                    ).scalar_one_or_none()

                    if not existing:
                        config_constraint = ConfigurationConstraint(
                            configuration_id=config.id,
                            constraint_id=rule.id,
                            custom_parameters={
                                "enabled": choice([True, False]),
                                "weight": round(randint(1, 10) / 10, 1),
                            },
                            weight=round(randint(1, 10) / 10, 1),
                            is_enabled=choice([True, False]),
                        )
                        session.add(config_constraint)
                        config_constraints_created += 1

            self.seeded_data["constraint_categories"] = categories_created
            self.seeded_data["constraint_rules"] = rules_created
            self.seeded_data["configuration_constraints"] = config_constraints_created
            logger.info(
                f"✓ Constraints: {categories_created} categories, {rules_created} rules, {config_constraints_created} config constraints"
            )

    async def _seed_infrastructure(self):
        """Seed buildings, room types, and rooms with realistic data"""
        async with db_manager.get_db_transaction() as session:
            logger.info("🏢 Seeding infrastructure...")

            # Buildings - realistic university buildings
            building_data = [
                ("ENG", "Engineering Complex"),
                ("SCI", "Science Building"),
                ("MGT", "Management Building"),
                ("LIB", "Central Library"),
                ("MED", "Medical Sciences"),
                ("LAW", "Law Faculty"),
                ("ART", "Arts & Humanities"),
                ("SOC", "Social Sciences"),
                ("TECH", "Technology Center"),
                ("ADMIN", "Administration Block"),
                ("SPORT", "Sports Complex"),
                ("HALL", "Main Auditorium"),
            ]

            buildings = {}
            for code, name in building_data:
                if len(buildings) >= SCALE_LIMITS["buildings"]:
                    break

                existing = (
                    (
                        await session.execute(
                            select(Building).where(Building.code == code)
                        )
                    )
                    .scalars()
                    .first()
                )

                if not existing:
                    b = Building(code=code, name=name, is_active=True)
                    session.add(b)
                    await session.flush()
                    buildings[code] = b
                else:
                    buildings[code] = existing

            # Room Types
            room_type_data = [
                ("Classroom", "Standard lecture room"),
                ("Laboratory", "Science/computer lab"),
                ("Auditorium", "Large presentation hall"),
                ("Seminar", "Small discussion room"),
                ("Workshop", "Hands-on learning space"),
                ("Library", "Study and research space"),
                ("Office", "Faculty/admin office"),
                ("Conference", "Meeting room"),
            ]

            room_types = {}
            for name, desc in room_type_data:
                if len(room_types) >= SCALE_LIMITS["room_types"]:
                    break

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
                else:
                    room_types[name] = existing

            # Rooms - generate realistic room distribution
            rooms_created = 0
            for building_code, building in buildings.items():
                if rooms_created >= SCALE_LIMITS["rooms"]:
                    break

                # Different buildings have different room counts
                if building_code in ["LIB", "ADMIN", "SPORT"]:
                    room_count = randint(8, 15)
                elif building_code in ["ENG", "SCI", "MED"]:
                    room_count = randint(25, 40)
                else:
                    room_count = randint(15, 25)

                for i in range(1, room_count + 1):
                    if rooms_created >= SCALE_LIMITS["rooms"]:
                        break

                    room_code = f"{building_code}{i:03d}"
                    existing = (
                        (
                            await session.execute(
                                select(Room).where(Room.code == room_code)
                            )
                        )
                        .scalars()
                        .first()
                    )

                    if not existing:
                        # Assign room type based on building
                        if building_code == "ENG":
                            rt_name = choice(["Classroom", "Laboratory", "Workshop"])
                        elif building_code == "SCI":
                            rt_name = choice(["Classroom", "Laboratory"])
                        elif building_code == "LIB":
                            rt_name = choice(["Library", "Seminar"])
                        else:
                            rt_name = choice(["Classroom", "Seminar", "Conference"])

                        room_type = room_types.get(
                            rt_name, list(room_types.values())[0]
                        )

                        # Capacity based on room type
                        if rt_name == "Auditorium":
                            capacity = randint(200, 500)
                        elif rt_name == "Classroom":
                            capacity = randint(30, 100)
                        elif rt_name == "Laboratory":
                            capacity = randint(20, 50)
                        else:
                            capacity = randint(15, 40)

                        r = Room(
                            code=room_code,
                            name=f"{building.name} Room {i}",
                            capacity=capacity,
                            exam_capacity=int(capacity * 0.7),  # 70% for exams
                            floor_number=((i - 1) // 20) + 1,
                            has_projector=choice([True, False]),
                            has_ac=choice([True, False]),
                            has_computers=rt_name == "Laboratory",
                            building_id=building.id,
                            room_type_id=room_type.id,
                            is_active=True,
                            overbookable=choice([True, False]),
                            max_inv_per_room=randint(1, 5),
                            adjacency_pairs=(
                                {
                                    "adjacent_rooms": [
                                        f"{building_code}{j:03d}"
                                        for j in range(
                                            max(1, i - 2), min(room_count + 1, i + 3)
                                        )
                                        if j != i
                                    ]
                                }
                                if randint(1, 4) == 1
                                else None
                            ),
                            notes=fake.sentence() if randint(1, 5) == 1 else None,
                        )
                        session.add(r)
                        rooms_created += 1

            self.seeded_data["buildings"] = len(buildings)
            self.seeded_data["room_types"] = len(room_types)
            self.seeded_data["rooms"] = rooms_created
            logger.info(
                f"✓ Infrastructure: {len(buildings)} buildings, {len(room_types)} room types, {rooms_created} rooms"
            )

    async def _seed_academic_structure(self):
        """Seed faculties, departments, programmes, and academic sessions"""
        async with db_manager.get_db_transaction() as session:
            logger.info("🎓 Seeding academic structure...")

            # Faculties
            faculty_data = [
                ("ENG", "Faculty of Engineering"),
                ("SCI", "Faculty of Sciences"),
                ("MGT", "Faculty of Management"),
                ("MED", "Faculty of Medicine"),
                ("LAW", "Faculty of Law"),
                ("ART", "Faculty of Arts"),
                ("SOC", "Faculty of Social Sciences"),
                ("EDU", "Faculty of Education"),
            ]

            faculties = {}
            for code, name in faculty_data:
                if len(faculties) >= SCALE_LIMITS["faculties"]:
                    break

                existing = (
                    (await session.execute(select(Faculty).where(Faculty.code == code)))
                    .scalars()
                    .first()
                )

                if not existing:
                    f = Faculty(code=code, name=name, is_active=True)
                    session.add(f)
                    await session.flush()
                    faculties[code] = f
                else:
                    faculties[code] = existing

            # Departments
            dept_data = {
                "ENG": [
                    ("CPE", "Computer Engineering"),
                    ("CVE", "Civil Engineering"),
                    ("MEE", "Mechanical Engineering"),
                    ("EEE", "Electrical Engineering"),
                    ("CHE", "Chemical Engineering"),
                ],
                "SCI": [
                    ("CSC", "Computer Science"),
                    ("MAT", "Mathematics"),
                    ("PHY", "Physics"),
                    ("CHM", "Chemistry"),
                    ("BIO", "Biology"),
                    ("STA", "Statistics"),
                ],
                "MGT": [
                    ("ACC", "Accounting"),
                    ("BUS", "Business Admin"),
                    ("ECO", "Economics"),
                    ("FIN", "Finance"),
                    ("MKT", "Marketing"),
                ],
                "MED": [
                    ("MDC", "Medicine"),
                    ("NUR", "Nursing"),
                    ("PHA", "Pharmacy"),
                    ("DEN", "Dentistry"),
                ],
                "LAW": [("LAW", "Law")],
                "ART": [
                    ("ENG", "English"),
                    ("HIS", "History"),
                    ("PHI", "Philosophy"),
                    ("MUS", "Music"),
                    ("ART", "Fine Arts"),
                ],
                "SOC": [
                    ("PSY", "Psychology"),
                    ("SOC", "Sociology"),
                    ("POL", "Political Science"),
                    ("ANT", "Anthropology"),
                ],
                "EDU": [("EDU", "Education"), ("PED", "Physical Education")],
            }

            departments = {}
            dept_count = 0
            for fac_code, depts in dept_data.items():
                if dept_count >= SCALE_LIMITS["departments"]:
                    break

                faculty = faculties.get(fac_code)
                if not faculty:
                    continue

                for dept_code, dept_name in depts:
                    if dept_count >= SCALE_LIMITS["departments"]:
                        break

                    full_code = f"{fac_code}_{dept_code}"
                    existing = (
                        (
                            await session.execute(
                                select(Department).where(
                                    Department.code == dept_code,
                                    Department.faculty_id == faculty.id,
                                )
                            )
                        )
                        .scalars()
                        .first()
                    )

                    if not existing:
                        d = Department(
                            code=dept_code,
                            name=dept_name,
                            faculty_id=faculty.id,
                            is_active=True,
                        )
                        session.add(d)
                        await session.flush()
                        departments[full_code] = d
                        dept_count += 1
                    else:
                        departments[full_code] = existing

            # Programmes
            programmes = {}
            prog_count = 0
            for dept_key, dept in departments.items():
                if prog_count >= SCALE_LIMITS["programmes"]:
                    break

                # Create 1-3 programmes per department
                prog_types = [("undergraduate", 4), ("postgraduate", 2)]
                for degree_type, duration in prog_types:
                    if prog_count >= SCALE_LIMITS["programmes"]:
                        break

                    # Generate programme names based on department
                    if degree_type == "undergraduate":
                        prog_name = f"Bachelor of {dept.name}"
                        prog_code = f"B{dept.code}"
                    else:
                        prog_name = f"Master of {dept.name}"
                        prog_code = f"M{dept.code}"

                    existing = (
                        (
                            await session.execute(
                                select(Programme).where(Programme.code == prog_code)
                            )
                        )
                        .scalars()
                        .first()
                    )

                    if not existing:
                        p = Programme(
                            code=prog_code,
                            name=prog_name,
                            department_id=dept.id,
                            degree_type=degree_type,
                            duration_years=duration,
                            is_active=True,
                        )
                        session.add(p)
                        await session.flush()
                        programmes[prog_code] = p
                        prog_count += 1
                    else:
                        programmes[prog_code] = existing

            # Academic Sessions
            sessions = {}
            current_year = date.today().year
            for i in range(SCALE_LIMITS["academic_sessions"]):
                year = current_year - i
                session_name = f"{year}/{year+1}"

                existing = (
                    (
                        await session.execute(
                            select(AcademicSession).where(
                                AcademicSession.name == session_name
                            )
                        )
                    )
                    .scalars()
                    .first()
                )

                if not existing:
                    s = AcademicSession(
                        name=session_name,
                        semester_system=choice(["semester", "trimester"]),
                        start_date=date(year, 9, 1),
                        end_date=date(year + 1, 8, 31),
                        is_active=(i == 0),  # Only current year is active
                    )
                    session.add(s)
                    await session.flush()
                    sessions[session_name] = s
                else:
                    sessions[session_name] = existing

            self.seeded_data["faculties"] = len(faculties)
            self.seeded_data["departments"] = dept_count
            self.seeded_data["programmes"] = prog_count
            self.seeded_data["academic_sessions"] = len(sessions)
            logger.info(
                f"✓ Academic: {len(faculties)} faculties, {dept_count} departments, {prog_count} programmes, {len(sessions)} sessions"
            )

    async def _seed_time_slots(self):
        """Seed comprehensive time slots"""
        async with db_manager.get_db_transaction() as session:
            logger.info("⏰ Seeding time slots...")

            time_slots_data = [
                ("Early Morning", time(7, 0), time(10, 0)),
                ("Morning", time(8, 0), time(11, 0)),
                ("Mid Morning", time(9, 0), time(12, 0)),
                ("Late Morning", time(10, 0), time(13, 0)),
                ("Early Afternoon", time(12, 0), time(15, 0)),
                ("Afternoon", time(13, 0), time(16, 0)),
                ("Mid Afternoon", time(14, 0), time(17, 0)),
                ("Late Afternoon", time(15, 0), time(18, 0)),
                ("Early Evening", time(16, 0), time(19, 0)),
                ("Evening", time(17, 0), time(20, 0)),
                ("Night", time(18, 0), time(21, 0)),
                # Weekend slots
                ("Weekend Morning", time(9, 0), time(12, 0)),
                ("Weekend Afternoon", time(14, 0), time(17, 0)),
                ("Weekend Evening", time(18, 0), time(21, 0)),
                # Extended slots for long exams
                ("Extended Morning", time(8, 0), time(12, 30)),
            ]

            slots_created = 0
            for name, start_time, end_time in time_slots_data:
                if slots_created >= SCALE_LIMITS["time_slots"]:
                    break

                existing = (
                    (
                        await session.execute(
                            select(TimeSlot).where(TimeSlot.name == name)
                        )
                    )
                    .scalars()
                    .first()
                )

                if not existing:
                    duration = int(
                        (
                            dt_datetime.combine(date.today(), end_time)
                            - dt_datetime.combine(date.today(), start_time)
                        ).total_seconds()
                        / 60
                    )

                    ts = TimeSlot(
                        name=name,
                        start_time=start_time,
                        end_time=end_time,
                        duration_minutes=duration,
                        is_active=True,
                    )
                    session.add(ts)
                    slots_created += 1

            self.seeded_data["time_slots"] = slots_created
            logger.info(f"✓ Time Slots: {slots_created} slots created")

    async def _seed_courses(self):
        """Seed courses for all departments"""
        async with db_manager.get_db_transaction() as session:
            logger.info("📚 Seeding courses...")

            # Get all departments
            departments = (await session.execute(select(Department))).scalars().all()

            course_subjects = [
                "Introduction",
                "Advanced",
                "Applied",
                "Theoretical",
                "Practical",
                "Research",
                "Project",
                "Seminar",
                "Laboratory",
                "Workshop",
                "Methods",
                "Analysis",
                "Design",
                "Systems",
                "Management",
            ]

            courses_created = 0
            for dept in departments:
                if courses_created >= SCALE_LIMITS["courses"]:
                    break

                # Each department gets 15-25 courses
                dept_course_count = randint(15, 25)
                for i in range(dept_course_count):
                    if courses_created >= SCALE_LIMITS["courses"]:
                        break

                    # Generate course levels (100-500)
                    level = choice([100, 200, 300, 400, 500])
                    course_code = f"{dept.code}{level}{i+1:02d}"

                    existing = (
                        (
                            await session.execute(
                                select(Course).where(Course.code == course_code)
                            )
                        )
                        .scalars()
                        .first()
                    )

                    if not existing:
                        subject = choice(course_subjects)
                        specialty = fake.word().capitalize()
                        title = f"{subject} {specialty} in {dept.name}"

                        c = Course(
                            code=course_code,
                            title=title[:300],  # Ensure it fits in varchar(300)
                            credit_units=choice([2, 3, 4, 5, 6]),
                            course_level=level,
                            semester=choice([1, 2, 3]),
                            is_practical=choice([True, False]),
                            morning_only=(
                                choice([True, False]) if level >= 300 else False
                            ),
                            exam_duration_minutes=choice([120, 150, 180, 210]),
                            department_id=dept.id,
                            is_active=True,
                        )
                        session.add(c)
                        courses_created += 1

            self.seeded_data["courses"] = courses_created
            logger.info(f"✓ Courses: {courses_created} courses created")

    async def _seed_students_and_registrations(self):
        """Seed students and their course registrations"""
        async with db_manager.get_db_transaction() as session:
            logger.info("👨‍🎓 Seeding students and registrations...")

            programmes = (await session.execute(select(Programme))).scalars().all()
            courses = (await session.execute(select(Course))).scalars().all()
            active_session = (
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

            if not active_session:
                logger.error("No active academic session found")
                return

            current_year = date.today().year
            batch_size = 500
            target_students = min(SCALE_LIMITS["students"], 8000)
            students_created = 0
            registration_count = 0

            # Safe unique list of department codes used for matric generation
            dept_codes = [
                row[0]
                for row in (
                    await session.execute(
                        text(
                            "SELECT DISTINCT d.code FROM exam_system.departments d "
                            "JOIN exam_system.programmes p ON p.department_id=d.id"
                        )
                    )
                ).all()
            ]

            if not dept_codes:
                logger.error("No department codes found")
                return

            for _batch_idx in range((target_students // batch_size) + 1):
                if students_created >= target_students:
                    break

                batch_students = []
                for _ in range(batch_size):
                    if students_created >= target_students:
                        break

                    # Generate a unique matric string with bounded attempts
                    attempts = 0
                    matric = None
                    year = None
                    while attempts < 10:
                        y = randint(current_year - 6, current_year)
                        dept_code = choice(dept_codes)
                        sequence = randint(100, 999)
                        candidate = f"BU/{y}/{dept_code}/{sequence:03d}"

                        if candidate in self.generated_matrics:
                            attempts += 1
                            continue

                        existing = (
                            (
                                await session.execute(
                                    select(Student).where(
                                        Student.matric_number == candidate
                                    )
                                )
                            )
                            .scalars()
                            .first()
                        )

                        if not existing:
                            matric = candidate
                            year = y
                            self.generated_matrics.add(candidate)
                            break
                        attempts += 1

                    if matric is None or attempts >= 10:
                        continue

                    programme = choice(programmes)
                    assert year is not None
                    entry_year = randint(year - 1, year)

                    # Determine current level safely
                    years_since_entry = current_year - entry_year
                    if programme.degree_type == "undergraduate":
                        if years_since_entry >= 3:
                            current_level = choice([300, 400])
                        elif years_since_entry >= 2:
                            current_level = choice([200, 300])
                        elif years_since_entry >= 1:
                            current_level = choice([100, 200])
                        else:
                            current_level = 100
                    else:
                        current_level = choice([500, 600])

                    student = Student(
                        matric_number=matric,
                        entry_year=entry_year,
                        current_level=current_level,
                        student_type=choice(["regular", "transfer"]),
                        special_needs=cast([], ARRAY(TEXT)),
                        programme_id=programme.id,
                        is_active=True,
                    )
                    session.add(student)
                    batch_students.append(student)
                    students_created += 1

                # Flush to obtain student IDs
                await session.flush()

                # Create registrations for flushed students
                for student in batch_students:
                    eligible_courses = [
                        c
                        for c in courses
                        if c.course_level <= student.current_level
                        and c.department_id == student.programme.department_id
                    ]

                    if not eligible_courses:
                        continue

                    num_courses = min(randint(5, 8), len(eligible_courses))
                    selected_courses = sample(eligible_courses, num_courses)

                    for course in selected_courses:
                        existing_reg = (
                            (
                                await session.execute(
                                    select(CourseRegistration).where(
                                        CourseRegistration.student_id == student.id,
                                        CourseRegistration.course_id == course.id,
                                        CourseRegistration.session_id
                                        == active_session.id,
                                    )
                                )
                            )
                            .scalars()
                            .first()
                        )

                        if not existing_reg:
                            reg = CourseRegistration(
                                student_id=student.id,
                                course_id=course.id,
                                session_id=active_session.id,
                                registration_type=choice(["regular", "retake"]),
                                registered_at=fake.date_time_this_year(),
                            )
                            session.add(reg)
                            registration_count += 1

                if students_created % 1000 == 0:
                    logger.info(
                        f"Progress: {students_created} students, {registration_count} registrations"
                    )

            self.seeded_data["students"] = students_created
            self.seeded_data["course_registrations"] = registration_count
            logger.info(
                f"✓ Students: {students_created} students, {registration_count} registrations"
            )

    async def _seed_staff(self):
        """Seed staff members"""
        async with db_manager.get_db_transaction() as session:
            logger.info("👨‍🏫 Seeding staff...")

            departments = (await session.execute(select(Department))).scalars().all()
            users = (await session.execute(select(User))).scalars().all()

            staff_created = 0
            staff_types = ["academic", "administrative", "technical", "support"]

            for _ in range(SCALE_LIMITS["staff"]):
                if staff_created >= SCALE_LIMITS["staff"]:
                    break

                staff_number = f"ST{fake.unique.numerify(text='#######')}"
                existing = (
                    await session.execute(
                        select(Staff).where(Staff.staff_number == staff_number)
                    )
                ).scalar_one_or_none()

                if not existing:
                    staff = Staff(
                        staff_number=staff_number,
                        department_id=choice(departments).id if departments else None,
                        position=fake.job(),
                        staff_type=choice(staff_types),
                        can_invigilate=choice([True, False]),
                        max_daily_sessions=randint(1, 3),
                        max_consecutive_sessions=randint(1, 2),
                        is_active=True,
                        user_id=choice(users).id if users else None,
                    )
                    session.add(staff)
                    staff_created += 1

            self.seeded_data["staff"] = staff_created
            logger.info(f"✓ Staff: {staff_created} staff members created")

    async def _seed_exams(self):
        """Seed exams for courses"""
        async with db_manager.get_db_transaction() as session:
            logger.info("📝 Seeding exams...")

            courses = (await session.execute(select(Course))).scalars().all()
            time_slots = (await session.execute(select(TimeSlot))).scalars().all()
            active_session = (
                (
                    await session.execute(
                        select(AcademicSession).where(
                            AcademicSession.is_active == true()
                        )
                    )
                )
                .scalars()
                .first()
            )

            if not active_session or not time_slots:
                logger.error("Missing required data for exam seeding")
                return

            # Check if active_session has a start_date
            if active_session.start_date is None:
                logger.error("Active session has no start date")
                return

            start_date = _to_date(active_session.start_date)
            exam_period_start = start_date + timedelta(
                days=60
            )  # Exams start 2 months after session
            exam_period_end = start_date + timedelta(
                days=240
            )  # End 8 months after session

            exams_created = 0
            # Create exams for 70% of courses (not all courses have exams)
            exam_courses = sample(courses, int(len(courses) * 0.7))

            for course in exam_courses:
                if exams_created >= SCALE_LIMITS["exams"]:
                    break

                existing_exam = (
                    (
                        await session.execute(
                            select(Exam).where(
                                Exam.course_id == course.id,
                                Exam.session_id == active_session.id,
                            )
                        )
                    )
                    .scalars()
                    .first()
                )

                if not existing_exam:
                    # Random exam date within exam period
                    days_range = (exam_period_end - exam_period_start).days
                    exam_date = exam_period_start + timedelta(
                        days=randint(0, days_range)
                    )

                    # Get expected students for this course
                    reg_count = (
                        (
                            await session.execute(
                                select(CourseRegistration).where(
                                    CourseRegistration.course_id == course.id,
                                    CourseRegistration.session_id == active_session.id,
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )

                    expected_students = (
                        len(reg_count) if reg_count else randint(10, 100)
                    )

                    exam = Exam(
                        course_id=course.id,
                        session_id=active_session.id,
                        exam_date=exam_date,
                        time_slot_id=choice(time_slots).id,
                        duration_minutes=course.exam_duration_minutes
                        or choice([120, 180]),
                        expected_students=expected_students,
                        requires_special_arrangements=choice([True, False]),
                        status=choice(["pending", "scheduled", "confirmed"]),
                        notes=(
                            f"Exam for {course.title}" if randint(1, 3) == 1 else None
                        ),
                        is_practical=course.is_practical,
                        requires_projector=choice([True, False]),
                        is_common=choice([True, False]),
                    )
                    session.add(exam)
                    exams_created += 1

            self.seeded_data["exams"] = exams_created
            logger.info(f"✓ Exams: {exams_created} exams created")

    async def _seed_exam_departments(self):
        """Seed exam departments using proper async pattern"""
        async with db_manager.get_db_transaction() as session:
            logger.info("🏫 Seeding exam departments...")
            logger.info(f"Target limit: {SCALE_LIMITS['exam_departments']}")

            try:
                # Get all exams and departments
                logger.info("Fetching exams...")
                # Use selectinload to eagerly load course and department relationships
                exams_result = await session.execute(
                    select(Exam).options(
                        selectinload(Exam.course).selectinload(Course.department)
                    )
                )
                exams = exams_result.scalars().all()
                logger.info(f"Found {len(exams)} exams")

                logger.info("Fetching departments...")
                departments_result = await session.execute(select(Department))
                departments = departments_result.scalars().all()
                logger.info(f"Found {len(departments)} departments")

                if not exams or not departments:
                    logger.error(
                        "No exams or departments found for seeding exam departments"
                    )
                    return

                exam_deps_created = 0
                batch_count = 0

                for exam in exams:
                    if exam_deps_created >= SCALE_LIMITS["exam_departments"]:
                        logger.info(
                            f"Reached target limit of {SCALE_LIMITS['exam_departments']}"
                        )
                        break

                    # Each exam belongs to at least the course's department
                    course_dept_id = exam.course.department_id
                    logger.debug(
                        f"Processing exam {exam.id}, course department: {course_dept_id}"
                    )

                    # Check if relationship already exists
                    existing = await session.execute(
                        select(ExamDepartment).where(
                            ExamDepartment.exam_id == exam.id,
                            ExamDepartment.department_id == course_dept_id,
                        )
                    )
                    existing_record = existing.scalar_one_or_none()

                    if not existing_record:
                        exam_dep = ExamDepartment(
                            exam_id=exam.id, department_id=course_dept_id
                        )
                        session.add(exam_dep)
                        exam_deps_created += 1
                        logger.debug(
                            f"Added primary department relationship for exam {exam.id}"
                        )
                    else:
                        logger.debug(
                            f"Primary department relationship already exists for exam {exam.id}"
                        )

                    # Some exams might involve multiple departments
                    if randint(1, 5) == 1:  # 20% chance
                        extra_deps = sample(
                            [d for d in departments if d.id != course_dept_id],
                            randint(1, 2),
                        )
                        for dep in extra_deps:
                            if exam_deps_created >= SCALE_LIMITS["exam_departments"]:
                                break

                            # Check if relationship already exists
                            existing_extra = await session.execute(
                                select(ExamDepartment).where(
                                    ExamDepartment.exam_id == exam.id,
                                    ExamDepartment.department_id == dep.id,
                                )
                            )
                            existing_extra_record = existing_extra.scalar_one_or_none()

                            if not existing_extra_record:
                                exam_dep_extra = ExamDepartment(
                                    exam_id=exam.id, department_id=dep.id
                                )
                                session.add(exam_dep_extra)
                                exam_deps_created += 1
                                logger.debug(
                                    f"Added extra department {dep.id} for exam {exam.id}"
                                )

                    # Commit in batches to avoid memory issues
                    if exam_deps_created % 100 == 0:
                        batch_count += 1
                        logger.info(
                            f"Flushing batch {batch_count}, created {exam_deps_created} so far"
                        )
                        await session.flush()

                await session.flush()
                self.seeded_data["exam_departments"] = exam_deps_created
                logger.info(
                    f"✓ Exam departments: {exam_deps_created} relationships created"
                )

            except Exception as e:
                logger.error(f"Error in _seed_exam_departments: {e}")
                logger.error(f"Error type: {type(e).__name__}")
                import traceback

                logger.error(f"Traceback: {traceback.format_exc()}")
                raise

    async def run_parallel(self, drop_existing: bool = False):
        """Run seeding with parallel execution where possible"""
        logger.info("🚀 Starting parallel fake data seeding...")

        if drop_existing:
            await self._clear_all_data()
        # Test database connection first
        try:
            async with db_manager.get_db_transaction() as session:
                await session.execute(text("SELECT 1"))
            logger.info("✅ Database connection test successful")
        except Exception as e:
            logger.error(f"❌ Database connection test failed: {e}")
            return
        # Group seeding tasks by dependencies
        parallel_tasks = [
            self._seed_users_and_roles(),
            self._seed_system_configurations(),
            self._seed_constraints(),
            self._seed_infrastructure(),
            self._seed_academic_structure(),
        ]

        # Run initial independent tasks in parallel
        await asyncio.gather(*parallel_tasks)

        # Run dependent tasks sequentially
        await self._seed_time_slots()
        await self._seed_courses()
        await self._seed_students_and_registrations()
        await self._seed_staff()
        await self._seed_exams()

        # Run these in parallel as they don't depend on each other
        parallel_tasks2 = [
            self._seed_exam_departments(),
            self._seed_exam_allowed_rooms(),
            self._seed_exam_rooms(),
            self._seed_exam_invigilators(),
            self._seed_staff_unavailability(),
        ]
        await asyncio.gather(*parallel_tasks2)

        # Final sequential tasks
        await self._seed_timetable_jobs()
        await self._seed_timetable_versions()
        await self._seed_timetable_assignments()
        await self._seed_timetable_edits()
        await self._seed_file_uploads()
        await self._seed_system_events()
        await self._seed_user_notifications()
        await self._seed_audit_logs()

        logger.info("🎉 Parallel fake data seeding completed!")
        await self.print_summary()

    async def _seed_exam_allowed_rooms(self):
        """Seed exam allowed rooms"""
        async with db_manager.get_db_transaction() as session:
            logger.info("🚪 Seeding exam allowed rooms...")

            exams = (await session.execute(select(Exam))).scalars().all()
            rooms = (await session.execute(select(Room))).scalars().all()

            allowed_rooms_created = 0

            for exam in exams:
                if allowed_rooms_created >= SCALE_LIMITS["exam_allowed_rooms"]:
                    break

                # Each exam can have 1-5 allowed rooms
                num_rooms = randint(1, 5)
                selected_rooms = sample(rooms, min(num_rooms, len(rooms)))

                for room in selected_rooms:
                    if allowed_rooms_created >= SCALE_LIMITS["exam_allowed_rooms"]:
                        break

                    existing = (
                        await session.execute(
                            select(ExamAllowedRoom).where(
                                ExamAllowedRoom.exam_id == exam.id,
                                ExamAllowedRoom.room_id == room.id,
                            )
                        )
                    ).scalar_one_or_none()

                    if not existing:
                        allowed_room = ExamAllowedRoom(exam_id=exam.id, room_id=room.id)
                        session.add(allowed_room)
                        allowed_rooms_created += 1

            self.seeded_data["exam_allowed_rooms"] = allowed_rooms_created
            logger.info(
                f"✓ Exam allowed rooms: {allowed_rooms_created} relationships created"
            )

    async def _seed_exam_rooms(self):
        """Seed exam rooms"""
        async with db_manager.get_db_transaction() as session:
            logger.info("🪑 Seeding exam rooms...")

            exams = (await session.execute(select(Exam))).scalars().all()
            rooms = (await session.execute(select(Room))).scalars().all()

            exam_rooms_created = 0

            for exam in exams:
                if exam_rooms_created >= SCALE_LIMITS["exam_rooms"]:
                    break

                # Each exam can have 1-3 rooms
                num_rooms = randint(1, 3)
                selected_rooms = sample(rooms, min(num_rooms, len(rooms)))

                for i, room in enumerate(selected_rooms):
                    if exam_rooms_created >= SCALE_LIMITS["exam_rooms"]:
                        break

                    existing = (
                        await session.execute(
                            select(ExamRoom).where(
                                ExamRoom.exam_id == exam.id, ExamRoom.room_id == room.id
                            )
                        )
                    ).scalar_one_or_none()

                    if not existing:
                        exam_room = ExamRoom(
                            exam_id=exam.id,
                            room_id=room.id,
                            allocated_capacity=min(
                                room.exam_capacity or room.capacity,
                                exam.expected_students // num_rooms + randint(-10, 10),
                            ),
                            is_primary=(i == 0),
                            seating_arrangement=(
                                {
                                    "rows": randint(5, 20),
                                    "columns": randint(5, 10),
                                    "spacing": choice(["normal", "social_distancing"]),
                                }
                                if randint(1, 3) == 1
                                else None
                            ),
                        )
                        session.add(exam_room)
                        exam_rooms_created += 1

            self.seeded_data["exam_rooms"] = exam_rooms_created
            logger.info(f"✓ Exam rooms: {exam_rooms_created} assignments created")

    async def _seed_exam_invigilators(self):
        """Seed exam invigilators"""
        async with db_manager.get_db_transaction() as session:
            logger.info("👮 Seeding exam invigilators...")

            exams = (await session.execute(select(Exam))).scalars().all()
            staff_members = (
                (
                    await session.execute(
                        select(Staff).where(Staff.can_invigilate == True)
                    )
                )
                .scalars()
                .all()
            )
            rooms = (await session.execute(select(Room))).scalars().all()
            time_slots = (await session.execute(select(TimeSlot))).scalars().all()

            invigilators_created = 0

            for exam in exams:
                if invigilators_created >= SCALE_LIMITS["exam_invigilators"]:
                    break

                # Each exam needs 1-3 invigilators
                num_invigilators = randint(1, 3)
                selected_staff = sample(
                    staff_members, min(num_invigilators, len(staff_members))
                )

                for i, staff in enumerate(selected_staff):
                    if invigilators_created >= SCALE_LIMITS["exam_invigilators"]:
                        break

                    # Get exam rooms for this exam
                    exam_rooms = (
                        (
                            await session.execute(
                                select(ExamRoom).where(ExamRoom.exam_id == exam.id)
                            )
                        )
                        .scalars()
                        .all()
                    )

                    if not exam_rooms:
                        continue

                    existing = (
                        await session.execute(
                            select(ExamInvigilator).where(
                                ExamInvigilator.exam_id == exam.id,
                                ExamInvigilator.staff_id == staff.id,
                            )
                        )
                    ).scalar_one_or_none()

                    if not existing:
                        invigilator = ExamInvigilator(
                            exam_id=exam.id,
                            staff_id=staff.id,
                            room_id=choice(exam_rooms).room_id,
                            time_slot_id=exam.time_slot_id,
                            is_chief_invigilator=(i == 0),
                            assigned_at=fake.date_time_this_year(),
                        )
                        session.add(invigilator)
                        invigilators_created += 1

            self.seeded_data["exam_invigilators"] = invigilators_created
            logger.info(
                f"✓ Exam invigilators: {invigilators_created} assignments created"
            )

    async def _seed_staff_unavailability(self):
        """Seed staff unavailability"""
        async with db_manager.get_db_transaction() as session:
            logger.info("⛔ Seeding staff unavailability...")

            staff_members = (await session.execute(select(Staff))).scalars().all()
            sessions = (await session.execute(select(AcademicSession))).scalars().all()
            time_slots = (await session.execute(select(TimeSlot))).scalars().all()

            unavailability_created = 0

            for staff in staff_members:
                if unavailability_created >= SCALE_LIMITS["staff_unavailability"]:
                    break

                # Each staff member might have 0-3 unavailability entries
                num_entries = randint(0, 3)

                for _ in range(num_entries):
                    if unavailability_created >= SCALE_LIMITS["staff_unavailability"]:
                        break

                    session_obj = choice(sessions)
                    start_date = _to_date(session_obj.start_date)
                    end_date = _to_date(session_obj.end_date)

                    days_range = (end_date - start_date).days
                    unavailable_date = start_date + timedelta(
                        days=randint(0, days_range)
                    )

                    existing = (
                        await session.execute(
                            select(StaffUnavailability).where(
                                StaffUnavailability.staff_id == staff.id,
                                StaffUnavailability.session_id == session_obj.id,
                                StaffUnavailability.unavailable_date
                                == unavailable_date,
                            )
                        )
                    ).scalar_one_or_none()

                    if not existing:
                        unavailability = StaffUnavailability(
                            staff_id=staff.id,
                            session_id=session_obj.id,
                            time_slot_id=(
                                choice(time_slots).id if randint(1, 2) == 1 else None
                            ),
                            unavailable_date=unavailable_date,
                            reason=choice(
                                ["Sick leave", "Conference", "Personal", "Training"]
                            ),
                        )
                        session.add(unavailability)
                        unavailability_created += 1

            self.seeded_data["staff_unavailability"] = unavailability_created
            logger.info(
                f"✓ Staff unavailability: {unavailability_created} entries created"
            )

    async def _seed_timetable_jobs(self):
        """Seed timetable jobs with detailed logging and eager loading"""
        async with db_manager.get_db_transaction() as session:
            logger.info("📅 Seeding timetable jobs...")
            logger.info(f"Target limit: {SCALE_LIMITS['timetable_jobs']}")

            try:
                # Get all required data with eager loading
                sessions_result = await session.execute(
                    select(AcademicSession).options(selectinload(AcademicSession.exams))
                )
                sessions = sessions_result.scalars().all()
                logger.info(f"Found {len(sessions)} academic sessions")

                configs_result = await session.execute(select(SystemConfiguration))
                configs = configs_result.scalars().all()
                logger.info(f"Found {len(configs)} system configurations")

                users_result = await session.execute(select(User))
                users = users_result.scalars().all()
                logger.info(f"Found {len(users)} users")

                if not sessions or not configs or not users:
                    logger.error("Missing required data for timetable job seeding")
                    return

                jobs_created = 0
                batch_count = 0

                for session_obj in sessions:
                    if jobs_created >= SCALE_LIMITS["timetable_jobs"]:
                        logger.info(
                            f"Reached target limit of {SCALE_LIMITS['timetable_jobs']}"
                        )
                        break

                    # Each session can have 1-2 jobs
                    num_jobs = randint(1, 2)
                    logger.debug(f"Session {session_obj.id}: creating {num_jobs} jobs")

                    for _ in range(num_jobs):
                        if jobs_created >= SCALE_LIMITS["timetable_jobs"]:
                            break

                        # Initialize config and user to None
                        config = None
                        user = None
                        try:
                            # Get random config and user
                            config = choice(configs)
                            user = choice(users)

                            # Log the selected IDs for debugging
                            logger.debug(
                                f"Using config ID: {config.id}, user ID: {user.id}"
                            )

                            job = TimetableJob(
                                session_id=session_obj.id,
                                configuration_id=config.id,
                                initiated_by=user.id,
                                status=choice(
                                    ["queued", "running", "completed", "failed"]
                                ),
                                progress_percentage=randint(0, 100),
                                cp_sat_runtime_seconds=(
                                    randint(60, 3600) if randint(1, 2) == 1 else None
                                ),
                                ga_runtime_seconds=(
                                    randint(60, 3600) if randint(1, 2) == 1 else None
                                ),
                                total_runtime_seconds=randint(60, 7200),
                                hard_constraint_violations=randint(0, 10),
                                soft_constraint_score=round(randint(800, 1000) / 10, 1),
                                room_utilization_percentage=round(
                                    randint(60, 95) + randint(0, 99) / 100, 2
                                ),
                                solver_phase=choice(
                                    ["initial", "optimization", "final"]
                                ),
                                error_message=(
                                    fake.sentence() if randint(1, 10) == 1 else None
                                ),
                                result_data={
                                    "statistics": {
                                        "exams_scheduled": randint(50, 500),
                                        "rooms_used": randint(10, 50),
                                        "average_utilization": round(
                                            randint(60, 95) + randint(0, 99) / 100, 2
                                        ),
                                    }
                                },
                                started_at=fake.date_time_this_year(),
                                completed_at=(
                                    fake.date_time_this_year()
                                    if randint(1, 3) > 1
                                    else None
                                ),
                            )
                            session.add(job)
                            jobs_created += 1
                            logger.debug(
                                f"Created job {jobs_created} for session {session_obj.id}"
                            )

                        except Exception as e:
                            logger.error(f"Error creating timetable job: {e}")
                            logger.error(f"Session ID: {session_obj.id}")
                            logger.error(f"Config ID: {config.id if config else 'N/A'}")
                            logger.error(f"User ID: {user.id if user else 'N/A'}")
                            continue

                        # Commit in batches to avoid memory issues
                        if jobs_created % 50 == 0:
                            batch_count += 1
                            logger.info(
                                f"Flushing batch {batch_count}, created {jobs_created} jobs so far"
                            )
                            try:
                                await session.flush()
                                logger.debug(
                                    f"Successfully flushed batch {batch_count}"
                                )
                            except Exception as e:
                                logger.error(f"Error flushing batch {batch_count}: {e}")
                                # Rollback and retry might be needed here
                                raise

                # Final flush
                await session.flush()
                self.seeded_data["timetable_jobs"] = jobs_created
                logger.info(f"✓ Timetable jobs: {jobs_created} jobs created")

            except Exception as e:
                logger.error(f"Error in _seed_timetable_jobs: {e}")
                logger.error(f"Error type: {type(e).__name__}")
                import traceback

                logger.error(f"Traceback: {traceback.format_exc()}")
                raise

    async def _seed_timetable_versions(self):
        """Seed timetable versions with unique version numbers"""
        async with db_manager.get_db_transaction() as session:
            logger.info("📋 Seeding timetable versions...")

            jobs = (await session.execute(select(TimetableJob))).scalars().all()
            users = (await session.execute(select(User))).scalars().all()

            # Get existing version numbers to avoid conflicts
            existing_versions = set(
                (await session.execute(select(TimetableVersion.version_number)))
                .scalars()
                .all()
            )

            versions_created = 0
            used_version_numbers = set()

            for job in jobs:
                if versions_created >= SCALE_LIMITS["timetable_versions"]:
                    break

                # Generate unique version number
                version_number = randint(1, 1000)
                while (
                    version_number in existing_versions
                    or version_number in used_version_numbers
                ):
                    version_number = randint(1, 1000)

                used_version_numbers.add(version_number)

                existing = (
                    await session.execute(
                        select(TimetableVersion).where(
                            TimetableVersion.job_id == job.id,
                            TimetableVersion.version_number == version_number,
                        )
                    )
                ).scalar_one_or_none()

                if not existing:
                    version = TimetableVersion(
                        job_id=job.id,
                        version_number=version_number,
                        is_active=choice([True, False]),
                        approval_level=(
                            choice(["department", "faculty", "university"])
                            if randint(1, 3) == 1
                            else None
                        ),
                        approved_by=choice(users).id if randint(1, 2) == 1 else None,
                        approved_at=(
                            fake.date_time_this_year() if randint(1, 2) == 1 else None
                        ),
                    )
                    session.add(version)
                    versions_created += 1

            self.seeded_data["timetable_versions"] = versions_created
            logger.info(f"✓ Timetable versions: {versions_created} versions created")

    async def _seed_timetable_assignments(self):
        """Seed timetable assignments"""
        async with db_manager.get_db_transaction() as session:
            logger.info("📊 Seeding timetable assignments...")

            exams = (await session.execute(select(Exam))).scalars().all()
            rooms = (await session.execute(select(Room))).scalars().all()
            time_slots = (await session.execute(select(TimeSlot))).scalars().all()

            assignments_created = 0

            for exam in exams:
                if assignments_created >= SCALE_LIMITS["timetable_assignments"]:
                    break

                if not exam.exam_date or not exam.time_slot_id:
                    continue

                # Get exam rooms for this exam
                exam_rooms = (
                    (
                        await session.execute(
                            select(ExamRoom).where(ExamRoom.exam_id == exam.id)
                        )
                    )
                    .scalars()
                    .all()
                )

                for exam_room in exam_rooms:
                    if assignments_created >= SCALE_LIMITS["timetable_assignments"]:
                        break

                    existing = (
                        await session.execute(
                            select(TimetableAssignment).where(
                                TimetableAssignment.exam_id == exam.id,
                                TimetableAssignment.room_id == exam_room.room_id,
                            )
                        )
                    ).scalar_one_or_none()

                    if not existing:
                        assignment = TimetableAssignment(
                            exam_id=exam.id,
                            room_id=exam_room.room_id,
                            day=exam.exam_date,
                            time_slot_id=exam.time_slot_id,
                            student_count=exam_room.allocated_capacity,
                            is_confirmed=choice([True, False]),
                        )
                        session.add(assignment)
                        assignments_created += 1

            self.seeded_data["timetable_assignments"] = assignments_created
            logger.info(
                f"✓ Timetable assignments: {assignments_created} assignments created"
            )

    async def _seed_timetable_edits(self):
        """Seed timetable edits"""
        async with db_manager.get_db_transaction() as session:
            logger.info("✏️ Seeding timetable edits...")

            versions = (await session.execute(select(TimetableVersion))).scalars().all()
            exams = (await session.execute(select(Exam))).scalars().all()
            users = (await session.execute(select(User))).scalars().all()

            edits_created = 0

            for version in versions:
                if edits_created >= SCALE_LIMITS["timetable_edits"]:
                    break

                # Each version can have 0-5 edits
                num_edits = randint(0, 5)

                for _ in range(num_edits):
                    if edits_created >= SCALE_LIMITS["timetable_edits"]:
                        break

                    exam = choice(exams)

                    existing = (
                        await session.execute(
                            select(TimetableEdit).where(
                                TimetableEdit.version_id == version.id,
                                TimetableEdit.exam_id == exam.id,
                            )
                        )
                    ).scalar_one_or_none()

                    if not existing:
                        edit_types = [
                            "reschedule",
                            "room_change",
                            "duration_change",
                            "cancel",
                            "reinstate",
                        ]
                        edit_type = choice(edit_types)

                        old_values = None
                        new_values = None

                        if edit_type == "reschedule":
                            if exam.exam_date:
                                # Convert to Python date object first
                                exam_date = exam.exam_date
                                old_values = {"exam_date": str(exam_date)}
                                # Convert to Python date for arithmetic operations
                                if isinstance(exam_date, date):
                                    new_date = exam_date + timedelta(days=randint(1, 7))
                                else:
                                    # Fallback if not a date object
                                    new_date = date.today() + timedelta(
                                        days=randint(1, 7)
                                    )
                                new_values = {"exam_date": str(new_date)}
                            else:
                                # fake.date_this_year() returns a Python date
                                new_dt = fake.date_this_year()
                                old_values = None
                                new_values = {"exam_date": str(new_dt)}

                        elif edit_type == "room_change":
                            # This would need room data, simplified for example
                            old_values = {"room_id": str(uuid4())}
                            new_values = {"room_id": str(uuid4())}
                        elif edit_type == "duration_change":
                            old_values = {"duration_minutes": exam.duration_minutes}
                            new_values = {
                                "duration_minutes": exam.duration_minutes
                                + randint(-30, 30)
                            }
                        elif edit_type == "cancel":
                            old_values = {"status": exam.status}
                            new_values = {"status": "cancelled"}
                        elif edit_type == "reinstate":
                            old_values = {"status": exam.status}
                            new_values = {"status": "scheduled"}

                        edit = TimetableEdit(
                            version_id=version.id,
                            exam_id=exam.id,
                            edited_by=choice(users).id,
                            edit_type=edit_type,
                            old_values=old_values,
                            new_values=new_values,
                            reason=fake.sentence() if randint(1, 3) == 1 else None,
                            validation_status=choice(
                                ["pending", "approved", "rejected"]
                            ),
                        )
                        session.add(edit)
                        edits_created += 1

            self.seeded_data["timetable_edits"] = edits_created
            logger.info(f"✓ Timetable edits: {edits_created} edits created")

    async def _seed_file_uploads(self):
        """Seed file upload sessions and uploaded files"""
        async with db_manager.get_db_transaction() as session:
            logger.info("📤 Seeding file uploads...")

            users = (await session.execute(select(User))).scalars().all()
            sessions = (await session.execute(select(AcademicSession))).scalars().all()

            upload_sessions_created = 0
            uploaded_files_created = 0

            for _ in range(SCALE_LIMITS["file_upload_sessions"]):
                if upload_sessions_created >= SCALE_LIMITS["file_upload_sessions"]:
                    break

                upload_types = ["students", "courses", "exams", "timetable"]
                upload_type = choice(upload_types)

                session_obj = choice(sessions) if randint(1, 2) == 1 else None

                upload_session = FileUploadSession(
                    upload_type=upload_type,
                    uploaded_by=choice(users).id,
                    session_id=session_obj.id if session_obj else None,
                    status=choice(["processing", "completed", "failed"]),
                    total_records=randint(10, 1000),
                    processed_records=randint(0, 1000),
                    validation_errors=(
                        {
                            "errors": [
                                {
                                    "row": randint(1, 100),
                                    "field": fake.word(),
                                    "message": fake.sentence(),
                                }
                                for _ in range(randint(0, 5))
                            ]
                        }
                        if randint(1, 5) == 1
                        else None
                    ),
                    completed_at=(
                        fake.date_time_this_year() if randint(1, 3) > 1 else None
                    ),
                )
                session.add(upload_session)
                await session.flush()
                upload_sessions_created += 1

                # Create uploaded files for this session
                num_files = randint(1, 3)
                for _ in range(num_files):
                    if uploaded_files_created >= SCALE_LIMITS["uploaded_files"]:
                        break

                    file_types = ["csv", "xlsx", "pdf", "txt"]
                    file_type = choice(file_types)

                    uploaded_file = UploadedFile(
                        upload_session_id=upload_session.id,
                        file_name=f"{upload_type}_{fake.word()}.{file_type}",
                        file_path=f"/uploads/{upload_session.id}/{fake.uuid4()}.{file_type}",
                        file_size=randint(1024, 10485760),  # 1KB to 10MB
                        file_type=file_type,
                        mime_type=f"application/{file_type}",
                        checksum=fake.sha256(),
                        row_count=randint(10, 1000),
                        validation_status=choice(["pending", "valid", "invalid"]),
                        validation_errors=(
                            {
                                "errors": [
                                    {
                                        "row": randint(1, 100),
                                        "field": fake.word(),
                                        "message": fake.sentence(),
                                    }
                                    for _ in range(randint(0, 3))
                                ]
                            }
                            if randint(1, 4) == 1
                            else None
                        ),
                        uploaded_at=fake.date_time_this_year(),
                    )
                    session.add(uploaded_file)
                    uploaded_files_created += 1

            self.seeded_data["file_upload_sessions"] = upload_sessions_created
            self.seeded_data["uploaded_files"] = uploaded_files_created
            logger.info(
                f"✓ File uploads: {upload_sessions_created} sessions, {uploaded_files_created} files"
            )

    async def _seed_system_events(self):
        """Seed system events"""
        async with db_manager.get_db_transaction() as session:
            logger.info("🔔 Seeding system events...")

            users = (await session.execute(select(User))).scalars().all()

            events_created = 0

            for _ in range(SCALE_LIMITS["system_events"]):
                if events_created >= SCALE_LIMITS["system_events"]:
                    break

                event_types = ["info", "warning", "error", "success"]
                priorities = ["low", "medium", "high", "critical"]
                entity_types = ["user", "exam", "course", "timetable", "system"]

                event = SystemEvent(
                    title=fake.sentence(),
                    message=fake.paragraph(),
                    event_type=choice(event_types),
                    priority=choice(priorities),
                    entity_type=choice(entity_types),
                    entity_id=choice([uuid4(), None]),
                    event_metadata={"source": fake.word(), "details": fake.paragraph()},
                    affected_users=(
                        [choice(users).id for _ in range(randint(1, 5))]
                        if users and randint(1, 3) == 1
                        else None
                    ),
                    is_resolved=choice([True, False]),
                    resolved_by=choice(users).id if randint(1, 3) == 1 else None,
                    resolved_at=(
                        fake.date_time_this_year() if randint(1, 3) == 1 else None
                    ),
                )
                session.add(event)
                events_created += 1

            self.seeded_data["system_events"] = events_created
            logger.info(f"✓ System events: {events_created} events created")

    async def _seed_user_notifications(self):
        """Seed user notifications"""
        async with db_manager.get_db_transaction() as session:
            logger.info("📩 Seeding user notifications...")

            users = (await session.execute(select(User))).scalars().all()
            events = (await session.execute(select(SystemEvent))).scalars().all()

            notifications_created = 0

            for user in users:
                if notifications_created >= SCALE_LIMITS["user_notifications"]:
                    break

                # Each user can have 0-5 notifications
                num_notifications = randint(0, 5)

                for _ in range(num_notifications):
                    if notifications_created >= SCALE_LIMITS["user_notifications"]:
                        break

                    event = choice(events)

                    existing = (
                        await session.execute(
                            select(UserNotification).where(
                                UserNotification.user_id == user.id,
                                UserNotification.event_id == event.id,
                            )
                        )
                    ).scalar_one_or_none()

                    if not existing:
                        notification = UserNotification(
                            user_id=user.id,
                            event_id=event.id,
                            is_read=choice([True, False]),
                            read_at=(
                                fake.date_time_this_year()
                                if randint(1, 3) == 1
                                else None
                            ),
                        )
                        session.add(notification)
                        notifications_created += 1

            self.seeded_data["user_notifications"] = notifications_created
            logger.info(
                f"✓ User notifications: {notifications_created} notifications created"
            )

    async def _seed_audit_logs(self):
        """Seed audit logs for system activities"""
        async with db_manager.get_db_transaction() as session:
            logger.info("📝 Seeding audit logs...")

            # Get entities to log actions for
            users = (await session.execute(select(User))).scalars().all()
            exams = (await session.execute(select(Exam))).scalars().all()
            courses = (await session.execute(select(Course))).scalars().all()

            logs_created = 0
            entity_types = [
                "user",
                "exam",
                "course",
                "student",
                "room",
                "timetable",
                "system",
            ]
            actions = [
                "create",
                "update",
                "delete",
                "view",
                "export",
                "login",
                "logout",
            ]

            for _ in range(SCALE_LIMITS["audit_logs"]):
                user = choice(users) if users else None
                entity_type = choice(entity_types)

                # Create realistic log entries
                log = AuditLog(
                    user_id=user.id if user else None,
                    action=choice(actions),
                    entity_type=entity_type,
                    entity_id=None,  # Can be set based on entity_type if needed
                    old_values=(
                        fake.pydict(3, True, value_types=[str, int, bool])
                        if randint(1, 3) == 1
                        else None
                    ),
                    new_values=(
                        fake.pydict(3, True, value_types=[str, int, bool])
                        if randint(1, 3) == 1
                        else None
                    ),
                    ip_address=fake.ipv4() if randint(1, 4) > 1 else None,
                    user_agent=fake.user_agent() if randint(1, 4) > 1 else None,
                    session_id=fake.uuid4() if randint(1, 5) == 1 else None,
                    notes=fake.sentence() if randint(1, 4) == 1 else None,
                )

                # Set entity_id based on entity_type
                if entity_type == "exam" and exams:
                    log.entity_id = choice(exams).id
                elif entity_type == "course" and courses:
                    log.entity_id = choice(courses).id
                # For other entity types, we could add more logic

                session.add(log)
                logs_created += 1

                # Commit in batches to avoid memory issues
                if logs_created % 100 == 0:
                    await session.flush()

            self.seeded_data["audit_logs"] = logs_created
            logger.info(f"✓ Audit Logs: {logs_created} logs created")

    async def print_summary(self):
        """Print summary of seeded data"""
        logger.info("\n" + "=" * 50)
        logger.info("📊 FAKE DATA SEEDING SUMMARY")
        logger.info("=" * 50)
        for entity, count in self.seeded_data.items():
            limit = SCALE_LIMITS.get(entity, "N/A")
            logger.info(f"{entity.replace('_', ' ').title():30}: {count:6,} / {limit}")
        logger.info("=" * 50)


async def main():
    """Main entry point for the fake seeder"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed the database with comprehensive fake data"
    )
    parser.add_argument("--database-url", help="Database URL override")
    parser.add_argument(
        "--drop-existing", action="store_true", help="Drop existing data before seeding"
    )
    args = parser.parse_args()

    seeder = ComprehensiveFakeSeeder(args.database_url)
    await seeder.run(drop_existing=args.drop_existing)


if __name__ == "__main__":
    asyncio.run(main())
