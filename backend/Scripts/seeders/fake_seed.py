# backend\Scripts\seeders\fake_seed.py

# Baze University Adaptive Exam Timetabling System - Comprehensive Fake Seeder

from collections import defaultdict
import os
import sys
import asyncio
import argparse
import logging
import math
import random
from pathlib import Path
from datetime import datetime, date, time, timedelta
from typing import Any, Dict, Set, List, Optional
from uuid import uuid4

from faker import Faker
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# --- Project Setup ---
# Add the backend directory to the Python path to import app modules.
try:
    BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
    if str(BACKEND_DIR) not in sys.path:
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
        TimeSlotTemplate,
        TimeSlotTemplatePeriod,
        TimetableEdit,
        TimetableJob,
        TimetableVersion,
        UploadedFile,
        User,
        UserNotification,
        VersionDependency,
        VersionMetadata,
        TimetableScenario,
        TimetableLock,
        AssignmentChangeRequest,
        ConflictReport,
        TimetableConflict,
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
    Generates realistic and schema-compliant fake data for the exam timetabling system.
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
        self.seeded_data: Dict[str, int] = defaultdict(int)
        self.generated_matrics: Set[str] = set()
        self.demo_users: Dict[str, User] = {}
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
        Sets the data magnitude level, updating SCALE_LIMITS for all entities.
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

        base_counts["users"] = base_counts["students"] + base_counts["staff"] + 3

        global SCALE_LIMITS
        SCALE_LIMITS = {
            **base_counts,
            "timeslot_templates": 3,
            "timeslot_template_periods": 3 * 3,
            "student_enrollments": base_counts["students"]
            * base_counts["academic_sessions"],
            "course_registrations": int(base_counts["students"] * 6.0),
            "course_instructors": int(base_counts["courses"] * 1.5),
            "exam_departments": int(base_counts["exams"] * 1.2),
            "exam_prerequisites": int(base_counts["exams"] * 0.2),
            "staff_unavailability": int(base_counts["staff"] * 2),
            "timetable_jobs": 5,
            "timetable_versions": 10,
            "timetable_assignments": int(base_counts["exams"] * 1.1),
            "exam_invigilators": int(base_counts["exams"] * 2),
            "timetable_edits": 50,
            "audit_logs": 500,
            "system_configurations": 3,
            "constraint_categories": 5,
            "constraint_rules": 17,
            "configuration_constraints": 25,
            "system_events": 50,
            "user_notifications": 100,
            "file_upload_sessions": 10,
            "uploaded_files": 15,
            "session_templates": 5,
            "version_metadata": 10,
            "version_dependencies": 8,
            "timetable_scenarios": 3,
            "timetable_locks": 0,
            "timetable_conflicts": 40,
            "assignment_change_requests": 20,
            "conflict_reports": 30,
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

            await self._seed_core_entities()
            await self._seed_academic_structure()
            await self._seed_demo_users()
            await self._seed_people_and_users()
            await self._seed_course_instructors_and_unavailability()
            await self._seed_scheduling_data()
            await self._seed_hitl_and_versioning()
            await self._seed_system_and_logging()

            await self._log_data_complexity_analysis()

            logger.info("🎉 Comprehensive fake data seeding completed successfully!")
            await self.print_summary()

        except Exception as e:
            logger.error(
                f"💥 An unexpected error occurred during seeding: {e}", exc_info=True
            )
            raise

    async def _clear_all_data(self):
        """Clears all data from tables in reverse dependency order."""
        async with db_manager.get_db_transaction() as session:
            tables_to_clear = [
                "audit_logs",
                "user_notifications",
                "system_events",
                "assignment_change_requests",
                "conflict_reports",
                "timetable_conflicts",
                "timetable_edits",
                "exam_invigilators",
                "timetable_assignments",
                "timetable_locks",
                "version_dependencies",
                "version_metadata",
                "uploaded_files",
                "timetable_versions",
                "timetable_jobs",
                "timetable_scenarios",
                "file_upload_sessions",
                "exam_prerequisites_association",
                "exam_departments",
                "configuration_constraints",
                "course_instructors",
                "course_registrations",
                "student_enrollments",
                "staff_unavailability",
                "exams",
                "courses",
                "staff",
                "students",
                "programmes",
                "departments",
                "faculties",
                "rooms",
                "room_types",
                "buildings",
                "timeslot_template_periods",
                "timeslot_templates",
                "academic_sessions",
                "session_templates",
                "constraint_rules",
                "constraint_categories",
                "system_configurations",
                "users",
            ]
            for table in tables_to_clear:
                try:
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
        await self._seed_timeslot_templates()

    async def _seed_academic_structure(self):
        logger.info("Phase 2: Seeding Academic Structure...")
        await self._seed_faculties_departments_programmes()
        await self._seed_academic_sessions()
        await self._seed_courses()

    async def _seed_demo_users(self):
        logger.info("Phase 3: Seeding Demo User Accounts...")
        await self._seed_demo_user_accounts()

    async def _seed_people_and_users(self):
        logger.info("Phase 4: Seeding People and Linking Users...")
        await self._seed_students_and_create_users()
        await self._seed_staff_and_create_users()

    async def _seed_course_instructors_and_unavailability(self):
        logger.info("Phase 5: Seeding Staff-Course Relations...")
        await self._seed_course_instructors()
        await self._seed_staff_unavailability()

    async def _seed_scheduling_data(self):
        logger.info("Phase 6: Seeding Core Scheduling Data...")
        await self._seed_exams_and_registrations()
        await self._seed_exam_relations()

    async def _seed_hitl_and_versioning(self):
        logger.info("Phase 7: Seeding Timetabling, HITL, and Versioning...")
        await self._seed_timetable_jobs_and_versions()
        await self._seed_timetable_assignments_and_invigilators()
        await self._seed_hitl_entities()

    async def _seed_system_and_logging(self):
        logger.info("Phase 8: Seeding System, Logging, and Feedback Entities...")
        await self._seed_timetable_edits()
        await self._seed_file_uploads()
        await self._seed_system_events_and_notifications()
        await self._seed_audit_logs()
        await self._seed_feedback_and_reporting_entities()

    # --- Detailed Seeding Methods ---

    async def _seed_infrastructure(self):
        """Seed buildings, room types, and rooms."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  🏢 Seeding infrastructure (buildings, rooms)...")
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
            buildings = [
                Building(code=code, name=f"{code} Building", is_active=True)
                for code in list(building_codes)[: SCALE_LIMITS["buildings"]]
            ]
            session.add_all(buildings)
            await session.flush()
            self.seeded_data["buildings"] = len(buildings)

            room_type_names = [
                "Classroom",
                "Laboratory",
                "Auditorium",
                "Seminar Room",
                "Workshop",
                "Office",
            ]
            room_types = [
                RoomType(name=name, description=f"{name} space", is_active=True)
                for name in room_type_names
            ]
            session.add_all(room_types)
            await session.flush()
            self.seeded_data["room_types"] = len(room_types)

            rooms = []
            generated_room_codes = set()
            for _ in range(SCALE_LIMITS["rooms"]):
                building = random.choice(buildings)
                room_type = random.choice(room_types)
                capacity = {
                    "Auditorium": random.randint(200, 500),
                    "Classroom": random.randint(40, 150),
                    "Laboratory": random.randint(30, 60),
                }.get(room_type.name, random.randint(20, 40))

                while True:
                    code = f"{building.code}-{random.randint(100, 999)}"
                    if code not in generated_room_codes:
                        generated_room_codes.add(code)
                        break

                r = Room(
                    code=code,
                    name=f"{building.name} Room {code.split('-')[1]}",
                    building_id=building.id,
                    room_type_id=room_type.id,
                    capacity=capacity,
                    exam_capacity=max(20, int(capacity * 0.7)),
                    has_projector=random.choice([True, False]),
                    has_computers=room_type.name == "Laboratory",
                    is_active=True,
                    has_ac=random.choice([True, True, False]),
                    max_inv_per_room=max(1, math.ceil(capacity / 50)),
                    notes=fake.sentence() if random.random() < 0.2 else None,
                    overbookable=random.random() < 0.1,
                )
                rooms.append(r)
            session.add_all(rooms)
            self.seeded_data["rooms"] = len(rooms)
            logger.info(
                f"  ✓ Seeded {len(buildings)} buildings, {len(room_types)} room types, {len(rooms)} rooms."
            )

    async def _seed_constraints_and_config(self):
        """
        FIXED: Seed system configurations and constraints with realistic parameters.
        This version uses raw SQL for a temporary admin user to bypass a potential
        mismatch between the SQLAlchemy User model's 'role' column type and the
        actual database schema (varchar vs enum).
        """
        async with db_manager.get_db_transaction() as session:
            logger.info(
                "  ⚙️ Seeding realistic system configurations and constraints..."
            )

            # --- Create a temporary admin user via raw SQL to get a valid ID ---
            temp_admin_email = "temp_admin_for_config@baze.edu.ng"
            # Using simple varchar insert for the role, which matches the schema
            await session.execute(
                text(
                    "INSERT INTO exam_system.users (email, first_name, last_name, is_active, is_superuser, role, created_at, updated_at) "
                    "VALUES (:email, 'Temp', 'Admin', true, true, 'admin', now(), now())"
                ),
                {"email": temp_admin_email},
            )

            # Fetch the ID of the user we just created
            admin_user_result = await session.execute(
                select(User).where(User.email == temp_admin_email)
            )
            temp_admin_user = admin_user_result.scalars().first()

            if not temp_admin_user:
                logger.error(
                    "Failed to create and fetch temporary admin user. Cannot seed configurations."
                )
                raise Exception(
                    "Could not create temporary admin user for seeding configurations."
                )

            admin_user_id = temp_admin_user.id

            # --- Seed Categories and Rules (as before) ---
            categories_data = [
                "Student Constraints",
                "Resource",
                "Spatial",
                "Pedagogical",
                "Fairness",
            ]
            categories = [ConstraintCategory(name=c) for c in categories_data]
            session.add_all(categories)
            await session.flush()
            self.seeded_data["constraint_categories"] = len(categories)
            cat_map = {c.name: c for c in categories}

            rules_data = [
                (
                    "UNIFIED_STUDENT_CONFLICT",
                    "Student Time Conflict",
                    "A student cannot take two exams at the same time.",
                    "hard",
                    "Student Constraints",
                    100.0,
                    {},
                ),
                (
                    "ROOM_CAPACITY_HARD",
                    "Room Capacity Exceeded",
                    "The number of students in a room cannot exceed its exam capacity.",
                    "hard",
                    "Spatial",
                    100.0,
                    {},
                ),
                (
                    "MINIMUM_INVIGILATORS",
                    "Minimum Invigilators",
                    "Ensure enough invigilators are assigned per room based on student count.",
                    "hard",
                    "Resource",
                    100.0,
                    {"students_per_invigilator": 50},
                ),
                (
                    "INSTRUCTOR_CONFLICT",
                    "Instructor Self-Invigilation",
                    "An instructor for a course cannot invigilate the exam for that same course.",
                    "hard",
                    "Pedagogical",
                    100.0,
                    {},
                ),
                (
                    "MAX_EXAMS_PER_STUDENT_PER_DAY",
                    "Max Exams Per Student Per Day",
                    "A student cannot take more than a specified number of exams in a single day.",
                    "hard",
                    "Student Constraints",
                    100.0,
                    {"max_exams_per_day": 2},
                ),
                (
                    "MINIMUM_GAP",
                    "Minimum Gap Between Exams",
                    "Penalizes scheduling a student's exams too close together on the same day.",
                    "soft",
                    "Student Constraints",
                    80.0,
                    {"min_gap_slots": 1},
                ),
                (
                    "OVERBOOKING_PENALTY",
                    "Room Overbooking Penalty",
                    "Penalize assigning more students to a room than its capacity (for overbookable rooms).",
                    "soft",
                    "Spatial",
                    5.0,
                    {},
                ),
                (
                    "PREFERENCE_SLOTS",
                    "Course Slot Preference",
                    "Penalize scheduling exams outside of their preferred slots (e.g., 'morning only').",
                    "soft",
                    "Pedagogical",
                    10.0,
                    {},
                ),
                (
                    "INVIGILATOR_LOAD_BALANCE",
                    "Invigilator Workload Balance",
                    "Penalize uneven distribution of total invigilation slots among staff.",
                    "soft",
                    "Fairness",
                    15.0,
                    {},
                ),
                (
                    "CARRYOVER_STUDENT_CONFLICT",
                    "Carryover Student Conflict",
                    "Allow, but penalize, scheduling conflicts for students with a 'carryover' registration status.",
                    "soft",
                    "Student Constraints",
                    50.0,
                    {"max_allowed_conflicts": 3},
                ),
                (
                    "INVIGILATOR_AVAILABILITY",
                    "Invigilator Availability",
                    "Penalize assigning invigilators during their stated unavailable times.",
                    "soft",
                    "Resource",
                    75.0,
                    {},
                ),
                (
                    "DAILY_WORKLOAD_BALANCE",
                    "Daily Exam Load Balance",
                    "Penalize uneven distribution of the total number of exams scheduled across different days.",
                    "soft",
                    "Fairness",
                    10.0,
                    {},
                ),
                (
                    "ROOM_SEQUENTIAL_USE",
                    "Room Sequential Use",
                    "Ensures no new exam starts in a room while another is ongoing (flexible mode only).",
                    "hard",
                    "Spatial",
                    100.0,
                    {},
                ),
                (
                    "ROOM_DURATION_HOMOGENEITY",
                    "Room Duration Homogeneity",
                    "Penalizes using a room for exams of different durations on the same day (flexible mode only).",
                    "soft",
                    "Fairness",
                    80.0,
                    {},
                ),
            ]
            rules = []
            for code, name, desc, c_type, cat_name, weight, params in rules_data:
                category = cat_map.get(cat_name)
                if not category:
                    continue
                rule = ConstraintRule(
                    code=code,
                    name=name,
                    description=desc,
                    constraint_type=c_type,
                    category_id=category.id,
                    is_active=True,
                    default_weight=weight,
                    constraint_definition={
                        "description": desc,
                        "parameters": [
                            {"key": p_key, "value": p_val, "type": type(p_val).__name__}
                            for p_key, p_val in params.items()
                        ],
                    },
                )
                rules.append(rule)
            session.add_all(rules)
            await session.flush()
            self.seeded_data["constraint_rules"] = len(rules)

            # --- Seed Configurations using the temporary admin user ID ---
            config_names = ["Default", "Fast Solve", "High Quality"]
            configs = [
                SystemConfiguration(
                    name=name,
                    description=f"Parameters for {name}",
                    created_by=admin_user_id,
                    is_default=(name == "Default"),
                )
                for name in config_names
            ]
            session.add_all(configs)
            await session.flush()
            self.seeded_data["system_configurations"] = len(configs)

            config_constraints = [
                ConfigurationConstraint(
                    configuration_id=config.id,
                    constraint_id=rule.id,
                    weight=rule.default_weight,
                    is_enabled=True,
                )
                for config in configs
                for rule in rules
            ]
            session.add_all(config_constraints)
            self.seeded_data["configuration_constraints"] = len(config_constraints)

            logger.info(
                f"  ✓ Seeded {len(categories)} categories, {len(rules)} rules, {len(configs)} configs, and {len(config_constraints)} links."
            )

    async def _seed_session_templates(self):
        """Seed session templates."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  📄 Seeding session templates...")
            templates_data = ["Standard Semester", "Fast-Track", "Postgraduate"]
            templates = [
                SessionTemplate(
                    name=name, description=f"Template for {name}", is_active=True
                )
                for name in templates_data
            ]
            session.add_all(templates)
            self.seeded_data["session_templates"] = len(templates)
            logger.info(f"  ✓ Seeded {len(templates)} session templates.")

    async def _seed_timeslot_templates(self):
        """Seed timeslot templates and their periods."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  🕰️  Seeding timeslot templates...")
            templates, periods = [], []

            std_template = TimeSlotTemplate(
                name="Standard Weekday", description="9am, 12pm, 3pm slots"
            )
            templates.append(std_template)
            session.add(std_template)
            await session.flush()
            periods.extend(
                [
                    TimeSlotTemplatePeriod(
                        timeslot_template_id=std_template.id,
                        period_name="Morning",
                        start_time=time(9, 0),
                        end_time=time(12, 0),
                    ),
                    TimeSlotTemplatePeriod(
                        timeslot_template_id=std_template.id,
                        period_name="Afternoon",
                        start_time=time(12, 0),
                        end_time=time(15, 0),
                    ),
                    TimeSlotTemplatePeriod(
                        timeslot_template_id=std_template.id,
                        period_name="Evening",
                        start_time=time(15, 0),
                        end_time=time(18, 0),
                    ),
                ]
            )

            con_template = TimeSlotTemplate(
                name="Condensed Day", description="Two longer slots per day"
            )
            templates.append(con_template)
            session.add(con_template)
            await session.flush()
            periods.extend(
                [
                    TimeSlotTemplatePeriod(
                        timeslot_template_id=con_template.id,
                        period_name="AM",
                        start_time=time(9, 30),
                        end_time=time(12, 30),
                    ),
                    TimeSlotTemplatePeriod(
                        timeslot_template_id=con_template.id,
                        period_name="PM",
                        start_time=time(13, 30),
                        end_time=time(16, 30),
                    ),
                ]
            )

            session.add_all(periods)
            self.seeded_data["timeslot_templates"] = len(templates)
            self.seeded_data["timeslot_template_periods"] = len(periods)
            logger.info(
                f"  ✓ Seeded {len(templates)} timeslot templates with {len(periods)} periods."
            )

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
                "LAW": ["PUB", "PRV"],
                "ART": ["ENG", "HIS"],
            }

            faculties = [
                Faculty(code=code, name=f"Faculty of {name}", is_active=True)
                for code, name in list(faculty_data.items())[
                    : SCALE_LIMITS["faculties"]
                ]
            ]
            session.add_all(faculties)
            await session.flush()
            self.seeded_data["faculties"] = len(faculties)

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
        """Seed academic sessions representing exam periods."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  🗓️ Seeding academic sessions (exam periods)...")
            templates = (
                (await session.execute(select(TimeSlotTemplate))).scalars().all()
            )
            if not templates:
                logger.error(
                    "  ❌ No timeslot templates found. Cannot create academic sessions."
                )
                return

            std_template = next(
                (t for t in templates if t.name == "Standard Weekday"), templates[0]
            )
            sessions, current_year = [], datetime.now().year
            for i in range(SCALE_LIMITS["academic_sessions"]):
                year, is_active_session = current_year - i, i == 0
                start_date = (
                    date(year, 11, 15) if is_active_session else date(year, 5, 10)
                )
                end_date = start_date + timedelta(days=14 if is_active_session else 21)
                template_id = (
                    std_template.id
                    if is_active_session
                    else random.choice(templates).id
                )
                sessions.append(
                    AcademicSession(
                        name=f"{year}/{year+1} Exam Period",
                        semester_system="semester",
                        start_date=start_date,
                        end_date=end_date,
                        is_active=is_active_session,
                        timeslot_template_id=template_id,
                        slot_generation_mode=(
                            "flexible" if is_active_session else "fixed"
                        ),
                    )
                )
            session.add_all(sessions)
            self.seeded_data["academic_sessions"] = len(sessions)
            logger.info(f"  ✓ Seeded {len(sessions)} academic sessions (exam periods).")

    async def _seed_courses(self):
        """Seed courses."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  📚 Seeding courses...")
            departments = (await session.execute(select(Department))).scalars().all()
            if not departments:
                return

            courses, generated_course_codes = [], set()
            course_titles = [
                "Introduction to {topic}",
                "Advanced {topic}",
                "{topic} Theory",
                "Applied {topic}",
                "Principles of {topic}",
            ]
            course_topics = [
                "Algorithms",
                "Databases",
                "Networking",
                "Software Engineering",
                "Artificial Intelligence",
                "Calculus",
                "Linear Algebra",
                "Mechanics",
                "Thermodynamics",
                "Microeconomics",
                "Marketing",
            ]

            for _ in range(SCALE_LIMITS["courses"]):
                dept = random.choice(departments)
                level = random.choice([100, 200, 300, 400])
                while True:
                    code = f"{dept.code}{level+random.randint(1, 99)}"
                    if code not in generated_course_codes:
                        generated_course_codes.add(code)
                        break

                c = Course(
                    code=code,
                    title=random.choice(course_titles).format(
                        topic=random.choice(course_topics)
                    ),
                    department_id=dept.id,
                    credit_units=random.choice([2, 3, 4]),
                    course_level=level,
                    is_practical=random.random() < 0.15,
                    exam_duration_minutes=random.choice([60, 120, 180]),
                    morning_only=random.random() < 0.1,
                )
                courses.append(c)
            session.add_all(courses)
            self.seeded_data["courses"] = len(courses)
            logger.info(f"  ✓ Seeded {len(courses)} courses.")

    async def _seed_demo_user_accounts(self):
        """Creates the three main demo user accounts: admin, staff, and student."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  👥 Seeding demo user accounts (admin, staff, student)...")
            demo_password = hash_password("demo")

            # 1. Create Demo Admin
            admin_user = User(
                email="admin@baze.edu.ng",
                first_name="Demo",
                last_name="Admin",
                password_hash=demo_password,
                is_active=True,
                is_superuser=True,
                role="admin",
            )
            session.add(admin_user)
            self.demo_users["admin"] = admin_user

            # 2. Create Demo Staff and linked User
            departments = (await session.execute(select(Department))).scalars().all()
            if not departments:
                logger.error("Cannot create demo staff user without departments.")
                return

            staff_user = User(
                email="staff@baze.edu.ng",
                first_name="Demo",
                last_name="Staff",
                password_hash=demo_password,
                is_active=True,
                role="staff",
            )
            session.add(staff_user)
            await session.flush([staff_user])
            demo_staff = Staff(
                user_id=staff_user.id,
                staff_number="ST_DEMO",
                first_name="Demo",
                last_name="Staff",
                department_id=random.choice(departments).id,
                staff_type="academic",
                can_invigilate=True,
                is_active=True,
            )
            session.add(demo_staff)

            # 3. Create Demo Student and linked User
            programmes = (
                (
                    await session.execute(
                        select(Programme).options(selectinload(Programme.department))
                    )
                )
                .scalars()
                .all()
            )
            if not programmes:
                logger.error("Cannot create demo student user without programmes.")
                return

            student_user = User(
                email="student@baze.edu.ng",
                first_name="Demo",
                last_name="Student",
                password_hash=demo_password,
                is_active=True,
                role="student",
            )
            session.add(student_user)
            await session.flush([student_user])

            demo_prog = random.choice(programmes)
            current_year = datetime.now().year
            demo_entry_year = current_year - random.randint(
                0, demo_prog.duration_years - 1
            )

            demo_student = Student(
                user_id=student_user.id,
                matric_number=f"BU/{str(demo_entry_year)[-2:]}/{demo_prog.department.code}/_DEMO",
                first_name="Demo",
                last_name="Student",
                entry_year=demo_entry_year,
                programme_id=demo_prog.id,
            )
            session.add(demo_student)

            self.seeded_data["users"] += 3
            self.seeded_data["staff"] += 1
            self.seeded_data["students"] += 1
            logger.info(
                "  ✓ Seeded 3 demo accounts with linked staff/student profiles."
            )

    async def _seed_students_and_create_users(self):
        """Seeds students and creates a corresponding user account for each."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  👨‍🎓 Seeding students and their user accounts...")
            programmes = (
                (
                    await session.execute(
                        select(Programme).options(selectinload(Programme.department))
                    )
                )
                .scalars()
                .all()
            )
            if not programmes:
                logger.warning("  - Skipping student seeding: no programmes found.")
                return

            students_created = []
            users_created = 0
            current_year = datetime.now().year
            default_password = hash_password("password123")

            # We already created 1 demo student, so generate N-1
            for i in range(SCALE_LIMITS["students"] - 1):
                first_name = fake.first_name()
                last_name = fake.last_name()
                email = f"{first_name}.{last_name}{random.randint(1,999)}@fake.baze.edu.ng".lower()

                user = User(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password_hash=default_password,
                    is_active=True,
                    role="student",
                )
                session.add(user)
                await session.flush([user])
                users_created += 1

                prog = random.choice(programmes)
                entry_year = current_year - random.randint(0, prog.duration_years - 1)

                student = Student(
                    user_id=user.id,
                    matric_number=f"BU/{str(entry_year)[-2:]}/{prog.department.code}/{i+1:04d}",
                    first_name=first_name,
                    last_name=last_name,
                    entry_year=entry_year,
                    programme_id=prog.id,
                )
                session.add(student)
                students_created.append(student)

            self.seeded_data["students"] += len(students_created)
            self.seeded_data["users"] += users_created

            # Create Enrollments
            all_students = (
                (
                    await session.execute(
                        select(Student).options(selectinload(Student.programme))
                    )
                )
                .scalars()
                .all()
            )
            sessions_list = (
                (await session.execute(select(AcademicSession))).scalars().all()
            )
            enrollments = []
            for student in all_students:
                prog = student.programme
                for sess in sessions_list:
                    level = (
                        int(sess.name.split("/")[0]) - student.entry_year + 1
                    ) * 100
                    if 100 <= level <= (prog.duration_years * 100):
                        enrollments.append(
                            StudentEnrollment(
                                student_id=student.id, session_id=sess.id, level=level
                            )
                        )
            session.add_all(enrollments)
            self.seeded_data["student_enrollments"] = len(enrollments)
            logger.info(
                f"  ✓ Seeded {len(students_created)} additional students, created {users_created} linked users, and {len(enrollments)} enrollments."
            )

    async def _seed_staff_and_create_users(self):
        """Seeds staff and creates a corresponding user account for each."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  👨‍🏫 Seeding staff and their user accounts...")
            departments = (await session.execute(select(Department))).scalars().all()
            if not departments:
                logger.warning("  - Skipping staff seeding: no departments found.")
                return

            staff_created = 0
            users_created = 0
            default_password = hash_password("password123")

            # We already created 1 demo staff, so generate N-1
            for i in range(SCALE_LIMITS["staff"] - 1):
                first_name = fake.first_name()
                last_name = fake.last_name()
                email = f"{first_name}.{last_name}{random.randint(1,99)}@fake.baze.edu.ng".lower()
                user = User(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password_hash=default_password,
                    is_active=True,
                    role="staff",
                )
                session.add(user)
                await session.flush([user])
                users_created += 1

                staff_member = Staff(
                    user_id=user.id,
                    staff_number=f"ST{1001+i}",
                    first_name=first_name,
                    last_name=last_name,
                    department_id=random.choice(departments).id,
                    staff_type="academic",
                    can_invigilate=True,
                    is_active=True,
                )
                session.add(staff_member)
                staff_created += 1

            self.seeded_data["staff"] += staff_created
            self.seeded_data["users"] += users_created
            logger.info(
                f"  ✓ Seeded {staff_created} additional staff and created {users_created} linked users."
            )

    async def _seed_course_instructors(self):
        """Seed the many-to-many relationship between courses and staff."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  🧑‍🏫 Seeding course instructors...")
            courses = (await session.execute(select(Course))).scalars().all()
            staff_q = await session.execute(
                select(Staff).where(Staff.staff_type == "academic")
            )
            staff = staff_q.scalars().all()
            if not courses or not staff:
                return

            instructors = []
            for course in courses:
                num = random.randint(1, 2)
                assigned = random.sample(staff, min(num, len(staff)))
                for staff_member in assigned:
                    instructors.append(
                        CourseInstructor(course_id=course.id, staff_id=staff_member.id)
                    )

            session.add_all(instructors)
            self.seeded_data["course_instructors"] = len(instructors)
            logger.info(f"  ✓ Seeded {len(instructors)} course instructor links.")

    async def _seed_staff_unavailability(self):
        """Seed staff unavailability for the active session."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  🚫 Seeding staff unavailability...")
            staff_members_q = await session.execute(
                select(Staff).where(Staff.can_invigilate == True)
            )
            staff_members = staff_members_q.scalars().all()

            active_session_q = await session.execute(
                select(AcademicSession)
                .where(AcademicSession.is_active == True)
                .options(
                    selectinload(AcademicSession.timeslot_template).selectinload(
                        TimeSlotTemplate.periods
                    )
                )
            )
            active_session = active_session_q.scalars().first()
            if (
                not staff_members
                or not active_session
                or not active_session.timeslot_template
            ):
                return

            exam_period_start = active_session.start_date
            exam_period_duration = (
                active_session.end_date - active_session.start_date
            ).days
            exam_dates = [
                exam_period_start + timedelta(days=i)
                for i in range(exam_period_duration + 1)
                if (exam_period_start + timedelta(days=i)).weekday() < 5
            ]
            periods = active_session.timeslot_template.periods
            unavailabilities = []

            for staff in random.sample(staff_members, k=int(len(staff_members) * 0.7)):
                for _ in range(random.randint(1, 3)):
                    if len(unavailabilities) >= SCALE_LIMITS["staff_unavailability"]:
                        break
                    unavailabilities.append(
                        StaffUnavailability(
                            staff_id=staff.id,
                            session_id=active_session.id,
                            unavailable_date=random.choice(exam_dates),
                            time_slot_period=random.choice(
                                [p.period_name for p in periods]
                            ),
                            reason=random.choice(
                                ["Personal Appointment", "Medical", "Meeting"]
                            ),
                        )
                    )

            session.add_all(unavailabilities)
            self.seeded_data["staff_unavailability"] = len(unavailabilities)
            logger.info(
                f"  ✓ Seeded {len(unavailabilities)} staff unavailability records."
            )

    async def _seed_exams_and_registrations(self):
        """Seed exams and course registrations based on natural enrollment."""
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
            students = (
                (
                    await session.execute(
                        select(Student).options(selectinload(Student.programme))
                    )
                )
                .scalars()
                .all()
            )
            if not courses or not students:
                return

            student_details = {
                s.id: {
                    "dept_id": s.programme.department_id,
                    "level": (int(active_session.name.split("/")[0]) - s.entry_year + 1)
                    * 100,
                }
                for s in students
            }
            registrations, course_enrollment = [], defaultdict(list)
            course_map = {c.id: c for c in courses}

            for student_id, details in student_details.items():
                eligible_courses = [
                    c
                    for c in courses
                    if c.department_id == details["dept_id"]
                    and c.course_level == details["level"]
                ]
                num_courses = random.randint(3, 9)
                for course in random.sample(
                    eligible_courses, min(num_courses, len(eligible_courses))
                ):
                    reg = CourseRegistration(
                        student_id=student_id,
                        course_id=course.id,
                        session_id=active_session.id,
                        registration_type=(
                            "carryover" if random.random() < 0.05 else "normal"
                        ),
                    )
                    registrations.append(reg)
                    course_enrollment[course.id].append(student_id)

            session.add_all(registrations)
            self.seeded_data["course_registrations"] = len(registrations)

            exams, courses_with_students = [], list(course_enrollment.keys())
            exam_course_ids = random.sample(
                courses_with_students,
                min(len(courses_with_students), SCALE_LIMITS["exams"]),
            )

            for course_id in exam_course_ids:
                course = course_map.get(course_id)
                reg_count = len(course_enrollment[course_id])
                if course and reg_count > 0:
                    exams.append(
                        Exam(
                            course_id=course.id,
                            session_id=active_session.id,
                            duration_minutes=course.exam_duration_minutes,
                            expected_students=reg_count,
                            status="pending",
                            is_practical=course.is_practical or False,
                            morning_only=course.morning_only,
                        )
                    )

            session.add_all(exams)
            self.seeded_data["exams"] = len(exams)
            logger.info(
                f"  ✓ Seeded {len(registrations)} registrations and {len(exams)} exams."
            )

    async def _seed_exam_relations(self):
        """Seed exam_departments and prerequisites."""
        async with db_manager.get_db_transaction() as session:
            logger.info(
                "  🔗 Seeding exam relations (departments, rooms, prerequisites)..."
            )
            exams_q = await session.execute(
                select(Exam).options(
                    selectinload(Exam.course), selectinload(Exam.prerequisites)
                )
            )
            exams = exams_q.scalars().all()
            if not exams:
                return

            exam_depts, prereqs_count = [], 0
            dept_level_exams = defaultdict(list)
            for exam in exams:
                dept_level_exams[
                    (exam.course.department_id, exam.course.course_level)
                ].append(exam)

            for exam in exams:
                exam_depts.append(
                    ExamDepartment(
                        exam_id=exam.id, department_id=exam.course.department_id
                    )
                )
                if (
                    prereqs_count < SCALE_LIMITS["exam_prerequisites"]
                    and exam.course.course_level > 100
                ):
                    potential = dept_level_exams.get(
                        (exam.course.department_id, exam.course.course_level - 100), []
                    )
                    if potential:
                        prereq_exam = random.choice(potential)
                        if prereq_exam.id != exam.id and prereq_exam.id not in {
                            p.id for p in exam.prerequisites
                        }:
                            exam.prerequisites.append(prereq_exam)
                            prereqs_count += 1

            session.add_all(exam_depts)
            self.seeded_data["exam_departments"] = len(exam_depts)
            self.seeded_data["exam_prerequisites_association"] = prereqs_count
            logger.info(
                f"  ✓ Seeded {len(exam_depts)} exam depts and {prereqs_count} prereqs."
            )

    async def _seed_timetable_jobs_and_versions(self):
        """Seed timetable jobs and versions."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  ⏳ Seeding timetable jobs and versions...")
            sessions_list = (
                (await session.execute(select(AcademicSession))).scalars().all()
            )
            configs = (
                (await session.execute(select(SystemConfiguration))).scalars().all()
            )

            # Make sure admin user exists for 'initiated_by'
            admin_user_result = await session.execute(
                select(User).where(User.email == "admin@baze.edu.ng")
            )
            admin_user = admin_user_result.scalars().first()

            if not all([sessions_list, configs, admin_user]):
                logger.warning(
                    "Skipping timetable jobs/versions due to missing sessions, configs, or admin user."
                )
                return

            jobs, versions = [], []
            for _ in range(SCALE_LIMITS["timetable_jobs"]):
                assert admin_user
                job = TimetableJob(
                    session_id=random.choice(sessions_list).id,
                    configuration_id=random.choice(configs).id,
                    initiated_by=admin_user.id,
                    status=random.choice(["completed", "failed", "running"]),
                    progress_percentage=random.randint(0, 100),
                )
                session.add(job)
                await session.flush()
                jobs.append(job)

                for i in range(random.randint(1, 3)):
                    versions.append(
                        TimetableVersion(
                            job_id=job.id,
                            version_number=i + 1,
                            version_type="primary",
                            is_active=(i == 0),
                            is_published=random.choice([True, False]),
                        )
                    )

            session.add_all(versions)
            self.seeded_data["timetable_jobs"] = len(jobs)
            self.seeded_data["timetable_versions"] = len(versions)
            logger.info(f"  ✓ Seeded {len(jobs)} jobs and {len(versions)} versions.")

    async def _seed_timetable_assignments_and_invigilators(self):
        """Seed timetable assignments and exam invigilators."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  ✍️ Seeding timetable assignments and invigilators...")
            versions_q = await session.execute(
                select(TimetableVersion).options(
                    selectinload(TimetableVersion.job)
                    .selectinload(TimetableJob.session)
                    .selectinload(AcademicSession.timeslot_template)
                    .selectinload(TimeSlotTemplate.periods)
                )
            )
            versions = versions_q.scalars().all()
            rooms = (await session.execute(select(Room))).scalars().all()
            exams = (await session.execute(select(Exam))).scalars().all()
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
                return

            assignments, invigilators = [], []
            for version in versions:
                if not (
                    version.job
                    and version.job.session
                    and version.job.session.timeslot_template
                ):
                    continue

                start, end = (
                    version.job.session.start_date,
                    version.job.session.end_date,
                )
                exam_dates = [
                    start + timedelta(days=i)
                    for i in range((end - start).days + 1)
                    if (start + timedelta(days=i)).weekday() < 5
                ]
                session_exams = [
                    e for e in exams if e.session_id == version.job.session_id
                ]
                periods = version.job.session.timeslot_template.periods

                for exam in random.sample(
                    session_exams, min(len(session_exams), SCALE_LIMITS["exams"] // 2)
                ):
                    if not exam_dates or not periods:
                        continue

                    assigned_room = random.choice(rooms)
                    assign = TimetableAssignment(
                        exam_id=exam.id,
                        room_id=assigned_room.id,
                        version_id=version.id,
                        exam_date=random.choice(exam_dates),
                        timeslot_template_period_id=random.choice(periods).id,
                        student_count=exam.expected_students,
                        allocated_capacity=assigned_room.exam_capacity,
                        is_primary=True,
                        is_confirmed=True,
                    )
                    session.add(assign)
                    await session.flush()
                    assignments.append(assign)

                    num_invigilators = max(1, math.ceil(exam.expected_students / 50))
                    for i, inv_staff in enumerate(
                        random.sample(staff, min(num_invigilators, len(staff)))
                    ):
                        invigilators.append(
                            ExamInvigilator(
                                timetable_assignment_id=assign.id,
                                staff_id=inv_staff.id,
                                role="lead-invigilator" if i == 0 else "invigilator",
                            )
                        )

            session.add_all(invigilators)
            self.seeded_data["timetable_assignments"] = len(assignments)
            self.seeded_data["exam_invigilators"] = len(invigilators)
            logger.info(
                f"  ✓ Seeded {len(assignments)} assignments and {len(invigilators)} invigilators."
            )

    async def _seed_hitl_entities(self):
        """Seed Human-in-the-Loop entities like scenarios."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  🔒 Seeding HITL scenarios...")
            versions = (await session.execute(select(TimetableVersion))).scalars().all()
            users = (await session.execute(select(User))).scalars().all()

            if not versions or not users:
                return

            scenarios = []
            for i in range(SCALE_LIMITS["timetable_scenarios"]):
                scenarios.append(
                    TimetableScenario(
                        parent_version_id=random.choice(versions).id,
                        name=f"What-if Scenario {i+1}",
                        description=fake.sentence(),
                        created_by=random.choice(users).id,
                    )
                )
            session.add_all(scenarios)

            self.seeded_data["timetable_scenarios"] = len(scenarios)
            self.seeded_data["timetable_locks"] = 0
            logger.info(f"  ✓ Seeded {len(scenarios)} scenarios. (Skipped locks)")

    async def _seed_timetable_edits(self):
        """Seed timetable edits."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  ✏️ Seeding timetable edits...")
            assignments = (
                (await session.execute(select(TimetableAssignment))).scalars().all()
            )
            users = (await session.execute(select(User))).scalars().all()
            if not assignments or not users:
                return

            edits = []
            for assign in random.sample(
                assignments, min(len(assignments), SCALE_LIMITS["timetable_edits"])
            ):
                edits.append(
                    TimetableEdit(
                        version_id=assign.version_id,
                        exam_id=assign.exam_id,
                        edited_by=random.choice(users).id,
                        edit_type=random.choice(["reschedule", "room_change"]),
                        reason="Administrative adjustment",
                        validation_status=random.choice(["approved", "pending"]),
                        old_values={
                            "date": str(assign.exam_date),
                            "period_id": str(assign.timeslot_template_period_id),
                        },
                        new_values={"date": str(assign.exam_date + timedelta(days=1))},
                    )
                )
            session.add_all(edits)
            self.seeded_data["timetable_edits"] = len(edits)
            logger.info(f"  ✓ Seeded {len(edits)} timetable edits.")

    async def _seed_file_uploads(self):
        """Seed file upload sessions and files."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  📤 Seeding file uploads...")
            users = (await session.execute(select(User))).scalars().all()
            if not users:
                return

            upload_sessions, uploaded_files = [], []
            for upload_type in ["students", "courses", "staff", "exams"]:
                if len(upload_sessions) >= SCALE_LIMITS["file_upload_sessions"]:
                    break
                upload_session = FileUploadSession(
                    upload_type=upload_type,
                    uploaded_by=random.choice(users).id,
                    status=random.choice(["completed", "failed"]),
                    total_records=random.randint(50, 200),
                )
                session.add(upload_session)
                await session.flush()
                upload_sessions.append(upload_session)
                uploaded_files.append(
                    UploadedFile(
                        upload_session_id=upload_session.id,
                        file_name=f"{upload_type}.csv",
                        file_path=f"/uploads/{upload_type}.csv",
                        file_size=random.randint(1024, 10240),
                        file_type="csv",
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
                return

            events, notifications = [], []
            for _ in range(SCALE_LIMITS["system_events"]):
                event = SystemEvent(
                    title=fake.sentence(nb_words=4),
                    message=fake.paragraph(nb_sentences=2),
                    event_type=random.choice(
                        ["info", "warning", "error", "job_status"]
                    ),
                )
                session.add(event)
                await session.flush()
                events.append(event)

                for user in random.sample(users, min(5, len(users))):
                    if len(notifications) < SCALE_LIMITS["user_notifications"]:
                        notifications.append(
                            UserNotification(
                                user_id=user.id,
                                event_id=event.id,
                                is_read=random.choice([True, False]),
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
            scenarios = (
                (await session.execute(select(TimetableScenario))).scalars().all()
            )
            if not users:
                return

            logs = [
                AuditLog(
                    user_id=random.choice(users).id,
                    action=random.choice(["login", "create", "update", "delete"]),
                    entity_type=random.choice(["exam", "student", "timetable"]),
                    ip_address=fake.ipv4(),
                    scenario_id=(
                        random.choice(scenarios).id
                        if scenarios and random.random() < 0.2
                        else None
                    ),
                )
                for _ in range(SCALE_LIMITS["audit_logs"])
            ]
            session.add_all(logs)
            self.seeded_data["audit_logs"] = len(logs)
            logger.info(f"  ✓ Seeded {len(logs)} audit logs.")

    async def _seed_feedback_and_reporting_entities(self):
        """Seed feedback and reporting tables."""
        async with db_manager.get_db_transaction() as session:
            logger.info("  📈 Seeding feedback and reporting entities...")
            staff = (await session.execute(select(Staff))).scalars().all()
            students = (await session.execute(select(Student))).scalars().all()
            assignments = (
                (await session.execute(select(TimetableAssignment))).scalars().all()
            )
            exams = (await session.execute(select(Exam))).scalars().all()
            versions = (await session.execute(select(TimetableVersion))).scalars().all()

            change_reqs, conflict_reps, timetable_conflicts = [], [], []

            # Ensure every staff member has one assignment change request.
            if staff and assignments:
                for staff_member in staff:
                    change_reqs.append(
                        AssignmentChangeRequest(
                            staff_id=staff_member.id,
                            timetable_assignment_id=random.choice(assignments).id,
                            reason=random.choice(
                                [
                                    "Personal emergency",
                                    "Scheduling clash",
                                    "Medical appointment",
                                ]
                            ),
                            description=fake.sentence(),
                            status=random.choice(["pending", "approved", "denied"]),
                        )
                    )

            # Ensure every student has one conflict report.
            if students and exams:
                for student in students:
                    conflict_reps.append(
                        ConflictReport(
                            student_id=student.id,
                            exam_id=random.choice(exams).id,
                            description="I have a documented medical appointment.",
                            status=random.choice(["pending", "resolved"]),
                        )
                    )

            if versions and exams and students:
                # Limit the number of timetable conflicts to avoid excessive data
                num_conflicts = min(
                    SCALE_LIMITS["timetable_conflicts"], len(students) * 2
                )
                for _ in range(num_conflicts):
                    timetable_conflicts.append(
                        TimetableConflict(
                            version_id=random.choice(versions).id,
                            type=random.choice(["hard", "soft"]),
                            severity=random.choice(["high", "medium", "low"]),
                            message="Student exam overlap detected.",
                            details={
                                "student_id": str(random.choice(students).id),
                                "conflicting_exams": [
                                    str(e.id) for e in random.sample(exams, 2)
                                ],
                            },
                            is_resolved=random.choice([True, False]),
                        )
                    )

            session.add_all(change_reqs + conflict_reps + timetable_conflicts)
            self.seeded_data["assignment_change_requests"] = len(change_reqs)
            self.seeded_data["conflict_reports"] = len(conflict_reps)
            self.seeded_data["timetable_conflicts"] = len(timetable_conflicts)
            logger.info(
                f"  ✓ Seeded {len(change_reqs)} change requests, {len(conflict_reps)} reports, and {len(timetable_conflicts)} conflicts."
            )

    async def _log_data_complexity_analysis(self):
        """Fetches final data counts and calculates complexity metrics."""
        logger.info("\n" + "=" * 60 + "\n🔬 DATA COMPLEXITY ANALYSIS\n" + "=" * 60)
        async with db_manager.get_session() as session:
            try:
                num_students = self.seeded_data.get("students", 0)
                num_exams = self.seeded_data.get("exams", 0)
                num_registrations = self.seeded_data.get("course_registrations", 0)
                total_exam_seats = (
                    await session.scalar(select(func.sum(Exam.expected_students))) or 0
                )
                total_room_capacity = (
                    await session.scalar(select(func.sum(Room.exam_capacity))) or 0
                )
                num_invigilators = (
                    await session.scalar(
                        select(func.count(Staff.id)).where(Staff.can_invigilate == True)
                    )
                    or 0
                )

                avg_courses_per_student = (
                    num_registrations / num_students if num_students > 0 else 0
                )
                avg_students_per_exam = (
                    total_exam_seats / num_exams if num_exams > 0 else 0
                )
                room_pressure = (
                    total_exam_seats / total_room_capacity
                    if total_room_capacity > 0
                    else float("inf")
                )

                logger.info(f"{'Metric':<35}: {'Value':>20}")
                logger.info("-" * 60)
                logger.info(
                    f"{'Average courses per student':<35}: {avg_courses_per_student:20.2f}"
                )
                logger.info(
                    f"{'Average students per exam':<35}: {avg_students_per_exam:20.2f}"
                )
                logger.info(
                    f"{'Total student exam seats':<35}: {int(total_exam_seats):>20,}"
                )
                logger.info(
                    f"{'Total available exam capacity':<35}: {int(total_room_capacity):>20,}"
                )
                logger.info(f"{'Room Pressure Ratio':<35}: {room_pressure:20.2f}")
                logger.info(f"{'Available Invigilators':<35}: {num_invigilators:>20,}")
                logger.info("-" * 60)
            except Exception as e:
                logger.error(f"Could not perform data complexity analysis: {e}")

    async def print_summary(self, dry_run=False):
        """Prints a summary of intended or actual data counts."""
        logger.info("\n" + "=" * 60 + "\n📊 SEEDING SUMMARY\n" + "=" * 60)
        data = SCALE_LIMITS if dry_run else self.seeded_data
        for entity in sorted(data.keys()):
            logger.info(
                f"{entity.replace('_', ' ').title():<35}: {data.get(entity, 0):>{10},}"
            )
        logger.info("=" * 60)


async def main():
    """Main entry point to run the seeder from the command line."""
    parser = argparse.ArgumentParser(
        description="Seed the database with comprehensive fake data.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--database-url", help="Database connection URL.")
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Drop all existing data before seeding.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing to the DB.",
    )
    parser.add_argument(
        "--seed", type=int, help="A seed for the random number generator."
    )
    parser.add_argument(
        "--magnitude",
        type=int,
        choices=[1, 2, 3, 4, 5],
        default=3,
        help="Data size magnitude.",
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
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⏹️ Seeding interrupted by user.")
        sys.exit(1)
