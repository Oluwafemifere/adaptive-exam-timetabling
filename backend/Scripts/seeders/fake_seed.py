#!/usr/bin/env python3

# backend/Scripts/seeders/fake_seed.py

from uuid import uuid4
import uuid
import os
import sys
import asyncio
import logging
import math
from pathlib import Path
from datetime import time, timedelta, datetime as dt_datetime, date
from random import choice, randint, sample
from typing import Any, Dict, Set, List, cast
from faker import Faker
from typing import TYPE_CHECKING
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, text, cast, true, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, date, timedelta

if TYPE_CHECKING:
    from datetime import date

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import db_manager
from app.models import (
    # Infrastructure
    Building,
    RoomType,
    Room,
    ExamAllowedRoom,
    # Academic
    AcademicSession,
    Faculty,
    Department,
    Programme,
    Course,
    Student,
    StudentEnrollment,
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
    # Versioning
    TimetableVersion,
    VersionMetadata,
    VersionDependency,
    SessionTemplate,
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
    "academic_sessions": int(os.getenv("SEED_SESSIONS", "3")),
    "courses": int(os.getenv("SEED_COURSES", "800")),
    "students": int(os.getenv("SEED_STUDENTS", "8000")),
    "student_enrollments": int(os.getenv("SEED_ENROLLMENTS", "8000")),
    "course_registrations": int(os.getenv("SEED_REGISTRATIONS", "50000")),
    "exams": int(os.getenv("SEED_EXAMS", "800")),
    "staff": int(os.getenv("SEED_STAFF", "400")),
    "users": int(os.getenv("SEED_USERS", "500")),
    "user_roles": int(os.getenv("SEED_ROLES", "10")),
    "user_role_assignments": int(os.getenv("SEED_ROLE_ASSIGNMENTS", "600")),
    "audit_logs": int(os.getenv("SEED_AUDIT_LOGS", "500")),
    "timetable_edits": int(os.getenv("SEED_TIMETABLE_EDITS", "200")),
    "timetable_versions": int(os.getenv("SEED_VERSIONS", "15")),
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
    "timetable_jobs": int(os.getenv("SEED_TIMETABLE_JOBS", "5")),
    "session_templates": int(os.getenv("SEED_SESSION_TEMPLATES", "5")),
    "version_metadata": int(os.getenv("SEED_VERSION_METADATA", "15")),
    "version_dependencies": int(os.getenv("SEED_VERSION_DEPENDENCIES", "10")),
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

    def set_magnitude_level(self, level: int):
        """
        Set the data magnitude level for seeding (1-5).
        This will update SCALE_LIMITS for the seeder instance.
        """
        MAGNITUDE_LEVELS = {
            1: {  # Basic - 100 students
                "faculties": 3,
                "departments": 8,
                "programmes": 15,
                "buildings": 5,
                "room_types": 5,
                "rooms": 50,
                "academic_sessions": 2,
                "courses": 50,
                "students": 100,
                "student_enrollments": 100,
                "course_registrations": 500,
                "exams": 50,
                "staff": 25,
                "users": 30,
                "user_roles": 8,
                "user_role_assignments": 35,
                "audit_logs": 50,
                "timetable_edits": 20,
                "timetable_versions": 3,
                "system_configurations": 2,
                "constraint_categories": 5,
                "constraint_rules": 15,
                "configuration_constraints": 20,
                "system_events": 25,
                "user_notifications": 50,
                "file_upload_sessions": 5,
                "uploaded_files": 10,
                "exam_departments": 50,
                "exam_invigilators": 75,
                "staff_unavailability": 25,
                "timetable_assignments": 50,
                "exam_allowed_rooms": 75,
                "timetable_jobs": 3,
                "session_templates": 2,
                "version_metadata": 3,
                "version_dependencies": 2,
            },
            2: {  # Small - 500 students
                "faculties": 4,
                "departments": 15,
                "programmes": 30,
                "buildings": 7,
                "room_types": 6,
                "rooms": 100,
                "academic_sessions": 3,
                "courses": 200,
                "students": 500,
                "student_enrollments": 500,
                "course_registrations": 2500,
                "exams": 200,
                "staff": 75,
                "users": 100,
                "user_roles": 10,
                "user_role_assignments": 110,
                "audit_logs": 150,
                "timetable_edits": 50,
                "timetable_versions": 4,
                "system_configurations": 3,
                "constraint_categories": 5,
                "constraint_rules": 20,
                "configuration_constraints": 25,
                "system_events": 50,
                "user_notifications": 100,
                "file_upload_sessions": 8,
                "uploaded_files": 15,
                "exam_departments": 200,
                "exam_invigilators": 300,
                "staff_unavailability": 75,
                "timetable_assignments": 200,
                "exam_allowed_rooms": 300,
                "timetable_jobs": 4,
                "session_templates": 3,
                "version_metadata": 4,
                "version_dependencies": 3,
            },
            3: {  # Medium - 2000 students
                "faculties": 6,
                "departments": 25,
                "programmes": 50,
                "buildings": 10,
                "room_types": 7,
                "rooms": 200,
                "academic_sessions": 3,
                "courses": 500,
                "students": 2000,
                "student_enrollments": 2000,
                "course_registrations": 10000,
                "exams": 500,
                "staff": 200,
                "users": 250,
                "user_roles": 10,
                "user_role_assignments": 275,
                "audit_logs": 300,
                "timetable_edits": 100,
                "timetable_versions": 5,
                "system_configurations": 3,
                "constraint_categories": 5,
                "constraint_rules": 20,
                "configuration_constraints": 30,
                "system_events": 75,
                "user_notifications": 200,
                "file_upload_sessions": 10,
                "uploaded_files": 20,
                "exam_departments": 500,
                "exam_invigilators": 750,
                "staff_unavailability": 150,
                "timetable_assignments": 500,
                "exam_allowed_rooms": 750,
                "timetable_jobs": 5,
                "session_templates": 4,
                "version_metadata": 5,
                "version_dependencies": 4,
            },
            4: {  # Large - 5000 students
                "faculties": 8,
                "departments": 35,
                "programmes": 80,
                "buildings": 12,
                "room_types": 8,
                "rooms": 300,
                "academic_sessions": 3,
                "courses": 800,
                "students": 5000,
                "student_enrollments": 5000,
                "course_registrations": 25000,
                "exams": 800,
                "staff": 400,
                "users": 500,
                "user_roles": 10,
                "user_role_assignments": 550,
                "audit_logs": 500,
                "timetable_edits": 200,
                "timetable_versions": 5,
                "system_configurations": 3,
                "constraint_categories": 5,
                "constraint_rules": 20,
                "configuration_constraints": 30,
                "system_events": 100,
                "user_notifications": 300,
                "file_upload_sessions": 12,
                "uploaded_files": 25,
                "exam_departments": 800,
                "exam_invigilators": 1200,
                "staff_unavailability": 200,
                "timetable_assignments": 800,
                "exam_allowed_rooms": 1200,
                "timetable_jobs": 5,
                "session_templates": 5,
                "version_metadata": 8,
                "version_dependencies": 6,
            },
            5: {  # Enterprise - 10,000 students
                "faculties": 10,
                "departments": 50,
                "programmes": 120,
                "buildings": 15,
                "room_types": 10,
                "rooms": 500,
                "academic_sessions": 4,
                "courses": 1200,
                "students": 10000,
                "student_enrollments": 10000,
                "course_registrations": 50000,
                "exams": 1200,
                "staff": 600,
                "users": 800,
                "user_roles": 12,
                "user_role_assignments": 900,
                "audit_logs": 1000,
                "timetable_edits": 400,
                "timetable_versions": 8,
                "system_configurations": 5,
                "constraint_categories": 6,
                "constraint_rules": 25,
                "configuration_constraints": 40,
                "system_events": 150,
                "user_notifications": 500,
                "file_upload_sessions": 15,
                "uploaded_files": 30,
                "exam_departments": 1200,
                "exam_invigilators": 1800,
                "staff_unavailability": 300,
                "timetable_assignments": 1200,
                "exam_allowed_rooms": 1800,
                "timetable_jobs": 8,
                "session_templates": 6,
                "version_metadata": 10,
                "version_dependencies": 8,
            },
        }

        if level not in MAGNITUDE_LEVELS:
            raise ValueError(
                f"Level must be one of {list(MAGNITUDE_LEVELS.keys())}, got {level}"
            )

        # Update the global SCALE_LIMITS
        global SCALE_LIMITS
        SCALE_LIMITS.update(MAGNITUDE_LEVELS[level])
        logger.info(
            f"Seeding magnitude set to level {level} (students: {SCALE_LIMITS['students']}, courses: {SCALE_LIMITS['courses']})"
        )

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
            await self._seed_session_templates()
            await self._seed_academic_structure()
            await self._seed_courses()
            await self._seed_students_and_enrollments()
            await self._seed_staff()
            await self._seed_exams()
            await self._seed_exam_departments()
            await self._seed_exam_allowed_rooms()
            await self._seed_timetable_jobs()
            await self._seed_timetable_versions()
            await self._seed_version_metadata()
            await self._seed_version_dependencies()
            await self._seed_timetable_assignments()
            await self._seed_exam_invigilators()
            await self._seed_staff_unavailability()
            await self._seed_timetable_edits()
            await self._seed_file_uploads()
            await self._seed_system_events()
            await self._seed_user_notifications()
            await self._seed_audit_logs()

            logger.info("🎉 Comprehensive fake data seeding completed!")
            await self.print_summary()

        except IntegrityError as e:
            logger.error(f"Integrity error during seeding: {e}")
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
                "audit_logs",
                "user_notifications",
                "system_events",
                "uploaded_files",
                "file_upload_sessions",
                "timetable_edits",
                "timetable_assignments",
                "staff_unavailability",
                "exam_invigilators",
                "exam_allowed_rooms",
                "exam_departments",
                "version_dependencies",
                "version_metadata",
                "timetable_versions",
                "timetable_jobs",
                "configuration_constraints",
                "system_configurations",
                "constraint_rules",
                "constraint_categories",
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
                    await session.execute(
                        text(f"TRUNCATE TABLE exam_system.{table} CASCADE")
                    )
                    logger.info(f"✓ Cleared {table}")
                except Exception as e:
                    logger.warning(f"Could not clear {table}: {e}")

        logger.info("🧹 Database cleared successfully")

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

            # Create role assignments for other users
            role_assignments_created = 0
            users = (await session.execute(select(User))).scalars().all()
            faculties = (await session.execute(select(Faculty))).scalars().all()
            departments = (await session.execute(select(Department))).scalars().all()

            for user in users:
                if user.email == "admin@baze.edu.ng":
                    continue
                if role_assignments_created >= SCALE_LIMITS["user_role_assignments"]:
                    break

                # Assign 1-2 roles per user
                num_roles = randint(1, 2)
                user_roles = sample(list(roles.values()), min(num_roles, len(roles)))

                for role in user_roles:
                    assignment = UserRoleAssignment(
                        user_id=user.id,
                        role_id=role.id,
                        faculty_id=(
                            choice(faculties).id
                            if faculties and randint(1, 3) == 1
                            else None
                        ),
                        department_id=(
                            choice(departments).id
                            if departments and randint(1, 3) == 1
                            else None
                        ),
                    )
                    session.add(assignment)
                    role_assignments_created += 1

            self.seeded_data["users"] = user_count + 1  # +1 for admin
            self.seeded_data["user_roles"] = len(roles)
            self.seeded_data["user_role_assignments"] = role_assignments_created
            logger.info(
                f"✓ Users and roles: {user_count + 1} users, {len(roles)} roles, {role_assignments_created} assignments"
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

    async def _seed_session_templates(self):
        """Seed session templates"""
        async with db_manager.get_db_transaction() as session:
            logger.info("📄 Seeding session templates...")
            templates_created = 0
            template_names = [
                "Standard Semester Template",
                "Fast-Track Semester Template",
                "Postgraduate Session Template",
                "Summer School Template",
                "Online Program Template",
            ]

            # Get existing sessions for source_session_id
            existing_sessions = (
                (await session.execute(select(AcademicSession))).scalars().all()
            )

            for name in template_names:
                if templates_created >= SCALE_LIMITS["session_templates"]:
                    break
                existing = (
                    await session.execute(
                        select(SessionTemplate).where(SessionTemplate.name == name)
                    )
                ).scalar_one_or_none()
                if not existing:
                    template = SessionTemplate(
                        name=name,
                        description=f"Template for {name}",
                        source_session_id=(
                            choice(existing_sessions).id
                            if existing_sessions and randint(1, 3) > 1
                            else None
                        ),
                        template_data={
                            "exam_period_days": randint(15, 25),
                            "default_duration_minutes": 180,
                            "allow_back_to_back": choice([True, False]),
                        },
                        is_active=True,
                    )
                    session.add(template)
                    templates_created += 1
            self.seeded_data["session_templates"] = templates_created
            logger.info(f"✓ Session templates: {templates_created} created")

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
                        departments[f"{fac_code}_{dept_code}"] = d
                        dept_count += 1
                    else:
                        departments[f"{fac_code}_{dept_code}"] = existing

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
            templates = (await session.execute(select(SessionTemplate))).scalars().all()
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
                        template_id=(
                            choice(templates).id
                            if templates and randint(1, 3) > 1
                            else None
                        ),
                        archived_at=dt_datetime(year + 1, 9, 1) if i > 1 else None,
                        session_config=(
                            {"allow_weekend_exams": choice([True, False])}
                            if randint(1, 4) == 1
                            else None
                        ),
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
                            title=title[:255],
                            credit_units=choice([2, 3, 4, 5, 6]),
                            course_level=level,
                            semester=choice([1, 2, 3]),
                            is_practical=choice([True, False]),
                            morning_only=(
                                choice([True, False]) if level >= 300 else False
                            ),
                            exam_duration_minutes=choice(
                                [
                                    60,
                                    120,
                                    180,
                                ]
                            ),
                            department_id=dept.id,
                            is_active=True,
                        )
                        session.add(c)
                        courses_created += 1

            self.seeded_data["courses"] = courses_created
            logger.info(f"✓ Courses: {courses_created} courses created")

    async def _seed_students_and_enrollments(self):
        """Seed students, their enrollments, and course registrations"""
        async with db_manager.get_db_transaction() as session:
            logger.info("👨‍🎓 Seeding students, enrollments, and registrations...")

            programmes = (await session.execute(select(Programme))).scalars().all()
            courses = (await session.execute(select(Course))).scalars().all()
            sessions = (await session.execute(select(AcademicSession))).scalars().all()

            if not programmes or not sessions:
                logger.error("No programmes or academic sessions found")
                return

            current_year = date.today().year
            students_created = 0
            enrollments_created = 0
            registrations_created = 0

            # Safe unique list of department codes used for matric generation
            dept_codes = [
                row[0]
                for row in (
                    await session.execute(
                        text(
                            "SELECT DISTINCT d.code FROM exam_system.departments d JOIN exam_system.programmes p ON p.department_id=d.id"
                        )
                    )
                ).all()
            ]
            if not dept_codes:
                logger.error("No department codes found")
                return

            for _ in range(SCALE_LIMITS["students"]):
                if students_created >= SCALE_LIMITS["students"]:
                    break

                # Generate unique matric number
                attempts = 0
                matric = None
                while attempts < 10:
                    y = randint(current_year - 6, current_year)
                    dept_code = choice(dept_codes)
                    sequence = randint(1000, 9999)
                    candidate = f"BU/{y%100:02d}/{dept_code}/{sequence:04d}"
                    if candidate not in self.generated_matrics:
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
                            self.generated_matrics.add(candidate)
                            break
                    attempts += 1

                if not matric:
                    continue

                programme = choice(programmes)
                entry_year = randint(
                    current_year - programme.duration_years, current_year
                )

                student = Student(
                    matric_number=matric,
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                    entry_year=entry_year,
                    special_needs=(
                        [choice(["extra_time", "wheelchair_access"])]
                        if randint(1, 20) == 1
                        else []
                    ),
                    programme_id=programme.id,
                )
                session.add(student)
                await session.flush()
                students_created += 1

                # Create enrollments for each student in each session
                for session_obj in sessions:
                    if enrollments_created >= SCALE_LIMITS["student_enrollments"]:
                        break

                    # Calculate student level based on entry year and session year
                    session_year = int(session_obj.name.split("/")[0])
                    years_since_entry = session_year - entry_year
                    level = min(
                        max(100, years_since_entry * 100),
                        programme.duration_years * 100,
                    )

                    enrollment = StudentEnrollment(
                        student_id=student.id,
                        session_id=session_obj.id,
                        level=level,
                        student_type=choice(["regular", "transfer", "direct_entry"]),
                        is_active=True,
                    )
                    session.add(enrollment)
                    enrollments_created += 1

                    # Create course registrations for this enrollment
                    if (
                        session_obj.is_active
                    ):  # Only register for active session courses
                        # Get courses that match student's level and department
                        eligible_courses = [
                            c
                            for c in courses
                            if c.department_id == programme.department_id
                            and c.course_level <= level
                        ]

                        if not eligible_courses:
                            continue

                        num_courses = min(randint(5, 8), len(eligible_courses))
                        selected_courses = sample(eligible_courses, num_courses)

                        for course in selected_courses:
                            if (
                                registrations_created
                                >= SCALE_LIMITS["course_registrations"]
                            ):
                                break

                            registration = CourseRegistration(
                                student_id=student.id,
                                course_id=course.id,
                                session_id=session_obj.id,
                                registration_type=choice(["regular", "retake"]),
                                registered_at=fake.date_time_this_year(),
                            )
                            session.add(registration)
                            registrations_created += 1

                if students_created % 100 == 0:
                    logger.info(
                        f"Progress: {students_created} students, {enrollments_created} enrollments, {registrations_created} registrations"
                    )

            self.seeded_data["students"] = students_created
            self.seeded_data["student_enrollments"] = enrollments_created
            self.seeded_data["course_registrations"] = registrations_created
            logger.info(
                f"✓ Students: {students_created} students, {enrollments_created} enrollments, {registrations_created} registrations"
            )

    async def _seed_staff(self):
        """Seed staff members with updated fields"""
        async with db_manager.get_db_transaction() as session:
            logger.info("👨‍🏫 Seeding staff...")

            departments = (await session.execute(select(Department))).scalars().all()
            users = (await session.execute(select(User))).scalars().all()

            # Get user IDs not already assigned to staff
            assigned_user_ids = set(
                (
                    await session.execute(
                        select(Staff.user_id).where(Staff.user_id.isnot(None))
                    )
                )
                .scalars()
                .all()
            )
            available_users = [
                u
                for u in users
                if u.id not in assigned_user_ids and u.email != "admin@baze.edu.ng"
            ]

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
                    # Assign available user or create without user link
                    assigned_user = choice(available_users) if available_users else None
                    if assigned_user:
                        available_users.remove(assigned_user)

                    staff = Staff(
                        staff_number=staff_number,
                        first_name=fake.first_name(),
                        last_name=fake.last_name(),
                        department_id=choice(departments).id if departments else None,
                        position=fake.job(),
                        staff_type=choice(staff_types),
                        can_invigilate=choice([True, False]),
                        max_daily_sessions=randint(1, 3),
                        max_consecutive_sessions=randint(1, 2),
                        is_active=True,
                        user_id=assigned_user.id if assigned_user else None,
                        max_concurrent_exams=randint(1, 2),
                        max_students_per_invigilator=choice([25, 50, 75]),
                        generic_availability_preferences=(
                            {
                                "preferred_days": sample(
                                    [
                                        "Monday",
                                        "Tuesday",
                                        "Wednesday",
                                        "Thursday",
                                        "Friday",
                                    ],
                                    randint(2, 4),
                                ),
                                "avoid_slots": [
                                    choice(["Morning", "Afternoon", "Evening"])
                                ],
                            }
                            if randint(1, 4) == 1
                            else None
                        ),
                    )
                    session.add(staff)
                    staff_created += 1

            self.seeded_data["staff"] = staff_created
            logger.info(f"✓ Staff: {staff_created} staff members created")

    async def _seed_exams(self):
        """Seed exams for courses with registered students"""
        async with db_manager.get_db_transaction() as session:
            logger.info("📝 Seeding exams...")

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
            if not active_session:
                logger.error("No active academic session found")
                return

            # Get courses with registrations in active session
            stmt = (
                select(Course)
                .join(CourseRegistration)
                .where(CourseRegistration.session_id == active_session.id)
                .distinct()
            )
            courses_with_registrations = (await session.execute(stmt)).scalars().all()
            staff_members = (await session.execute(select(Staff))).scalars().all()

            if not courses_with_registrations:
                logger.error("No courses with student registrations found")
                return

            exams_created = 0
            for course in courses_with_registrations:
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
                    # Get registration count for expected students
                    reg_count_result = await session.execute(
                        select(func.count(CourseRegistration.id)).where(
                            CourseRegistration.course_id == course.id,
                            CourseRegistration.session_id == active_session.id,
                        )
                    )
                    expected_students = reg_count_result.scalar_one()

                    if expected_students > 0:
                        exam = Exam(
                            course_id=course.id,
                            session_id=active_session.id,
                            duration_minutes=course.exam_duration_minutes
                            or choice([120, 180]),
                            expected_students=expected_students,
                            requires_special_arrangements=choice([True, False]),
                            status="pending",
                            notes=(
                                f"Exam for {course.title}"
                                if randint(1, 3) == 1
                                else None
                            ),
                            is_practical=course.is_practical,
                            requires_projector=choice([True, False]),
                            is_common=choice([True, False]),
                            morning_only=course.morning_only or False,
                            instructor_id=(
                                choice(staff_members).id
                                if staff_members and randint(1, 2) == 1
                                else None
                            ),
                        )
                        session.add(exam)
                        exams_created += 1

            self.seeded_data["exams"] = exams_created
            logger.info(f"✓ Exams: {exams_created} exams created")

    async def _seed_exam_departments(self):
        """Seed exam departments"""
        async with db_manager.get_db_transaction() as session:
            logger.info("🏫 Seeding exam departments...")

            exams = (await session.execute(select(Exam))).scalars().all()
            departments = (await session.execute(select(Department))).scalars().all()

            if not exams or not departments:
                logger.error(
                    "No exams or departments found for seeding exam departments"
                )
                return

            exam_deps_created = 0
            for exam in exams:
                if exam_deps_created >= SCALE_LIMITS["exam_departments"]:
                    break

                # Each exam can belong to 1-3 departments
                num_depts = randint(1, 3)
                selected_depts = sample(departments, min(num_depts, len(departments)))

                for dept in selected_depts:
                    if exam_deps_created >= SCALE_LIMITS["exam_departments"]:
                        break

                    existing = (
                        await session.execute(
                            select(ExamDepartment).where(
                                ExamDepartment.exam_id == exam.id,
                                ExamDepartment.department_id == dept.id,
                            )
                        )
                    ).scalar_one_or_none()
                    if not existing:
                        exam_dep = ExamDepartment(
                            exam_id=exam.id, department_id=dept.id
                        )
                        session.add(exam_dep)
                        exam_deps_created += 1

            self.seeded_data["exam_departments"] = exam_deps_created
            logger.info(
                f"✓ Exam departments: {exam_deps_created} relationships created"
            )

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

    async def _seed_timetable_jobs(self):
        """Seed timetable jobs"""
        async with db_manager.get_db_transaction() as session:
            logger.info("📅 Seeding timetable jobs...")

            sessions = (await session.execute(select(AcademicSession))).scalars().all()
            configs = (
                (await session.execute(select(SystemConfiguration))).scalars().all()
            )
            users = (await session.execute(select(User))).scalars().all()

            if not sessions or not configs or not users:
                logger.error("Missing required data for timetable job seeding")
                return

            jobs_created = 0
            for session_obj in sessions:
                if jobs_created >= SCALE_LIMITS["timetable_jobs"]:
                    break

                # Each session can have 1-2 jobs
                num_jobs = randint(1, 2)
                for _ in range(num_jobs):
                    if jobs_created >= SCALE_LIMITS["timetable_jobs"]:
                        break

                    job = TimetableJob(
                        session_id=session_obj.id,
                        configuration_id=choice(configs).id,
                        initiated_by=choice(users).id,
                        status=choice(["queued", "running", "completed", "failed"]),
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
                        solver_phase=choice(["initial", "optimization", "final"]),
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
                            fake.date_time_this_year() if randint(1, 3) > 1 else None
                        ),
                    )
                    session.add(job)
                    jobs_created += 1

            self.seeded_data["timetable_jobs"] = jobs_created
            logger.info(f"✓ Timetable jobs: {jobs_created} jobs created")

    async def _seed_timetable_versions(self):
        """Seed enhanced timetable versions"""
        async with db_manager.get_db_transaction() as session:
            logger.info("📋 Seeding timetable versions...")
            jobs = (await session.execute(select(TimetableJob))).scalars().all()
            users = (await session.execute(select(User))).scalars().all()
            if not jobs or not users:
                logger.warning("No jobs or users to create versions for.")
                return

            versions_created = 0
            all_versions = []
            for job in jobs:
                parent_version = None
                for i in range(randint(1, 3)):  # Create 1-3 versions per job
                    if versions_created >= SCALE_LIMITS["timetable_versions"]:
                        break
                    version = TimetableVersion(
                        job_id=job.id,
                        parent_version_id=parent_version.id if parent_version else None,
                        version_type=choice(["primary", "draft", "what-if", "final"]),
                        archive_date=(
                            fake.date_time_this_year() if randint(1, 10) == 1 else None
                        ),
                        is_published=choice([True, False, False]),
                        version_number=i + 1,
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
                    await session.flush()  # Flush to get ID
                    all_versions.append(version)
                    parent_version = version  # Next one can be a child
                    versions_created += 1

            self.seeded_data["timetable_versions"] = versions_created
            logger.info(f"✓ Timetable versions: {versions_created} versions created")

    async def _seed_version_metadata(self):
        """Seed version metadata for timetable versions"""
        async with db_manager.get_db_transaction() as session:
            logger.info("📝 Seeding version metadata...")
            versions = (await session.execute(select(TimetableVersion))).scalars().all()
            if not versions:
                logger.warning("No versions to add metadata to.")
                return

            metadata_created = 0
            for version in versions:
                if metadata_created >= SCALE_LIMITS["version_metadata"]:
                    break
                if randint(1, 2) == 1:  # 50% chance of having metadata
                    metadata = VersionMetadata(
                        version_id=version.id,
                        title=f"{version.version_type.title()} Version - {fake.bs()}",
                        description=fake.paragraph(nb_sentences=3),
                        tags={
                            "tags": sample(
                                ["draft", "final", "approved", "experimental"],
                                randint(1, 3),
                            )
                        },
                    )
                    session.add(metadata)
                    metadata_created += 1

            self.seeded_data["version_metadata"] = metadata_created
            logger.info(f"✓ Version metadata: {metadata_created} created")

    async def _seed_version_dependencies(self):
        """Seed dependencies between timetable versions"""
        async with db_manager.get_db_transaction() as session:
            logger.info("🔗 Seeding version dependencies...")
            versions = (await session.execute(select(TimetableVersion))).scalars().all()
            if len(versions) < 2:
                logger.warning("Not enough versions to create dependencies.")
                return

            dependencies_created = 0
            for _ in range(SCALE_LIMITS["version_dependencies"]):
                version, depends_on = sample(versions, 2)
                if version.id == depends_on.id:  # Avoid self-dependency
                    continue

                existing = (
                    await session.execute(
                        select(VersionDependency).where(
                            VersionDependency.version_id == version.id,
                            VersionDependency.depends_on_version_id == depends_on.id,
                        )
                    )
                ).scalar_one_or_none()

                if not existing:
                    dependency = VersionDependency(
                        version_id=version.id,
                        depends_on_version_id=depends_on.id,
                        dependency_type=choice(
                            ["based_on", "merges", "conflicts_with"]
                        ),
                    )
                    session.add(dependency)
                    dependencies_created += 1

            self.seeded_data["version_dependencies"] = dependencies_created
            logger.info(f"✓ Version dependencies: {dependencies_created} created")

    async def _seed_timetable_assignments(self):
        """Seed timetable assignments for exams"""
        logger.info("✍️ Seeding timetable assignments...")

        async with db_manager.get_db_transaction() as session:
            # CORRECTED: Eagerly load the 'job' relationship to prevent lazy-loading errors in async context.
            versions_query = select(TimetableVersion).options(
                selectinload(TimetableVersion.job)
            )
            versions = (await session.execute(versions_query)).scalars().all()

            rooms = (await session.execute(select(Room))).scalars().all()
            exams = (await session.execute(select(Exam))).scalars().all()

            if not versions or not rooms or not exams:
                logger.warning(
                    "Cannot seed assignments without versions, rooms, and exams."
                )
                return

            time_slot_periods = ["Morning", "Afternoon", "Evening"]
            assignments_created = 0

            for version in versions:
                if assignments_created >= SCALE_LIMITS["timetable_assignments"]:
                    break

                # Get session for this version - This will now work without a new DB call
                session_id = version.job.session_id
                session_exams = [e for e in exams if e.session_id == session_id]

                if not session_exams:
                    continue

                session_obj = await session.get(AcademicSession, session_id)
                exam_period_days = 10  # Assume a 2-week exam period

                for exam in sample(session_exams, min(len(session_exams), 50)):
                    if assignments_created >= SCALE_LIMITS["timetable_assignments"]:
                        break

                    # Simple scheduling logic
                    assert session_obj
                    exam_date = session_obj.start_date + timedelta(
                        days=randint(30, 30 + exam_period_days)
                    )
                    time_slot_period = choice(time_slot_periods)

                    # Split students across rooms if needed
                    students_to_assign = exam.expected_students
                    assigned_rooms = []

                    while students_to_assign > 0 and len(assigned_rooms) < 5:
                        room = choice(rooms)
                        if room in assigned_rooms:
                            continue

                        assigned_rooms.append(room)
                        allocated_capacity = min(
                            students_to_assign, room.exam_capacity or room.capacity
                        )

                        assignment = TimetableAssignment(
                            exam_id=exam.id,
                            room_id=room.id,
                            version_id=version.id,
                            exam_date=exam_date,
                            time_slot_period=time_slot_period,
                            student_count=allocated_capacity,
                            is_confirmed=choice([True, False]),
                            allocated_capacity=allocated_capacity,
                            is_primary=(len(assigned_rooms) == 1),
                            seating_arrangement=(
                                {"layout": "standard"} if randint(1, 3) == 1 else None
                            ),
                        )
                        session.add(assignment)
                        assignments_created += 1
                        students_to_assign -= allocated_capacity

            self.seeded_data["timetable_assignments"] = assignments_created
            logger.info(f"✓ Timetable assignments: {assignments_created} created")

    async def _seed_exam_invigilators(self):
        """Seed exam invigilators based on timetable assignments"""
        async with db_manager.get_db_transaction() as session:
            logger.info("👮 Seeding exam invigilators...")

            # Fetch all timetable assignments
            assignments = (
                (await session.execute(select(TimetableAssignment))).scalars().all()
            )

            # Fetch staff who can invigilate
            invigilator_staff = (
                (
                    await session.execute(
                        select(Staff).where(Staff.can_invigilate == true())
                    )
                )
                .scalars()
                .all()
            )

            if not assignments:
                logger.warning("No timetable assignments found to assign invigilators.")
                return
            if not invigilator_staff:
                logger.warning("No staff members available for invigilation.")
                return

            invigilators_created = 0
            for assignment in assignments:
                if invigilators_created >= SCALE_LIMITS["exam_invigilators"]:
                    break

                # Calculate number of invigilators based on student count
                student_count = assignment.student_count
                ratio = 50  # 1 invigilator per 50 students
                num_invigilators = max(1, math.ceil(student_count / ratio))

                if len(invigilator_staff) < num_invigilators:
                    continue  # Not enough staff to assign

                selected_staff = sample(invigilator_staff, num_invigilators)

                for i, staff in enumerate(selected_staff):
                    if invigilators_created >= SCALE_LIMITS["exam_invigilators"]:
                        break

                    # Check for existing assignment
                    existing = (
                        await session.execute(
                            select(ExamInvigilator).where(
                                ExamInvigilator.timetable_assignment_id
                                == assignment.id,
                                ExamInvigilator.staff_id == staff.id,
                            )
                        )
                    ).scalar_one_or_none()

                    if not existing:
                        invigilator = ExamInvigilator(
                            timetable_assignment_id=assignment.id,
                            staff_id=staff.id,
                            is_chief_invigilator=(i == 0),  # First one is chief
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

            if not staff_members or not sessions:
                logger.warning("Cannot seed unavailability without staff and sessions.")
                return

            time_slot_periods = [
                "Early Morning",
                "Morning",
                "Afternoon",
                "Evening",
                "Night",
            ]
            unavailability_created = 0

            for staff in staff_members:
                if unavailability_created >= SCALE_LIMITS["staff_unavailability"]:
                    break

                # Each staff member might have 0-3 unavailability entries
                for _ in range(randint(0, 3)):
                    if unavailability_created >= SCALE_LIMITS["staff_unavailability"]:
                        break

                    session_obj = choice(sessions)
                    start_date = _to_date(session_obj.start_date)
                    end_date = _to_date(session_obj.end_date)
                    if start_date >= end_date:
                        continue

                    days_range = (end_date - start_date).days
                    unavailable_date = start_date + timedelta(
                        days=randint(0, days_range)
                    )

                    unavailability = StaffUnavailability(
                        staff_id=staff.id,
                        session_id=session_obj.id,
                        unavailable_date=unavailable_date,
                        # 50% chance of being for the whole day, 50% for a specific period
                        time_slot_period=(
                            choice(time_slot_periods) if randint(1, 2) == 1 else None
                        ),
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

    async def _seed_timetable_edits(self):
        """Seed timetable edits for different versions"""
        async with db_manager.get_db_transaction() as session:
            logger.info("✏️ Seeding timetable edits...")

            assignments = (
                (await session.execute(select(TimetableAssignment))).scalars().all()
            )
            users = (await session.execute(select(User))).scalars().all()
            rooms = (await session.execute(select(Room))).scalars().all()

            if not assignments or not users or not rooms:
                logger.warning(
                    "Cannot seed edits without assignments, users, and rooms."
                )
                return

            edits_created = 0
            time_slot_periods = ["Morning", "Afternoon", "Evening"]

            for assignment in assignments:
                if edits_created >= SCALE_LIMITS["timetable_edits"]:
                    break

                # Create 0-2 edits per assignment
                for _ in range(randint(0, 2)):
                    if edits_created >= SCALE_LIMITS["timetable_edits"]:
                        break

                    edit_type = choice(["reschedule", "room_change", "cancel"])
                    old_values, new_values = {}, {}

                    if edit_type == "reschedule":
                        # normalize exam_date to Python date
                        exam_date_value = assignment.exam_date
                        if hasattr(exam_date_value, "to_pydatetime"):
                            exam_date_value = exam_date_value.to_pydatetime().date()  # type: ignore
                        elif isinstance(exam_date_value, datetime):
                            exam_date_value = exam_date_value.date()
                        elif not isinstance(exam_date_value, date):
                            exam_date_value = date(
                                exam_date_value.year,  # type: ignore
                                exam_date_value.month,  # type: ignore
                                exam_date_value.day,  # type: ignore
                            )

                        old_values = {
                            "exam_date": str(assignment.exam_date),
                            "time_slot_period": assignment.time_slot_period,
                        }
                        new_values = {
                            "exam_date": str(
                                exam_date_value + timedelta(days=randint(-2, 2))
                            ),
                            "time_slot_period": choice(time_slot_periods),
                        }

                    elif edit_type == "room_change":
                        old_values = {"room_id": str(assignment.room_id)}
                        new_values = {"room_id": str(choice(rooms).id)}

                    elif edit_type == "cancel":
                        old_values = {"status": "scheduled"}
                        new_values = {"status": "cancelled"}

                    edit = TimetableEdit(
                        version_id=assignment.version_id,
                        exam_id=assignment.exam_id,
                        edited_by=choice(users).id,
                        edit_type=edit_type,
                        old_values=old_values,
                        new_values=new_values,
                        reason=fake.sentence(),
                        validation_status=choice(["pending", "approved", "rejected"]),
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

            if not users or not sessions:
                logger.warning(
                    "Cannot seed file uploads without users and academic sessions."
                )
                return

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
                if events_created >= SCALE_LIMITS["system_events"] or not users:
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

            if not users or not events:
                logger.warning("Cannot seed notifications without users and events.")
                return

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
                if logs_created >= SCALE_LIMITS["audit_logs"]:
                    break

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

        for entity in sorted(self.seeded_data.keys()):
            count = self.seeded_data[entity]
            limit = SCALE_LIMITS.get(entity, "N/A")
            logger.info(f"{entity.replace('_', ' ').title():30}: {count:6,} / {limit}")

        logger.info("=" * 50)


async def main():
    """Main entry point for the fake seeder with argument parsing"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed the database with comprehensive fake data"
    )
    parser.add_argument("--database-url", help="Database URL override")
    parser.add_argument(
        "--drop-existing", action="store_true", help="Drop existing data before seeding"
    )
    parser.add_argument(
        "--magnitude",
        type=int,
        choices=[1, 2, 3, 4, 5],
        default=3,
        help="Set problem size magnitude level (1=Basic/100 students, 2=Small/500, 3=Medium/2000, 4=Large/5000, 5=Enterprise/10000)",
    )

    args = parser.parse_args()

    seeder = ComprehensiveFakeSeeder(args.database_url)
    # Set magnitude level based on command line argument
    seeder.set_magnitude_level(args.magnitude)
    await seeder.run(drop_existing=args.drop_existing)


if __name__ == "__main__":
    asyncio.run(main())
