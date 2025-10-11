import asyncio
import argparse
import logging
import math
import os
import random
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
from uuid import uuid4

from faker import Faker
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

try:
    # Adjust path to import from the app directory
    BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))

    from app.core.security import hash_password
    from app.database import db_manager, init_db
    from app.models import (
        AcademicSession,
        AssignmentChangeRequest,
        AuditLog,
        Building,
        ConfigurationRuleSetting,
        ConflictReport,
        ConstraintConfiguration,
        ConstraintParameter,
        ConstraintRule,
        Course,
        CourseDepartment,  # Added
        CourseFaculty,  # Added
        CourseInstructor,
        CourseRegistration,
        DataSeedingSession,
        Department,
        Exam,
        ExamDepartment,
        ExamInvigilator,
        Faculty,
        FileUpload,
        FileUploadSession,
        Programme,
        Room,
        RoomDepartment,  # Added
        RoomType,
        SessionTemplate,
        Staff,
        StaffUnavailability,
        Student,
        StudentEnrollment,
        SystemConfiguration,
        SystemEvent,
        TimeSlotTemplate,
        TimeSlotTemplatePeriod,
        TimetableAssignment,
        TimetableConflict,
        TimetableEdit,
        TimetableJob,
        TimetableJobExamDay,
        TimetableLock,
        TimetableScenario,
        TimetableVersion,
        UploadedFile,
        User,
        UserFilterPreset,
        UserNotification,
        VersionDependency,
        VersionMetadata,
    )
    from app.models.academic import SlotGenerationModeEnum

except ImportError as e:
    print(
        f"Error: Could not import project modules. Ensure this script is placed correctly."
    )
    print(f"Details: {e}")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)
fake = Faker()
SCALE_LIMITS = {}


class ComprehensiveFakeSeeder:
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
        self.generated_emails: Set[str] = set()
        self.generated_matrics: Set[str] = set()
        self.generated_staff_numbers: Set[str] = set()
        self.generated_course_codes: Set[str] = set()
        self.generated_room_codes: Set[str] = set()
        self.demo_users: Dict[str, User] = {}
        self._set_magnitude_level(self.magnitude)
        self._initialize_rng()

    def _initialize_rng(self):
        if self.seed is not None:
            logger.info(f"🌱 Initializing RNG with seed: {self.seed}")
            random.seed(self.seed)
            Faker.seed(self.seed)

    def _set_magnitude_level(self, level: int):
        MAGNITUDE_LEVELS = {
            0: {
                "faculties": 1,
                "departments": 1,
                "programmes": 1,
                "courses": 2,
                "students": 50,
                "staff": 3,
                "buildings": 1,
                "rooms": 2,
                "academic_sessions": 1,
            },
            1: {
                "faculties": 3,
                "departments": 8,
                "programmes": 15,
                "courses": 80,
                "students": 100,
                "staff": 5,  # MODIFIED: Adjusted for a ~20:1 student-staff ratio
                "buildings": 4,
                "rooms": 40,
                "academic_sessions": 2,
            },
            2: {
                "faculties": 4,
                "departments": 15,
                "programmes": 30,
                "courses": 200,
                "students": 500,
                "staff": 25,  # MODIFIED: Adjusted for a ~20:1 student-staff ratio
                "buildings": 6,
                "rooms": 80,
                "academic_sessions": 2,
            },
            3: {
                "faculties": 6,
                "departments": 25,
                "programmes": 50,
                "courses": 500,
                "students": 2000,
                "staff": 100,  # MODIFIED: Adjusted for a ~20:1 student-staff ratio
                "buildings": 10,
                "rooms": 150,
                "academic_sessions": 3,
            },
            4: {
                "faculties": 8,
                "departments": 35,
                "programmes": 80,
                "courses": 800,
                "students": 5000,
                "staff": 250,  # MODIFIED: Adjusted for a ~20:1 student-staff ratio
                "buildings": 12,
                "rooms": 250,
                "academic_sessions": 3,
            },
            5: {
                "faculties": 10,
                "departments": 50,
                "programmes": 120,
                "courses": 1200,
                "students": 10000,
                "staff": 500,  # MODIFIED: Adjusted for a ~20:1 student-staff ratio
                "buildings": 15,
                "rooms": 400,
                "academic_sessions": 4,
            },
        }
        base_counts = MAGNITUDE_LEVELS[level]
        base_counts["exams"] = int(
            base_counts["courses"] * 0.8
        )  # Exams are based on courses

        global SCALE_LIMITS
        SCALE_LIMITS = {
            **base_counts,
            "users": base_counts["students"] + base_counts["staff"] + 10,
            "timeslot_templates": 3,
            "timeslot_template_periods": 3 * 3,
            "student_enrollments": base_counts["students"]
            * base_counts["academic_sessions"],
            "course_registrations": int(base_counts["students"] * 7.5),
            "course_instructors": int(base_counts["courses"] * 1.5),
            "exam_departments": int(base_counts["exams"] * 1.2),
            "exam_prerequisites": int(base_counts["exams"] * 0.1),
            "staff_unavailability": int(base_counts["staff"] * 2),
            "timetable_jobs": 5,
            "timetable_versions": 10,
            "version_metadata": 10,
            "version_dependencies": 5,
            "timetable_assignments": int(
                base_counts["exams"] * 1.2
            ),  # Accounts for exam splitting
            "exam_invigilators": int(base_counts["exams"] * 2.5),
            "timetable_edits": 20,
            "audit_logs": 200,
            "constraint_rules": 8,
            "constraint_parameters": 15,
            "constraint_configurations": 3,
            "configuration_rule_settings": 3 * 8,
            "system_configurations": 3,
            "system_events": 20,
            "user_notifications": 40,
            "user_filter_presets": 10,
            "data_seeding_sessions": 2,
            "file_uploads": 5,
            "file_upload_sessions": 5,
            "uploaded_files": 8,
            "session_templates": 3,
            "timetable_scenarios": 3,
            "timetable_locks": 15,
            "timetable_conflicts": 40,
            "assignment_change_requests": 20,
            "conflict_reports": 30,
        }
        logger.info(
            f"Seeding magnitude set to level {level} (students: {SCALE_LIMITS['students']})"
        )

    async def run(self, drop_existing: bool = False):
        logger.info("🚀 Starting comprehensive fake data seeding...")
        try:
            await init_db(database_url=self.database_url, create_tables=False)
            logger.info("✅ Database connection established.")

            if drop_existing:
                await self._clear_all_data()

            # The order of these phases is crucial for maintaining data integrity
            await self._seed_phase_1_academic_and_physical_structure()
            await self._seed_phase_2_templates_and_config()
            await self._seed_phase_3_courses_people_and_users()
            await self._seed_phase_4_enrollments_and_exams()
            await self._seed_phase_5_timetabling_and_hitl()
            await self._seed_phase_6_system_and_logging()

            logger.info("🎉 Comprehensive fake data seeding completed successfully!")
            await self.print_summary()

        except Exception as e:
            logger.error(
                f"💥 An unexpected error occurred during seeding: {e}", exc_info=True
            )
            raise

    async def _clear_all_data(self):
        logger.warning("🧹 Clearing all existing data from database...")
        async with db_manager.get_db_transaction() as session:
            # CORRECTED: A dependency-aware order for truncation.
            # Children are truncated before parents.
            tables_to_clear = [
                "audit_logs",
                "user_notifications",
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
                "user_filter_presets",
                "file_uploads",
                "timetable_job_exam_days",
                "timetable_versions",  # Depends on jobs, scenarios
                "system_events",  # Depends on users
                "timetable_jobs",  # Depends on sessions, users, scenarios
                "timetable_scenarios",  # Depends on users
                "file_upload_sessions",  # Depends on users, sessions
                "data_seeding_sessions",  # Depends on users, sessions
                "exam_prerequisites_association",  # Depends on exams
                "exam_departments",  # Depends on exams, departments
                "configuration_rule_settings",  # Depends on configurations, rules
                "system_configurations",  # Depends on configurations, users
                "constraint_configurations",  # Depends on users
                "constraint_parameters",  # Depends on rules
                "constraint_rules",
                "course_instructors",  # Depends on courses, staff
                "course_faculties",  # Depends on courses, faculties
                "course_departments",  # Depends on courses, departments
                "course_registrations",  # Depends on students, courses, sessions
                "student_enrollments",  # Depends on students, sessions
                "staff_unavailability",  # Depends on staff, sessions
                "exams",  # Depends on courses, sessions
                "courses",
                "staff",  # Depends on departments, users
                "students",  # Depends on programmes, users
                "programmes",  # Depends on departments
                "room_departments",  # Depends on rooms, departments
                "departments",  # Depends on faculties
                "faculties",
                "rooms",  # Depends on buildings, room_types
                "room_types",
                "buildings",
                "timeslot_template_periods",  # Depends on timeslot_templates
                "timeslot_templates",
                "session_templates",  # Depends on academic_sessions
                "academic_sessions",
                "users",
            ]
            for table in tables_to_clear:
                try:
                    # This command remains the same
                    await session.execute(
                        text(
                            f'TRUNCATE TABLE exam_system."{table}" RESTART IDENTITY CASCADE'
                        )
                    )
                    logger.info(f"  - Cleared table: {table}")
                except Exception as e:
                    logger.warning(f"  - Could not clear table {table}: {e}")
        logger.info("🧹 Database cleared.")

    # --- Seeding Phases (Reordered for new schema) ---
    async def _seed_phase_1_academic_and_physical_structure(self):
        logger.info("Phase 1: Seeding Academic and Physical Structure...")
        await self._seed_faculties_departments_programmes()
        await self._seed_infrastructure()

    async def _seed_phase_2_templates_and_config(self):
        logger.info("Phase 2: Seeding Templates, Constraints, and Sessions...")
        await self._seed_timeslot_templates()
        await self._seed_session_templates()
        await self._seed_constraints_and_config()
        await self._seed_academic_sessions()

    async def _seed_phase_3_courses_people_and_users(self):
        logger.info("Phase 3: Seeding Courses, People, and Users...")
        await self._seed_courses()
        await self._seed_demo_user_accounts()
        await self._seed_students_and_create_users()
        await self._seed_staff_and_create_users()

    async def _seed_phase_4_enrollments_and_exams(self):
        logger.info("Phase 4: Seeding Enrollments, Exams, and Staffing...")
        await self._seed_student_enrollments()
        await self._seed_course_registrations_and_exams()
        await self._seed_exam_details()
        await self._seed_course_instructors()
        await self._seed_staff_unavailability()

    async def _seed_phase_5_timetabling_and_hitl(self):
        logger.info("Phase 5: Seeding Timetabling, Versioning, and HITL...")
        await self._seed_timetable_scenarios_jobs_and_versions()
        await self._seed_versioning_details()
        await self._seed_timetable_assignments_and_invigilators()
        await self._seed_timetable_support_entities()

    async def _seed_phase_6_system_and_logging(self):
        logger.info("Phase 6: Seeding System, Logging, and Feedback...")
        await self._seed_system_events_and_notifications()
        await self._seed_audit_logs()
        await self._seed_feedback_and_reporting_entities()
        await self._seed_file_upload_entities()
        await self._seed_user_presets()

    # --- Seeding Methods (in logical execution order) ---

    async def _generate_unique_email(self, first, last, suffix="baze.edu.ng"):
        email = f"{first.lower()}.{last.lower()}@{suffix}".replace(" ", "")
        c = 1
        while email in self.generated_emails:
            email = f"{first.lower()}.{last.lower()}{c}@{suffix}".replace(" ", "")
            c += 1
        self.generated_emails.add(email)
        return email

    async def _seed_faculties_departments_programmes(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding academic structure...")
            faculty_data = {
                "ENG": "Engineering",
                "SCI": "Science",
                "MGT": "Management",
                "LAW": "Law",
                "IT": "Computing & IT",
                "ENV": "Environmental Science",
                "ART": "Arts & Humanities",
                "MED": "Medical Sciences",
                "EDU": "Education",
                "AGR": "Agriculture",
            }
            faculties = [
                Faculty(code=c, name=f"Faculty of {n}", is_active=True)
                for c, n in list(faculty_data.items())[: SCALE_LIMITS["faculties"]]
            ]
            session.add_all(faculties)
            await session.flush()
            self.seeded_data["faculties"] = len(faculties)

            dept_data = {
                "ENG": ["CPE", "MCE", "CVE"],
                "SCI": ["CSC", "PHY", "CHM"],
                "MGT": ["ACC", "BUS", "MKT"],
                "IT": ["IFT", "CYS", "SWE"],
                "LAW": ["PUB", "PRV"],
            }
            depts, progs = [], []
            for fac in faculties:
                for dept_code in dept_data.get(fac.code, []):
                    if len(depts) >= SCALE_LIMITS["departments"]:
                        break
                    dept = Department(
                        code=dept_code,
                        name=f"Dept. of {dept_code}",
                        faculty_id=fac.id,
                        is_active=True,
                    )
                    depts.append(dept)
                    session.add(dept)
                    await session.flush()
                    if len(progs) < SCALE_LIMITS["programmes"]:
                        progs.append(
                            Programme(
                                code=f"B.{dept_code}",
                                name=f"B.Sc {dept_code}",
                                department_id=dept.id,
                                duration_years=4,
                                degree_type="undergraduate",
                                is_active=True,
                            )
                        )
            session.add_all(progs)
            self.seeded_data["departments"] = len(depts)
            self.seeded_data["programmes"] = len(progs)

    async def _seed_infrastructure(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding infrastructure with associations...")

            # Get faculties and departments created in the previous step
            faculties = (await session.execute(select(Faculty))).scalars().all()
            departments = (await session.execute(select(Department))).scalars().all()

            building_codes = [
                "A",
                "B",
                "C",
                "D",
                "E",
                "F",
                "G",
                "H",
                "J",
                "K",
                "L",
                "M",
                "ENG",
                "LAW",
                "MED",
            ]
            buildings = []
            for code in building_codes[: SCALE_LIMITS["buildings"]]:
                # Edge Case: ~20% of buildings are multi-purpose/not tied to a faculty
                faculty_id = None
                if faculties and random.random() < 0.8:
                    faculty_id = random.choice(faculties).id

                buildings.append(
                    Building(
                        code=code,
                        name=(
                            f"{code} Block"
                            if faculty_id
                            else f"General Purpose Hall {code}"
                        ),
                        is_active=True,
                        faculty_id=faculty_id,
                    )
                )
            session.add_all(buildings)
            await session.flush()
            self.seeded_data["buildings"] = len(buildings)

            room_types = [
                RoomType(name=n, description=f"{n}", is_active=True)
                for n in [
                    "Lecture Hall",
                    "Classroom",
                    "Lab",
                    "Auditorium",
                    "Seminar Room",
                ]
            ]
            session.add_all(room_types)
            await session.flush()
            self.seeded_data["room_types"] = len(room_types)

            room_type_population = [rt for rt in room_types]
            room_type_weights = {
                "Classroom": 0.50,
                "Lecture Hall": 0.25,
                "Lab": 0.10,
                "Seminar Room": 0.10,
                "Auditorium": 0.05,
            }
            weights = [
                room_type_weights.get(rt.name, 0.1) for rt in room_type_population
            ]

            rooms = []
            for _ in range(SCALE_LIMITS["rooms"]):
                b = random.choice(buildings)
                rt = random.choices(room_type_population, weights=weights, k=1)[0]
                capacity_map = {
                    "Auditorium": (200, 500),
                    "Lecture Hall": (80, 200),
                    "Classroom": (30, 80),
                    "Seminar Room": (15, 40),
                    "Lab": (20, 50),
                }
                cap = random.randint(*capacity_map.get(rt.name, (20, 60)))
                exam_cap = int(cap * random.uniform(0.4, 0.6))
                while True:
                    code = f"{b.code}{random.randint(101, 599)}"
                    if code not in self.generated_room_codes:
                        self.generated_room_codes.add(code)
                        break
                rooms.append(
                    Room(
                        code=code,
                        name=f"Room {code}",
                        building_id=b.id,
                        room_type_id=rt.id,
                        capacity=cap,
                        exam_capacity=exam_cap,
                        has_projector=random.choice([True, False]),
                        has_computers=(rt.name == "Lab"),
                        is_active=True,
                        has_ac=True,
                        max_inv_per_room=random.randint(2, 5),
                        overbookable=False,
                    )
                )
            session.add_all(rooms)
            await session.flush()
            self.seeded_data["rooms"] = len(rooms)

            # Seed room-to-department associations
            if rooms and departments:
                room_depts = []
                for room in rooms:
                    if random.random() < 0.9:  # 90% of rooms are associated
                        num_depts = random.choices([1, 2], weights=[0.9, 0.1], k=1)[0]
                        assigned_depts = random.sample(
                            departments, min(num_depts, len(departments))
                        )
                        for dept in assigned_depts:
                            room_depts.append(
                                RoomDepartment(room_id=room.id, department_id=dept.id)
                            )
                session.add_all(room_depts)
                self.seeded_data["room_departments"] = len(room_depts)

    async def _seed_timeslot_templates(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding timeslot templates...")
            t1 = TimeSlotTemplate(
                name="Standard 3-Slot Day",
                description="Morning, Afternoon, Evening slots",
            )
            session.add(t1)
            await session.flush()
            periods = [
                TimeSlotTemplatePeriod(
                    timeslot_template_id=t1.id,
                    period_name="Morning",
                    start_time=time(9, 0),
                    end_time=time(12, 0),
                ),
                TimeSlotTemplatePeriod(
                    timeslot_template_id=t1.id,
                    period_name="Afternoon",
                    start_time=time(12, 0),
                    end_time=time(15, 0),
                ),
                TimeSlotTemplatePeriod(
                    timeslot_template_id=t1.id,
                    period_name="Evening",
                    start_time=time(15, 0),
                    end_time=time(18, 0),
                ),
            ]
            session.add_all(periods)
            self.seeded_data["timeslot_templates"] = 1
            self.seeded_data["timeslot_template_periods"] = len(periods)

    async def _seed_session_templates(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding session templates...")
            templates = [
                SessionTemplate(name=n, description=f"Template for {n}", is_active=True)
                for n in [
                    "Standard Academic Year",
                    "Summer Session",
                    "Executive Programme",
                ]
            ][: SCALE_LIMITS["session_templates"]]
            session.add_all(templates)
            self.seeded_data["session_templates"] = len(templates)

    async def _seed_constraints_and_config(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding constraints schema with realistic weights...")

            rules_data = [
                (
                    "UNIFIED_STUDENT_CONFLICT",
                    "Unified Student Conflict",
                    "hard",
                    "Student",
                ),
                (
                    "MAX_EXAMS_PER_STUDENT_PER_DAY",
                    "Max Exams Per Student Per Day",
                    "soft",
                    "Student",
                ),
                ("ROOM_CAPACITY_HARD", "Room Capacity", "hard", "Room"),
                (
                    "ROOM_SEQUENTIAL_USE",
                    "Room Sequential Use (Flexible Mode)",
                    "hard",
                    "Room",
                ),
                ("MINIMUM_GAP", "Minimum Gap Between Exams", "soft", "Student"),
                ("OVERBOOKING_PENALTY", "Overbooking Penalty", "soft", "Room"),
                ("PREFERENCE_SLOTS", "Exam Slot Preferences", "soft", "Exam"),
                (
                    "INVIGILATOR_LOAD_BALANCE",
                    "Invigilator Workload Balance",
                    "soft",
                    "Invigilator",
                ),
                (
                    "INSTRUCTOR_CONFLICT",
                    "Instructor Self-Invigilation Conflict",
                    "soft",
                    "Invigilator",
                ),
                (
                    "CARRYOVER_STUDENT_CONFLICT",
                    "Carryover Student Conflict Penalty",
                    "soft",
                    "Student",
                ),
                (
                    "DAILY_WORKLOAD_BALANCE",
                    "Daily Exam Workload Balance",
                    "soft",
                    "Exam",
                ),
                (
                    "ROOM_DURATION_HOMOGENEITY",
                    "Room Duration Homogeneity (Flexible Mode)",
                    "soft",
                    "Room",
                ),
                ("ROOM_FIT_PENALTY", "Room Fit Penalty", "soft", "Room"),
            ]
            rules = [
                ConstraintRule(code=c, name=n, type=t, category=cat)
                for c, n, t, cat in rules_data
            ]
            session.add_all(rules)
            await session.flush()
            self.seeded_data["constraint_rules"] = len(rules)
            logger.info(f"  - Created {len(rules)} ConstraintRule records.")

            params_data = [
                (
                    "MAX_EXAMS_PER_STUDENT_PER_DAY",
                    "max_exams_per_day",
                    "integer",
                    "2",
                    "Max exams a student can have per day.",
                ),
                (
                    "MINIMUM_GAP",
                    "min_gap_slots",
                    "integer",
                    "1",
                    "Min empty slots between a student's exams.",
                ),
                (
                    "CARRYOVER_STUDENT_CONFLICT",
                    "max_allowed_conflicts",
                    "integer",
                    "3",
                    "Threshold for carryover conflicts.",
                ),
            ]
            rule_map = {r.code: r for r in rules}
            params = [
                ConstraintParameter(
                    rule_id=rule_map[rc].id,
                    key=k,
                    data_type=dt,
                    default_value=dv,
                    description=d,
                )
                for rc, k, dt, dv, d in params_data
                if rc in rule_map
            ]
            session.add_all(params)
            self.seeded_data["constraint_parameters"] = len(params)
            logger.info(f"  - Created {len(params)} ConstraintParameter records.")

            admin_user = await session.scalar(select(User).where(User.role == "admin"))
            if not admin_user:
                admin_user = User(
                    email=await self._generate_unique_email("config", "admin"),
                    first_name="Config",
                    last_name="Admin",
                    is_active=True,
                    is_superuser=True,
                    role="admin",
                    password_hash=hash_password("admin"),
                )
                session.add(admin_user)
                await session.flush()

            configs = [
                ConstraintConfiguration(
                    name="Standard University Policy",
                    is_default=True,
                    created_by=admin_user.id,
                ),
                ConstraintConfiguration(
                    name="Strict No-Back-to-Back Policy",
                    is_default=False,
                    created_by=admin_user.id,
                ),
                ConstraintConfiguration(
                    name="Flexible Slot Mode Policy",
                    is_default=False,
                    created_by=admin_user.id,
                ),
            ]
            session.add_all(configs)
            await session.flush()
            self.seeded_data["constraint_configurations"] = len(configs)
            std_config, strict_config, flex_config = configs[0], configs[1], configs[2]

            realistic_weights = {
                "CARRYOVER_STUDENT_CONFLICT": 950.0,
                "MAX_EXAMS_PER_STUDENT_PER_DAY": 800.0,
                "MINIMUM_GAP": 250.0,
                "INSTRUCTOR_CONFLICT": 150.0,
                "PREFERENCE_SLOTS": 40.0,
                "INVIGILATOR_LOAD_BALANCE": 70.0,
                "DAILY_WORKLOAD_BALANCE": 60.0,
                "OVERBOOKING_PENALTY": 20.0,
                "ROOM_DURATION_HOMOGENEITY": 10.0,
                "ROOM_FIT_PENALTY": 1.0,
            }

            all_settings = []
            for rule in rules:
                default_weight = (
                    realistic_weights.get(rule.code, 1.0)
                    if rule.type == "soft"
                    else 1.0
                )
                all_settings.append(
                    ConfigurationRuleSetting(
                        configuration_id=std_config.id,
                        rule_id=rule.id,
                        is_enabled=True,
                        weight=default_weight,
                    )
                )
                strict_setting = ConfigurationRuleSetting(
                    configuration_id=strict_config.id,
                    rule_id=rule.id,
                    is_enabled=True,
                    weight=default_weight,
                )
                if rule.code == "MINIMUM_GAP":
                    strict_setting.weight = 500.0
                all_settings.append(strict_setting)
                flex_setting = ConfigurationRuleSetting(
                    configuration_id=flex_config.id,
                    rule_id=rule.id,
                    is_enabled=True,
                    weight=default_weight,
                )
                all_settings.append(flex_setting)
            session.add_all(all_settings)
            self.seeded_data["configuration_rule_settings"] = len(all_settings)
            logger.info(
                f"  - Created {len(all_settings)} ConfigurationRuleSetting records with realistic weights."
            )

            sys_configs = [
                SystemConfiguration(
                    name=f"{c.name} Profile",
                    constraint_config_id=c.id,
                    is_default=c.is_default,
                    created_by=admin_user.id,
                    solver_parameters={"time_limit_seconds": 300},
                )
                for c in configs
            ]
            session.add_all(sys_configs)
            self.seeded_data["system_configurations"] = len(sys_configs)
            logger.info(f"  - Created {len(sys_configs)} SystemConfiguration records.")

    async def _seed_academic_sessions(self):
        async with db_manager.get_db_transaction() as session:
            logger.info(
                "  - Seeding academic sessions with extended 3-week duration..."
            )
            template_ids = (
                (await session.execute(select(TimeSlotTemplate.id))).scalars().all()
            )
            if not template_ids:
                return

            sessions = []
            current_year = datetime.now().year
            for i in range(SCALE_LIMITS["academic_sessions"]):
                year = current_year - i
                start_date = date(year, 10, 15)
                # FIX: Extended duration from 14 to 21 days to make schedule less constrained
                end_date = start_date + timedelta(days=21)

                sessions.append(
                    AcademicSession(
                        name=f"{year}/{year+1} Session",
                        semester_system="semester",
                        start_date=start_date,
                        end_date=end_date,
                        is_active=(i == 0),
                        timeslot_template_id=random.choice(template_ids),
                        slot_generation_mode=random.choice(
                            list(SlotGenerationModeEnum)
                        ),
                    )
                )
            session.add_all(sessions)
            self.seeded_data["academic_sessions"] = len(sessions)

    async def _seed_courses(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding courses with associations...")
            departments = (await session.execute(select(Department))).scalars().all()
            faculties = (await session.execute(select(Faculty))).scalars().all()
            if not departments or not faculties:
                logger.warning(
                    "No departments or faculties found, skipping course seeding."
                )
                return

            courses = []
            for _ in range(SCALE_LIMITS["courses"]):
                while True:
                    code = f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))}{random.randint(101, 499)}"
                    if code not in self.generated_course_codes:
                        self.generated_course_codes.add(code)
                        break
                courses.append(
                    Course(
                        code=code,
                        title=fake.catch_phrase(),
                        credit_units=random.randint(1, 4),
                        course_level=random.choice([100, 200, 300, 400]),
                        is_active=True,
                        exam_duration_minutes=random.choice([60, 90, 120, 180]),
                        is_practical=random.random() < 0.1,
                    )
                )
            session.add_all(courses)
            await session.flush()
            self.seeded_data["courses"] = len(courses)

            # Seed associations for courses
            course_depts, course_facs = [], []
            for course in courses:
                rand_val = random.random()
                if rand_val < 0.8:  # 80% standard course, 1 department
                    dept = random.choice(departments)
                    course_depts.append(
                        CourseDepartment(course_id=course.id, department_id=dept.id)
                    )
                elif rand_val < 0.9:  # 10% cross-listed, 2-3 departments
                    num_depts = random.randint(2, 3)
                    depts = random.sample(departments, min(num_depts, len(departments)))
                    for dept in depts:
                        course_depts.append(
                            CourseDepartment(course_id=course.id, department_id=dept.id)
                        )
                elif rand_val < 0.95:  # 5% faculty-wide course
                    fac = random.choice(faculties)
                    course_facs.append(
                        CourseFaculty(course_id=course.id, faculty_id=fac.id)
                    )
                # 5% are general/university courses with no association

            session.add_all(course_depts)
            session.add_all(course_facs)
            self.seeded_data["course_departments"] = len(course_depts)
            self.seeded_data["course_faculties"] = len(course_facs)

    async def _seed_demo_user_accounts(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding demo user accounts...")
            pwd = hash_password("password")
            users_to_create = {
                "admin": ("Admin", "User", True, "admin"),
                "staff": ("Staff", "User", False, "staff"),
                "student": ("Student", "User", False, "student"),
            }
            for role, (first, last, is_super, role_name) in users_to_create.items():
                email = f"{role}@baze.edu.ng"
                user = await session.scalar(select(User).where(User.email == email))
                if not user:
                    user = User(
                        email=email,
                        first_name=first,
                        last_name=last,
                        password_hash=pwd,
                        is_active=True,
                        is_superuser=is_super,
                        role=role_name,
                    )
                    session.add(user)
                    self.demo_users[role] = user
                    self.seeded_data["users"] += 1
            await session.flush()
            for role in users_to_create:
                if role not in self.demo_users:
                    self.demo_users[role] = await session.scalar(
                        select(User).where(
                            User.role == role, User.email.like(f"{role}@%")
                        )
                    )

    async def _seed_students_and_create_users(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding students and ensuring user accounts...")
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
                return

            students_to_create = []
            pwd = hash_password("password123")
            for i in range(SCALE_LIMITS["students"]):
                first, last = fake.first_name(), fake.last_name()
                user = User(
                    email=await self._generate_unique_email(
                        first, last, "student.baze.edu.ng"
                    ),
                    first_name=first,
                    last_name=last,
                    password_hash=pwd,
                    is_active=True,
                    is_superuser=False,
                    role="student",
                )
                prog = random.choice(programmes)
                entry_year = datetime.now().year - random.randint(
                    0, prog.duration_years - 1
                )
                matric_num_counter = i
                while True:
                    matric = f"BU/{str(entry_year)[-2:]}/{prog.department.code}/{matric_num_counter+1:04d}"
                    if matric not in self.generated_matrics:
                        self.generated_matrics.add(matric)
                        break
                    matric_num_counter += 1
                student = Student(
                    user_id=user.id,
                    matric_number=matric,
                    first_name=first,
                    last_name=last,
                    entry_year=entry_year,
                    programme_id=prog.id,
                )
                students_to_create.append((user, student))

            session.add_all([u for u, s in students_to_create])
            await session.flush()
            session.add_all([s for u, s in students_to_create])

            self.seeded_data["students"] = len(students_to_create)
            self.seeded_data["users"] += len(students_to_create)

    async def _seed_staff_and_create_users(self):
        async with db_manager.get_db_transaction() as session:
            logger.info(
                "  - Seeding staff (academic and admin) and ensuring user accounts..."
            )
            dept_ids = (await session.execute(select(Department.id))).scalars().all()

            staff_to_create = []
            pwd = hash_password("password123")
            for i in range(SCALE_LIMITS["staff"]):
                first, last = fake.first_name(), fake.last_name()
                user = User(
                    email=await self._generate_unique_email(
                        first, last, "staff.baze.edu.ng"
                    ),
                    first_name=first,
                    last_name=last,
                    password_hash=pwd,
                    is_active=True,
                    is_superuser=False,
                    role="staff",
                )

                # Edge Case: ~10% of staff are administrative
                is_admin_staff = random.random() < 0.1
                dept_id = (
                    random.choice(dept_ids) if dept_ids and not is_admin_staff else None
                )
                staff_type = "administrative" if is_admin_staff else "academic"

                staff_num_counter = i
                while True:
                    staff_num = f"STF{1001+staff_num_counter}"
                    if staff_num not in self.generated_staff_numbers:
                        self.generated_staff_numbers.add(staff_num)
                        break
                    staff_num_counter += 1
                staff_member = Staff(
                    user_id=user.id,
                    staff_number=staff_num,
                    first_name=first,
                    last_name=last,
                    department_id=dept_id,
                    staff_type=staff_type,
                    can_invigilate=True,
                    is_active=True,
                    max_daily_sessions=random.choice([1, 2, 2, 3]),
                    max_consecutive_sessions=random.choice([1, 1, 2]),
                    max_concurrent_exams=random.randint(1, 3),
                    max_students_per_invigilator=random.choice([30, 40, 50, 50, 60]),
                    generic_availability_preferences={},
                )
                staff_to_create.append((user, staff_member))

            session.add_all([u for u, s in staff_to_create])
            await session.flush()
            session.add_all([s for u, s in staff_to_create])

            self.seeded_data["staff"] = len(staff_to_create)
            self.seeded_data["users"] += len(staff_to_create)

    async def _seed_student_enrollments(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding student enrollments...")
            students = (
                (
                    await session.execute(
                        select(Student).options(selectinload(Student.programme))
                    )
                )
                .scalars()
                .all()
            )
            sessions = (await session.execute(select(AcademicSession))).scalars().all()
            if not students or not sessions:
                return

            enrollments = []
            for s in students:
                for sess in sessions:
                    session_start_year = int(sess.name.split("/")[0])
                    level = (session_start_year - s.entry_year + 1) * 100
                    if 100 <= level <= s.programme.duration_years * 100:
                        enrollments.append(
                            StudentEnrollment(
                                student_id=s.id, session_id=sess.id, level=level
                            )
                        )
            session.add_all(enrollments)
            self.seeded_data["student_enrollments"] = len(enrollments)

    async def _seed_course_registrations_and_exams(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding REALISTIC course registrations and exams...")
            active_session = await session.scalar(
                select(AcademicSession).where(AcademicSession.is_active == True)
            )
            if not active_session:
                logger.warning("No active session, skipping registrations.")
                return

            # 1. Pre-fetch and group all necessary data
            all_courses = (await session.execute(select(Course))).scalars().all()
            enrollments = (
                (
                    await session.execute(
                        select(StudentEnrollment)
                        .where(StudentEnrollment.session_id == active_session.id)
                        .options(
                            joinedload(StudentEnrollment.student).joinedload(
                                Student.programme
                            )
                        )
                    )
                )
                .scalars()
                .all()
            )

            if not all_courses or not enrollments:
                logger.warning("Missing courses or enrollments, skipping.")
                return

            # Create mappings for courses based on new schema
            course_dept_pairs = (
                await session.execute(
                    select(CourseDepartment.course_id, CourseDepartment.department_id)
                )
            ).all()
            dept_to_course_ids = defaultdict(list)
            for c_id, d_id in course_dept_pairs:
                dept_to_course_ids[d_id].append(c_id)

            course_id_map = {c.id: c for c in all_courses}

            # Group courses by department and level for efficient lookup
            courses_by_dept_level = defaultdict(list)
            for dept_id, course_ids in dept_to_course_ids.items():
                for course_id in course_ids:
                    course = course_id_map.get(course_id)
                    if course:
                        courses_by_dept_level[(dept_id, course.course_level)].append(
                            course
                        )

            # Group students by programme and level
            students_by_prog_level = defaultdict(list)
            for enr in enrollments:
                students_by_prog_level[(enr.student.programme_id, enr.level)].append(
                    enr.student_id
                )

            registrations = []
            course_student_counts = defaultdict(int)

            # 2. Iterate through student groups (cohorts) to create structured registrations
            for (prog_id, level), student_ids in students_by_prog_level.items():
                prog = await session.get(Programme, prog_id)
                if not prog:
                    continue

                dept_id = prog.department_id
                core_courses = courses_by_dept_level.get((dept_id, level), [])
                elective_pool = courses_by_dept_level.get((dept_id, level + 100), [])
                carryover_pool = courses_by_dept_level.get((dept_id, level - 100), [])

                num_core = min(len(core_courses), random.choice([4, 4, 5]))
                num_electives = min(len(elective_pool), random.choice([1, 2, 2]))

                selected_core = (
                    random.sample(core_courses, num_core) if core_courses else []
                )
                selected_electives = (
                    random.sample(elective_pool, num_electives) if elective_pool else []
                )

                for student_id in student_ids:
                    for course in selected_core + selected_electives:
                        registrations.append(
                            CourseRegistration(
                                student_id=student_id,
                                course_id=course.id,
                                session_id=active_session.id,
                                registration_type="normal",
                            )
                        )
                        course_student_counts[course.id] += 1

                    if carryover_pool and random.random() < 0.15:
                        course = random.choice(carryover_pool)
                        registrations.append(
                            CourseRegistration(
                                student_id=student_id,
                                course_id=course.id,
                                session_id=active_session.id,
                                registration_type="carryover",
                            )
                        )
                        course_student_counts[course.id] += 1

            session.add_all(registrations)
            self.seeded_data["course_registrations"] = len(registrations)
            logger.info(
                f"  - Created {len(registrations)} structured course registrations."
            )

            # 3. Create exams based on the final registration counts
            exams = []
            for course_id, count in course_student_counts.items():
                course = course_id_map.get(course_id)
                if course and count > 0:
                    exams.append(
                        Exam(
                            course_id=course.id,
                            session_id=active_session.id,
                            duration_minutes=course.exam_duration_minutes or 120,
                            expected_students=count,
                            status="pending",
                            is_practical=course.is_practical or False,
                            morning_only=course.morning_only or False,
                            requires_projector=random.random() < 0.2,
                            requires_special_arrangements=False,
                            is_common=count > 150,
                        )
                    )
            session.add_all(exams)
            self.seeded_data["exams"] = len(exams)
            logger.info(f"  - Created {len(exams)} exams based on registration counts.")

    async def _seed_exam_details(self):
        async with db_manager.get_db_transaction() as session:
            logger.info(
                "  - Seeding exam details (departments for cross-listed courses)..."
            )
            exams = (await session.execute(select(Exam))).scalars().all()
            if not exams:
                return

            # Create a map of course_id -> list of department_ids
            course_dept_pairs = (
                await session.execute(
                    select(CourseDepartment.course_id, CourseDepartment.department_id)
                )
            ).all()
            course_to_depts_map = defaultdict(list)
            for c_id, d_id in course_dept_pairs:
                course_to_depts_map[c_id].append(d_id)

            exam_depts = []
            # Handle exams for courses linked to specific departments
            for e in exams:
                associated_dept_ids = course_to_depts_map.get(e.course_id, [])
                for dept_id in associated_dept_ids:
                    exam_depts.append(
                        ExamDepartment(exam_id=e.id, department_id=dept_id)
                    )

            # Handle exams for faculty-wide courses
            course_faculty_pairs = (
                await session.execute(
                    select(CourseFaculty.course_id, CourseFaculty.faculty_id)
                )
            ).all()
            faculty_to_depts_map = defaultdict(list)
            all_depts = (await session.execute(select(Department))).scalars().all()
            for dept in all_depts:
                faculty_to_depts_map[dept.faculty_id].append(dept.id)

            for e in exams:
                if not course_to_depts_map.get(
                    e.course_id
                ):  # Only if it has no dept links
                    for c_id, f_id in course_faculty_pairs:
                        if c_id == e.course_id:
                            depts_in_faculty = faculty_to_depts_map.get(f_id, [])
                            for dept_id in depts_in_faculty:
                                exam_depts.append(
                                    ExamDepartment(exam_id=e.id, department_id=dept_id)
                                )

            # Ensure uniqueness and add to session
            unique_exam_depts_tuples = {
                (ed.exam_id, ed.department_id) for ed in exam_depts
            }
            final_exam_depts = [
                ExamDepartment(exam_id=eid, department_id=did)
                for eid, did in unique_exam_depts_tuples
            ]

            session.add_all(final_exam_depts)
            self.seeded_data["exam_departments"] = len(final_exam_depts)

    async def _seed_course_instructors(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding course instructors...")
            course_ids = (await session.execute(select(Course.id))).scalars().all()
            staff_ids = (
                (
                    await session.execute(
                        select(Staff.id).where(Staff.staff_type == "academic")
                    )
                )
                .scalars()
                .all()
            )
            if not course_ids or not staff_ids:
                return

            instructors = [
                CourseInstructor(course_id=c, staff_id=s)
                for c in course_ids
                for s in random.sample(
                    staff_ids, min(random.randint(1, 2), len(staff_ids))
                )
            ]
            session.add_all(instructors)
            self.seeded_data["course_instructors"] = len(instructors)

    async def _seed_staff_unavailability(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding staff unavailability...")
            staff_ids = (
                (
                    await session.execute(
                        select(Staff.id).where(Staff.can_invigilate == True)
                    )
                )
                .scalars()
                .all()
            )
            active_session = await session.scalar(
                select(AcademicSession)
                .where(AcademicSession.is_active == True)
                .options(
                    joinedload(AcademicSession.timeslot_template).joinedload(
                        TimeSlotTemplate.periods
                    )
                )
            )
            if not staff_ids or not active_session:
                return

            exam_dates = [
                active_session.start_date + timedelta(i)
                for i in range(
                    (active_session.end_date - active_session.start_date).days + 1
                )
                if (active_session.start_date + timedelta(i)).weekday() < 5
            ]
            periods = (
                [p.period_name for p in active_session.timeslot_template.periods]
                if active_session.timeslot_template
                else ["Morning"]
            )

            unavail_set = set()
            for s in random.sample(
                staff_ids, k=min(len(staff_ids), int(len(staff_ids) * 0.7))
            ):
                for _ in range(random.randint(1, 3)):
                    unavail_set.add(
                        (
                            s,
                            active_session.id,
                            random.choice(exam_dates),
                            random.choice(periods),
                        )
                    )

            unavailabilities = [
                StaffUnavailability(
                    staff_id=s, session_id=sess, unavailable_date=d, time_slot_period=p
                )
                for s, sess, d, p in unavail_set
            ]
            session.add_all(unavailabilities)
            self.seeded_data["staff_unavailability"] = len(unavailabilities)

    async def _seed_timetable_scenarios_jobs_and_versions(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding timetabling jobs and versions...")
            session_ids = (
                (await session.execute(select(AcademicSession.id))).scalars().all()
            )
            config_ids = (
                (await session.execute(select(SystemConfiguration.id))).scalars().all()
            )
            admin_id = self.demo_users["admin"].id
            if not all([session_ids, config_ids, admin_id]):
                return

            scenarios = [
                TimetableScenario(name=f"Scenario {i+1}", created_by=admin_id)
                for i in range(SCALE_LIMITS["timetable_scenarios"])
            ]
            session.add_all(scenarios)
            await session.flush()
            self.seeded_data["timetable_scenarios"] = len(scenarios)

            jobs = [
                TimetableJob(
                    session_id=random.choice(session_ids),
                    initiated_by=admin_id,
                    status="completed",
                    progress_percentage=100,
                    hard_constraint_violations=0,
                    can_pause=False,
                    can_resume=False,
                    can_cancel=False,
                    scenario_id=random.choice(scenarios).id,
                    configuration_id=random.choice(config_ids),
                )
                for _ in range(SCALE_LIMITS["timetable_jobs"])
            ]
            session.add_all(jobs)
            await session.flush()
            self.seeded_data["timetable_jobs"] = len(jobs)

            versions = [
                TimetableVersion(
                    job_id=j.id,
                    version_number=i + 1,
                    version_type="auto",
                    is_active=(i == 0),
                    is_published=True,
                    scenario_id=j.scenario_id,
                )
                for j in jobs
                for i in range(random.randint(1, 2))
            ]
            session.add_all(versions)
            self.seeded_data["timetable_versions"] = len(versions)

    async def _seed_versioning_details(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding versioning details (metadata, dependencies)...")
            versions = (await session.execute(select(TimetableVersion))).scalars().all()
            if len(versions) < 2:
                return

            metadata = [
                VersionMetadata(
                    version_id=v.id,
                    title=f"Version {v.version_number}",
                    description=fake.sentence(),
                )
                for v in versions
            ]
            session.add_all(metadata)
            self.seeded_data["version_metadata"] = len(metadata)

            dependencies = []
            for _ in range(SCALE_LIMITS["version_dependencies"]):
                v1, v2 = random.sample(versions, 2)
                if v1.id != v2.id:
                    dependencies.append(
                        VersionDependency(
                            version_id=v1.id,
                            depends_on_version_id=v2.id,
                            dependency_type="based_on",
                        )
                    )
            session.add_all(dependencies)
            self.seeded_data["version_dependencies"] = len(dependencies)

    async def _seed_timetable_assignments_and_invigilators(self):
        async with db_manager.get_db_transaction() as session:
            logger.info(
                "  - Seeding assignments and invigilators with realistic room and staff allocation..."
            )
            versions = (
                (
                    await session.execute(
                        select(TimetableVersion).options(
                            joinedload(TimetableVersion.job)
                            .joinedload(TimetableJob.session)
                            .joinedload(AcademicSession.timeslot_template)
                            .joinedload(TimeSlotTemplate.periods)
                        )
                    )
                )
                .scalars()
                .unique()
                .all()
            )

            all_rooms_q = await session.execute(
                select(Room)
                .where(Room.exam_capacity.isnot(None), Room.exam_capacity > 0)
                .order_by(Room.exam_capacity.desc())
            )
            all_rooms = all_rooms_q.scalars().all()

            exams = (await session.execute(select(Exam))).scalars().all()

            staff_q = await session.execute(
                select(Staff).where(Staff.can_invigilate == True)
            )
            all_staff_map = {s.id: s for s in staff_q.scalars().all()}

            unavail_q = await session.execute(select(StaffUnavailability))
            unavail_set = {
                (r.staff_id, r.session_id, r.unavailable_date, r.time_slot_period)
                for r in unavail_q.scalars().all()
            }

            if not all([versions, all_rooms, exams, all_staff_map]):
                logger.warning(
                    "Missing core data for assignment/invigilator seeding. Skipping."
                )
                return

            total_assignments_created = []
            total_invigilators_created = []

            for ver in versions:
                sess = ver.job.session
                if not sess or not sess.timeslot_template:
                    continue

                exam_dates = [
                    sess.start_date + timedelta(d)
                    for d in range((sess.end_date - sess.start_date).days + 1)
                    if (sess.start_date + timedelta(d)).weekday() < 5
                ]
                periods = sess.timeslot_template.periods
                period_map = {p.id: p.period_name for p in periods}
                sess_exams = [e for e in exams if e.session_id == sess.id]

                assignments_by_slot = defaultdict(list)
                assignments_this_version = []

                for exam in random.sample(
                    sess_exams, min(len(sess_exams), int(len(sess_exams) * 0.9))
                ):
                    if not exam_dates or not periods:
                        continue

                    students_to_assign = exam.expected_students
                    is_primary = True
                    exam_date = random.choice(exam_dates)
                    period_id = random.choice([p.id for p in periods])
                    slot_key = (exam_date, period_id)

                    while students_to_assign > 0:
                        room_to_use = None
                        best_fit_rooms = sorted(
                            [
                                r
                                for r in all_rooms
                                if r.exam_capacity
                                and r.exam_capacity >= students_to_assign
                            ],
                            key=lambda r: r.exam_capacity or 0,
                        )

                        if best_fit_rooms:
                            room_to_use = best_fit_rooms[0]
                        elif all_rooms:
                            room_to_use = all_rooms[0]
                        else:
                            break

                        room_capacity = room_to_use.exam_capacity
                        if not room_capacity:
                            continue

                        students_in_this_room = min(students_to_assign, room_capacity)

                        assignment = TimetableAssignment(
                            exam_id=exam.id,
                            room_id=room_to_use.id,
                            version_id=ver.id,
                            exam_date=exam_date,
                            timeslot_template_period_id=period_id,
                            student_count=students_in_this_room,
                            allocated_capacity=room_capacity,
                            is_primary=is_primary,
                            is_confirmed=True,
                        )
                        assignments_this_version.append(assignment)
                        assignments_by_slot[slot_key].append(assignment)
                        students_to_assign -= students_in_this_room
                        is_primary = False

                if not assignments_this_version:
                    continue

                session.add_all(assignments_this_version)
                await session.flush()

                invigilators_this_version = []
                for (
                    exam_date,
                    period_id,
                ), slot_assignments in assignments_by_slot.items():
                    period_name = period_map.get(period_id)
                    session_id = ver.job.session_id
                    if not period_name or not session_id:
                        continue

                    available_staff_pool = [
                        sid
                        for sid in all_staff_map.keys()
                        if (sid, session_id, exam_date, period_name) not in unavail_set
                    ]
                    random.shuffle(available_staff_pool)

                    for assignment in slot_assignments:
                        required_invigilators = max(
                            1, math.ceil(assignment.student_count / 50)
                        )

                        if len(available_staff_pool) >= required_invigilators:
                            assigned_staff_ids = available_staff_pool[
                                :required_invigilators
                            ]
                            available_staff_pool = available_staff_pool[
                                required_invigilators:
                            ]

                            for staff_id in assigned_staff_ids:
                                invigilators_this_version.append(
                                    ExamInvigilator(
                                        timetable_assignment_id=assignment.id,
                                        staff_id=staff_id,
                                        role="invigilator",
                                    )
                                )

                if invigilators_this_version:
                    session.add_all(invigilators_this_version)

                total_assignments_created.extend(assignments_this_version)
                total_invigilators_created.extend(invigilators_this_version)

            self.seeded_data["timetable_assignments"] = len(total_assignments_created)
            self.seeded_data["exam_invigilators"] = len(total_invigilators_created)

    async def _seed_timetable_support_entities(self):
        async with db_manager.get_db_transaction() as session:
            logger.info(
                "  - Seeding timetable support entities (conflicts, edits, locks)..."
            )
            versions_ids = (
                (await session.execute(select(TimetableVersion.id))).scalars().all()
            )
            exam_ids = (await session.execute(select(Exam.id))).scalars().all()
            user_ids = (await session.execute(select(User.id))).scalars().all()
            scenario_ids = (
                (await session.execute(select(TimetableScenario.id))).scalars().all()
            )

            assignments_result = await session.execute(
                select(TimetableAssignment).options(
                    selectinload(TimetableAssignment.version)
                )
            )
            assignments = assignments_result.scalars().all()

            if versions_ids:
                conflicts = [
                    TimetableConflict(
                        version_id=random.choice(versions_ids),
                        type="Student Conflict",
                        severity="high",
                        message=fake.sentence(),
                        is_resolved=random.choice([True, False]),
                    )
                    for _ in range(SCALE_LIMITS["timetable_conflicts"])
                ]
                session.add_all(conflicts)
                self.seeded_data["timetable_conflicts"] = len(conflicts)

            if versions_ids and exam_ids and user_ids:
                edits = [
                    TimetableEdit(
                        version_id=random.choice(versions_ids),
                        exam_id=random.choice(exam_ids),
                        edited_by=random.choice(user_ids),
                        edit_type="manual_reschedule",
                        validation_status="valid",
                    )
                    for _ in range(SCALE_LIMITS["timetable_edits"])
                ]
                session.add_all(edits)
                self.seeded_data["timetable_edits"] = len(edits)

            if assignments:
                job_exam_days_set = {
                    (a.version.job_id, a.exam_date) for a in assignments if a.version
                }
                job_days_to_add = [
                    TimetableJobExamDay(timetable_job_id=job_id, exam_date=ex_date)
                    for job_id, ex_date in job_exam_days_set
                ]
                if job_days_to_add:
                    session.add_all(job_days_to_add)
                    self.seeded_data["timetable_job_exam_days"] = len(job_days_to_add)

    async def _seed_system_events_and_notifications(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding system events and notifications...")
            user_ids = (await session.execute(select(User.id))).scalars().all()
            if not user_ids:
                return
            events = [
                SystemEvent(
                    title=fake.bs(),
                    message=fake.sentence(),
                    event_type="info",
                    priority="low",
                    is_resolved=True,
                )
                for _ in range(SCALE_LIMITS["system_events"])
            ]
            session.add_all(events)
            await session.flush()
            self.seeded_data["system_events"] = len(events)

            notifications = [
                UserNotification(
                    user_id=uid, event_id=e.id, is_read=random.choice([True, False])
                )
                for e in events
                for uid in random.sample(user_ids, min(3, len(user_ids)))
            ]
            session.add_all(notifications)
            self.seeded_data["user_notifications"] = len(notifications)

    async def _seed_audit_logs(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding audit logs...")
            user_ids = (await session.execute(select(User.id))).scalars().all()
            if not user_ids:
                return
            logs = [
                AuditLog(
                    user_id=random.choice(user_ids),
                    action=random.choice(["create", "update", "delete"]),
                    entity_type=random.choice(["exam", "student", "room"]),
                    ip_address=fake.ipv4(),
                )
                for _ in range(SCALE_LIMITS["audit_logs"])
            ]
            session.add_all(logs)
            self.seeded_data["audit_logs"] = len(logs)

    async def _seed_file_upload_entities(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding file upload and data seeding entities...")
            user_ids = (await session.execute(select(User.id))).scalars().all()
            session_ids = (
                (await session.execute(select(AcademicSession.id))).scalars().all()
            )
            if not user_ids or not session_ids:
                return

            num_to_create = min(len(session_ids), SCALE_LIMITS["data_seeding_sessions"])
            selected_session_ids = random.sample(session_ids, num_to_create)

            data_seed_sessions = [
                DataSeedingSession(
                    academic_session_id=session_id,
                    status="completed",
                    created_by=random.choice(user_ids),
                )
                for session_id in selected_session_ids
            ]
            session.add_all(data_seed_sessions)
            await session.flush()
            self.seeded_data["data_seeding_sessions"] = len(data_seed_sessions)

            if not data_seed_sessions:
                return

            file_uploads = [
                FileUpload(
                    data_seeding_session_id=s.id,
                    upload_type="students",
                    status="completed",
                    file_name=fake.file_name(extension="csv"),
                    file_path=f"/fake/{uuid4()}.csv",
                )
                for s in data_seed_sessions
                for _ in range(2)
            ]
            session.add_all(file_uploads)
            self.seeded_data["file_uploads"] = len(file_uploads)

            file_upload_sessions = [
                FileUploadSession(
                    upload_type="invigilators",
                    uploaded_by=random.choice(user_ids),
                    session_id=random.choice(session_ids),
                    status="completed",
                )
                for _ in range(SCALE_LIMITS["file_upload_sessions"])
            ]
            session.add_all(file_upload_sessions)
            await session.flush()
            self.seeded_data["file_upload_sessions"] = len(file_upload_sessions)

            if not file_upload_sessions:
                return

            uploaded_files = [
                UploadedFile(
                    upload_session_id=s.id,
                    file_name=fake.file_name(extension="xlsx"),
                    file_path=f"/fake/{uuid4()}.xlsx",
                    file_size=random.randint(1000, 50000),
                    file_type="excel",
                    validation_status="valid",
                )
                for s in file_upload_sessions
            ]
            session.add_all(uploaded_files)
            self.seeded_data["uploaded_files"] = len(uploaded_files)

    async def _seed_user_presets(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding user filter presets...")
            user_ids = (await session.execute(select(User.id))).scalars().all()
            if not user_ids:
                return

            presets = [
                UserFilterPreset(
                    user_id=random.choice(user_ids),
                    preset_name=f"Preset {i}",
                    preset_type="exam_view",
                    filters={"level": "100", "status": "pending"},
                )
                for i in range(SCALE_LIMITS["user_filter_presets"])
            ]
            session.add_all(presets)
            self.seeded_data["user_filter_presets"] = len(presets)

    async def _seed_feedback_and_reporting_entities(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding feedback and reporting...")
            staff_ids = (await session.execute(select(Staff.id))).scalars().all()
            student_ids = (await session.execute(select(Student.id))).scalars().all()
            assignment_ids = (
                (await session.execute(select(TimetableAssignment.id))).scalars().all()
            )
            exam_ids = (await session.execute(select(Exam.id))).scalars().all()

            if staff_ids and assignment_ids:
                reqs = [
                    AssignmentChangeRequest(
                        staff_id=random.choice(staff_ids),
                        timetable_assignment_id=random.choice(assignment_ids),
                        reason="Personal",
                        status=random.choice(["pending", "approved", "rejected"]),
                    )
                    for _ in range(SCALE_LIMITS["assignment_change_requests"])
                ]
                session.add_all(reqs)
                self.seeded_data["assignment_change_requests"] = len(reqs)

            if student_ids and exam_ids:
                reports = [
                    ConflictReport(
                        student_id=random.choice(student_ids),
                        exam_id=random.choice(exam_ids),
                        description="Two exams at once.",
                        status=random.choice(["pending", "resolved"]),
                    )
                    for _ in range(SCALE_LIMITS["conflict_reports"])
                ]
                session.add_all(reports)
                self.seeded_data["conflict_reports"] = len(reports)

    async def print_summary(self, dry_run=False):
        logger.info("\n" + "=" * 60 + "\n📊 SEEDING SUMMARY\n" + "=" * 60)
        source = SCALE_LIMITS if dry_run else self.seeded_data
        all_keys = sorted(list(set(SCALE_LIMITS.keys()) | set(self.seeded_data.keys())))
        for key in all_keys:
            intended = SCALE_LIMITS.get(key, 0)
            actual = self.seeded_data.get(key, 0)
            name = key.replace("_", " ").title()
            if dry_run:
                logger.info(f"{name:<35}: {intended:>{10},}")
            else:
                logger.info(f"{name:<35}: {actual:>{10},} (intended: {intended:,})")
        logger.info("=" * 60)


async def main():
    parser = argparse.ArgumentParser(
        description="Seed the database with comprehensive fake data."
    )
    parser.add_argument("--database-url", help="Database connection URL.")
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Drop all existing data before seeding.",
    )
    parser.add_argument(
        "--magnitude",
        type=int,
        choices=[1, 2, 3, 4, 5],
        default=1,
        help="Data size magnitude.",
    )
    parser.add_argument(
        "--seed", type=int, help="A seed for the random number generator."
    )
    args = parser.parse_args()

    seeder = ComprehensiveFakeSeeder(
        database_url=args.database_url, seed=args.seed, magnitude=args.magnitude
    )
    try:
        await seeder.run(drop_existing=args.drop_existing)
    except Exception:
        logger.critical("Seeding process failed. See error details above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
