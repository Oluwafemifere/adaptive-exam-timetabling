#!/usr/bin/env python3

# backend/Scripts/seeders/fake_seed.py

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
from uuid import uuid4, UUID
import uuid

from faker import Faker
from sqlalchemy import func, select, text, UniqueConstraint
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
        CourseDepartment,
        CourseFaculty,
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
        RoomDepartment,
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

        # MODIFIED: These are now session-scoped, reset for each session
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
                "staff": 5,
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
                "staff": 25,
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
                "staff": 100,
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
                "staff": 250,
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
                "staff": 500,
                "buildings": 15,
                "rooms": 400,
                "academic_sessions": 4,
            },
        }
        base_counts = MAGNITUDE_LEVELS[level]
        base_counts["exams"] = int(base_counts["courses"] * 0.8)

        global SCALE_LIMITS
        SCALE_LIMITS = {**base_counts}  # Other limits can be added here as before
        logger.info(
            f"Seeding magnitude set to level {level} (students per session: {SCALE_LIMITS['students']})"
        )

    async def run(self, drop_existing: bool = False):
        logger.info("🚀 Starting comprehensive fake data seeding...")
        try:
            await init_db(database_url=self.database_url, create_tables=False)
            logger.info("✅ Database connection established.")

            if drop_existing:
                await self._clear_all_data()

            # MODIFIED: New session-centric seeding flow
            await self._seed_global_entities()
            await self._seed_session_specific_data()
            await self._seed_post_session_data()

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
                "timetable_versions",
                "system_events",
                "timetable_jobs",
                "timetable_scenarios",
                "file_upload_sessions",
                "data_seeding_sessions",
                "exam_prerequisites_association",
                "exam_departments",
                "configuration_rule_settings",
                "system_configurations",
                "constraint_configurations",
                "constraint_parameters",
                "constraint_rules",
                "course_instructors",
                "course_faculties",
                "course_departments",
                "course_registrations",
                "student_enrollments",
                "staff_unavailability",
                "exams",
                "courses",
                "staff",
                "students",
                "programmes",
                "room_departments",
                "departments",
                "faculties",
                "rooms",
                "room_types",
                "buildings",
                "timeslot_template_periods",
                "timeslot_templates",
                "session_templates",
                "academic_sessions",
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

    async def _generate_unique_email(self, first, last, suffix="baze.edu.ng"):
        email = f"{first.lower()}.{last.lower()}@{suffix}".replace(" ", "")
        c = 1
        while email in self.generated_emails:
            email = f"{first.lower()}.{last.lower()}{c}@{suffix}".replace(" ", "")
            c += 1
        self.generated_emails.add(email)
        return email

    # --- MODIFIED SEEDING FLOW ---

    async def _seed_global_entities(self):
        """Seed entities that are not session-specific."""
        logger.info("Phase 1: Seeding Global Entities...")
        await self._seed_timeslot_templates()
        await self._seed_session_templates()
        await self._seed_constraints_and_config()
        await self._seed_demo_user_accounts()
        await self._seed_room_types()
        await self._seed_academic_sessions()

    async def _seed_session_specific_data(self):
        """Iterate through each academic session and seed its related data."""
        logger.info("Phase 2: Seeding Session-Specific Data...")
        async with db_manager.get_db_transaction() as session:
            academic_sessions = (
                (await session.execute(select(AcademicSession))).scalars().all()
            )

            for sess in academic_sessions:
                logger.info(f"  - Populating data for session: {sess.name}")
                # Reset session-scoped unique identifiers
                self.generated_matrics.clear()
                self.generated_staff_numbers.clear()
                self.generated_course_codes.clear()
                self.generated_room_codes.clear()

                faculties = await self._seed_faculties(session, sess.id)
                departments = await self._seed_departments(session, sess.id, faculties)
                programmes = await self._seed_programmes(session, sess.id, departments)
                buildings = await self._seed_buildings(session, sess.id, faculties)
                await self._seed_rooms(session, sess.id, buildings, departments)
                courses = await self._seed_courses(
                    session, sess.id, departments, faculties
                )
                students = await self._seed_students(session, sess.id, programmes)
                staff = await self._seed_staff(session, sess.id, departments)

                # Seed relationships within the session
                await self._seed_course_instructors(session, sess.id, courses, staff)
                await self._seed_course_registrations_and_exams(
                    session, sess.id, courses, students
                )
                await self._seed_student_enrollments(session, sess.id, students)

    async def _seed_post_session_data(self):
        """Seed entities that depend on the session-specific data being in place."""
        logger.info("Phase 3: Seeding Post-Session Dependent Data...")
        await self._seed_timetable_jobs_and_versions()
        await self._seed_versioning_details()
        await self._seed_timetable_support_entities()
        await self._seed_system_events_and_notifications()
        await self._seed_audit_logs()
        await self._seed_feedback_and_reporting_entities()
        await self._seed_file_upload_entities()
        await self._seed_user_presets()

    # --- REVISED, SESSION-SCOPED & GLOBAL SEEDING METHODS ---

    async def _seed_faculties(
        self, session: AsyncSession, session_id: UUID
    ) -> List[Faculty]:
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
            Faculty(
                code=c,
                name=f"Faculty of {n}",
                is_active=True,
                session_id=session_id,
            )
            for c, n in list(faculty_data.items())[: SCALE_LIMITS["faculties"]]
        ]
        session.add_all(faculties)
        await session.flush()
        self.seeded_data["faculties"] += len(faculties)
        return faculties

    async def _seed_departments(
        self, session: AsyncSession, session_id: UUID, faculties: List[Faculty]
    ) -> List[Department]:
        dept_data = {
            "ENG": ["CPE", "MCE", "CVE"],
            "SCI": ["CSC", "PHY", "CHM"],
            "MGT": ["ACC", "BUS", "MKT"],
            "IT": ["IFT", "CYS", "SWE"],
            "LAW": ["PUB", "PRV"],
        }
        depts = []
        for fac in faculties:
            for dept_code in dept_data.get(fac.code, []):
                if len(depts) >= SCALE_LIMITS["departments"]:
                    break
                depts.append(
                    Department(
                        code=dept_code,
                        name=f"Dept. of {dept_code}",
                        faculty_id=fac.id,
                        is_active=True,
                        session_id=session_id,
                    )
                )
        session.add_all(depts)
        await session.flush()
        self.seeded_data["departments"] += len(depts)
        return depts

    async def _seed_programmes(
        self, session: AsyncSession, session_id: UUID, departments: List[Department]
    ) -> List[Programme]:
        progs = []
        for dept in departments:
            if len(progs) >= SCALE_LIMITS["programmes"]:
                break
            progs.append(
                Programme(
                    code=f"B.{dept.code}",
                    name=f"B.Sc {dept.code}",
                    department_id=dept.id,
                    duration_years=4,
                    degree_type="undergraduate",
                    is_active=True,
                    session_id=session_id,
                )
            )
        session.add_all(progs)
        await session.flush()
        self.seeded_data["programmes"] += len(progs)
        return progs

    async def _seed_buildings(
        self, session: AsyncSession, session_id: UUID, faculties: List[Faculty]
    ) -> List[Building]:
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
            faculty_id = random.choice([f.id for f in faculties] + [None])
            buildings.append(
                Building(
                    code=code,
                    name=f"Building {code}",
                    is_active=True,
                    faculty_id=faculty_id,
                    session_id=session_id,
                )
            )
        session.add_all(buildings)
        await session.flush()
        self.seeded_data["buildings"] += len(buildings)
        return buildings

    async def _seed_room_types(self):  # Room types are global
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding global room types...")
            count = await session.scalar(select(func.count(RoomType.id)))
            if count is not None and count > 0:
                logger.info("    - Room types already exist, skipping.")
                self.seeded_data["room_types"] = count
                return

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

    async def _seed_rooms(
        self,
        session: AsyncSession,
        session_id: UUID,
        buildings: List[Building],
        departments: List[Department],
    ):
        room_types = (await session.execute(select(RoomType))).scalars().all()
        if not buildings or not room_types:
            return

        rooms = []
        for _ in range(SCALE_LIMITS["rooms"]):
            b = random.choice(buildings)
            rt = random.choice(room_types)
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
                    session_id=session_id,
                )
            )
        session.add_all(rooms)
        await session.flush()
        self.seeded_data["rooms"] += len(rooms)

        if rooms and departments:
            room_depts = [
                RoomDepartment(room_id=room.id, department_id=dept.id)
                for room in rooms
                if random.random() < 0.9
                for dept in random.sample(
                    departments,
                    min(
                        random.choices([1, 2], weights=[0.9, 0.1], k=1)[0],
                        len(departments),
                    ),
                )
            ]
            session.add_all(room_depts)
            self.seeded_data["room_departments"] += len(room_depts)

    async def _seed_courses(
        self,
        session: AsyncSession,
        session_id: UUID,
        departments: List[Department],
        faculties: List[Faculty],
    ) -> List[Course]:
        if not departments or not faculties:
            return []
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
                    session_id=session_id,
                )
            )
        session.add_all(courses)
        await session.flush()
        self.seeded_data["courses"] += len(courses)

        course_depts, course_facs = [], []
        for course in courses:
            rand_val = random.random()
            if rand_val < 0.85:  # 85% standard course, 1-2 departments
                num_depts = random.choices([1, 2], weights=[0.9, 0.1], k=1)[0]
                depts_to_assign = random.sample(
                    departments, min(num_depts, len(departments))
                )
                for dept in depts_to_assign:
                    course_depts.append(
                        CourseDepartment(
                            course_id=course.id,
                            department_id=dept.id,
                            session_id=session_id,
                        )
                    )
            elif rand_val < 0.95:  # 10% faculty-wide course
                fac_to_assign = random.choice(faculties)
                course_facs.append(
                    CourseFaculty(
                        course_id=course.id,
                        faculty_id=fac_to_assign.id,
                        session_id=session_id,
                    )
                )

        session.add_all(course_depts)
        session.add_all(course_facs)
        self.seeded_data["course_departments"] += len(course_depts)
        self.seeded_data["course_faculties"] += len(course_facs)
        return courses

    async def _seed_course_instructors(
        self,
        session: AsyncSession,
        session_id: UUID,
        courses: List[Course],
        staff: List[Staff],
    ):
        if not courses or not staff:
            return

        academic_staff = [s for s in staff if s.staff_type == "academic"]
        if not academic_staff:
            return

        instructors = [
            CourseInstructor(course_id=c.id, staff_id=s.id, session_id=session_id)
            for c in courses
            for s in random.sample(
                academic_staff, min(random.randint(1, 2), len(academic_staff))
            )
        ]
        session.add_all(instructors)
        self.seeded_data["course_instructors"] += len(instructors)

    async def _seed_students(
        self, session: AsyncSession, session_id: UUID, programmes: List[Programme]
    ) -> List[Student]:
        if not programmes:
            return []
        students_to_create = []
        pwd = hash_password("password123")
        for i in range(SCALE_LIMITS["students"]):
            first, last = fake.first_name(), fake.last_name()
            user_email = await self._generate_unique_email(
                first, last, "student.baze.edu.ng"
            )

            user = await session.scalar(select(User).where(User.email == user_email))
            if not user:
                user = User(
                    email=user_email,
                    first_name=first,
                    last_name=last,
                    password_hash=pwd,
                    is_active=True,
                    is_superuser=False,
                    role="student",
                )
                self.seeded_data["users"] += 1

            prog = random.choice(programmes)
            entry_year = datetime.now().year - random.randint(
                0, prog.duration_years - 1
            )

            matric_counter = i
            while True:
                matric = f"BU/{str(entry_year)[-2:]}/{prog.code}/{matric_counter+1:04d}"
                if matric not in self.generated_matrics:
                    self.generated_matrics.add(matric)
                    break
                matric_counter += 1

            student = Student(
                matric_number=matric,
                first_name=first,
                last_name=last,
                entry_year=entry_year,
                programme_id=prog.id,
                user=user,
                session_id=session_id,
            )
            students_to_create.append(student)

        session.add_all(students_to_create)
        await session.flush()
        self.seeded_data["students"] += len(students_to_create)
        return students_to_create

    async def _seed_staff(
        self, session: AsyncSession, session_id: UUID, departments: List[Department]
    ) -> List[Staff]:
        if not departments:
            return []
        staff_to_create = []
        pwd = hash_password("password123")
        for i in range(SCALE_LIMITS["staff"]):
            first, last = fake.first_name(), fake.last_name()

            user_email = await self._generate_unique_email(
                first, last, "staff.baze.edu.ng"
            )
            user = await session.scalar(select(User).where(User.email == user_email))
            if not user:
                user = User(
                    email=user_email,
                    first_name=first,
                    last_name=last,
                    password_hash=pwd,
                    is_active=True,
                    is_superuser=False,
                    role="staff",
                )
                self.seeded_data["users"] += 1

            staff_num_counter = i
            while True:
                staff_num = f"STF{1001+staff_num_counter}"
                if staff_num not in self.generated_staff_numbers:
                    self.generated_staff_numbers.add(staff_num)
                    break
                staff_num_counter += 1

            is_admin_staff = random.random() < 0.1
            dept_id = random.choice(departments).id if not is_admin_staff else None

            staff_member = Staff(
                staff_number=staff_num,
                first_name=first,
                last_name=last,
                department_id=dept_id,
                staff_type="administrative" if is_admin_staff else "academic",
                can_invigilate=True,
                is_active=True,
                max_daily_sessions=2,
                max_consecutive_sessions=2,
                max_concurrent_exams=1,
                max_students_per_invigilator=50,
                user=user,
                session_id=session_id,
            )
            staff_to_create.append(staff_member)

        session.add_all(staff_to_create)
        await session.flush()
        self.seeded_data["staff"] += len(staff_to_create)
        return staff_to_create

    async def _seed_course_registrations_and_exams(
        self,
        session: AsyncSession,
        session_id: UUID,
        courses: List[Course],
        students: List[Student],
    ):
        if not courses or not students:
            return

        registrations = []
        course_student_counts = defaultdict(int)
        for student in students:
            num_courses = random.randint(5, 8)
            registered_courses = random.sample(courses, min(num_courses, len(courses)))
            for course in registered_courses:
                registrations.append(
                    CourseRegistration(
                        student_id=student.id,
                        course_id=course.id,
                        session_id=session_id,
                        registration_type="normal",
                    )
                )
                course_student_counts[course.id] += 1

        session.add_all(registrations)
        self.seeded_data["course_registrations"] += len(registrations)

        exams = [
            Exam(
                course_id=course.id,
                session_id=session_id,
                duration_minutes=course.exam_duration_minutes or 120,
                expected_students=count,
                status="pending",
                is_practical=course.is_practical or False,
                morning_only=course.morning_only or False,
                requires_projector=random.random() < 0.2,
                requires_special_arrangements=False,
                is_common=count > 150,
            )
            for course in courses
            if (count := course_student_counts.get(course.id, 0)) > 0
        ]
        session.add_all(exams)
        await session.flush()
        self.seeded_data["exams"] += len(exams)

        exam_depts_q = await session.execute(
            select(Exam.id, CourseDepartment.department_id)
            .join(Course, Exam.course_id == Course.id)
            .join(CourseDepartment, CourseDepartment.course_id == Course.id)
            .where(Exam.session_id == session_id)
        )

        exam_depts = [
            ExamDepartment(exam_id=e_id, department_id=d_id)
            for e_id, d_id in exam_depts_q.all()
        ]
        session.add_all(exam_depts)
        self.seeded_data["exam_departments"] += len(exam_depts)

    async def _seed_student_enrollments(
        self, session: AsyncSession, session_id: UUID, students: List[Student]
    ):
        if not students:
            return
        enrollments = []
        current_year = datetime.now().year
        for s in students:
            level = (current_year - s.entry_year + 1) * 100
            if level >= 100:
                enrollments.append(
                    StudentEnrollment(
                        student_id=s.id, session_id=session_id, level=level
                    )
                )

        session.add_all(enrollments)
        self.seeded_data["student_enrollments"] += len(enrollments)

    async def _seed_timetable_jobs_and_versions(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding timetable jobs and initial versions...")
            sessions = (await session.execute(select(AcademicSession))).scalars().all()
            admin_user = self.demo_users.get("admin")
            scenarios = []
            if not admin_user:
                return

            for i in range(3):
                scenarios.append(
                    TimetableScenario(
                        name=f"Scenario {i+1}",
                        description=f"Desc for Scenario {i+1}",
                        created_by=admin_user.id,
                    )
                )
            session.add_all(scenarios)
            await session.flush()
            self.seeded_data["timetable_scenarios"] = len(scenarios)

            jobs = []
            for sess in sessions:
                # Add a dummy configuration_id since it's required by the model
                dummy_config_id = uuid.uuid4()
                for i in range(2):  # 2 jobs per session
                    jobs.append(
                        TimetableJob(
                            session_id=sess.id,
                            scenario_id=random.choice(scenarios).id,
                            status="completed",
                            initiated_by=admin_user.id,
                            # FIXED: Removed 'job_type' as it does not exist on the model
                            # ADDED: Added missing required fields
                            configuration_id=dummy_config_id,
                            progress_percentage=100,
                            hard_constraint_violations=0,
                            can_pause=False,
                            can_resume=False,
                            can_cancel=False,
                        )
                    )
            session.add_all(jobs)
            await session.flush()
            self.seeded_data["timetable_jobs"] = len(jobs)

            versions = [
                TimetableVersion(
                    job_id=job.id,
                    version_number=1,
                    is_published=(i == 0),
                    version_type="generated",
                    is_active=True,
                )
                for i, job in enumerate(jobs)
            ]
            session.add_all(versions)
            self.seeded_data["timetable_versions"] = len(versions)

    async def print_summary(self, dry_run=False):
        logger.info("\n" + "=" * 60 + "\n📊 SEEDING SUMMARY\n" + "=" * 60)

        intended_totals = defaultdict(int)
        sessions_count = SCALE_LIMITS.get("academic_sessions", 1)

        session_scoped_keys = [
            "faculties",
            "departments",
            "programmes",
            "courses",
            "students",
            "staff",
            "buildings",
            "rooms",
            "course_departments",
            "course_faculties",
            "course_instructors",
            "exams",
            "student_enrollments",
            "course_registrations",
            "staff_unavailability",
            "exam_departments",
        ]

        for key, val in SCALE_LIMITS.items():
            if key in session_scoped_keys:
                intended_totals[key] = val * sessions_count
            else:
                intended_totals[key] = val

        all_keys = sorted(
            list(set(intended_totals.keys()) | set(self.seeded_data.keys()))
        )

        for key in all_keys:
            intended = intended_totals.get(key, 0)
            actual = self.seeded_data.get(key, 0)
            name = key.replace("_", " ").title()

            if dry_run:
                logger.info(f"{name:<35}: {intended:>{10},}")
            else:
                logger.info(f"{name:<35}: {actual:>{10},}")

        logger.info("=" * 60)

    # --- OTHER SEEDING METHODS (MOSTLY UNCHANGED) ---

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
            if len(versions) > 1:
                for _ in range(len(versions) // 2):
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

    async def _seed_timeslot_templates(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding timeslot templates...")
            count = await session.scalar(select(func.count(TimeSlotTemplate.id)))
            if count is not None and count > 0:
                logger.info("    - Timeslot templates already exist, skipping.")
                self.seeded_data["timeslot_templates"] = count
                periods_count = await session.scalar(
                    select(func.count(TimeSlotTemplatePeriod.id))
                )
                self.seeded_data["timeslot_template_periods"] = periods_count or 0
                return

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
            count = await session.scalar(select(func.count(SessionTemplate.id)))
            if count is not None and count > 0:
                logger.info("    - Session templates already exist, skipping.")
                self.seeded_data["session_templates"] = count
                return

            templates = [
                SessionTemplate(name=n, description=f"Template for {n}", is_active=True)
                for n in [
                    "Standard Academic Year",
                    "Summer Session",
                    "Executive Programme",
                ]
            ]
            session.add_all(templates)
            self.seeded_data["session_templates"] = len(templates)

    async def _seed_constraints_and_config(self):
        """
        MODIFIED: Seeds a comprehensive set of constraint rules, parameters,
        and a default system configuration that uses them.
        """
        async with db_manager.get_db_transaction() as session:
            logger.info(
                "  - Seeding constraints schema, parameters, and configurations..."
            )
            count = await session.scalar(select(func.count(ConstraintRule.id)))
            if count is not None and count > 0:
                logger.info("    - Constraint rules already exist, skipping.")
                # Also check and report other related tables
                self.seeded_data["constraint_rules"] = count or 0
                self.seeded_data["constraint_parameters"] = (
                    await session.scalar(select(func.count(ConstraintParameter.id)))
                    or 0
                )
                self.seeded_data["constraint_configurations"] = (
                    await session.scalar(select(func.count(ConstraintConfiguration.id)))
                    or 0
                )
                self.seeded_data["configuration_rule_settings"] = (
                    await session.scalar(
                        select(func.count(ConfigurationRuleSetting.id))
                    )
                    or 0
                )
                self.seeded_data["system_configurations"] = (
                    await session.scalar(select(func.count(SystemConfiguration.id)))
                    or 0
                )
                return

            # 1. Define all constraint rules based on the scheduling engine's capabilities
            rules_data = [
                # Hard Constraints
                {
                    "code": "UNIFIED_STUDENT_CONFLICT",
                    "name": "Unified Student Conflict",
                    "type": "hard",
                    "category": "Student",
                    "desc": "Ensures a student is not scheduled for more than one exam at the same time.",
                },
                {
                    "code": "ROOM_CAPACITY_HARD",
                    "name": "Room Capacity",
                    "type": "hard",
                    "category": "Room",
                    "desc": "Ensures the number of students in a room does not exceed its exam capacity.",
                },
                {
                    "code": "ROOM_SEQUENTIAL_USE",
                    "name": "Room Sequential Use",
                    "type": "hard",
                    "category": "Room",
                    "desc": "Prevents two different exams from being scheduled in the same room at the same time.",
                },
                # Soft Constraints with Parameters
                {
                    "code": "MAX_EXAMS_PER_STUDENT_PER_DAY",
                    "name": "Max Exams Per Student Per Day",
                    "type": "soft",
                    "category": "Student",
                    "desc": "Penalizes scheduling a student for more than a set number of exams in a single day.",
                    "params": [
                        {
                            "key": "max_exams_per_day",
                            "data_type": "integer",
                            "default_value": "2",
                            "desc": "The maximum number of exams a student can have in one day before penalties apply.",
                        }
                    ],
                },
                {
                    "code": "MINIMUM_GAP",
                    "name": "Minimum Gap Between Exams",
                    "type": "soft",
                    "category": "Student",
                    "desc": "Penalizes scheduling exams for the same student without a minimum time gap in between.",
                    "params": [
                        {
                            "key": "min_gap_slots",
                            "data_type": "integer",
                            "default_value": "1",
                            "desc": "The minimum number of empty timeslots between two exams for the same student on the same day.",
                        }
                    ],
                },
                {
                    "code": "ROOM_FIT_PENALTY",
                    "name": "Room Fit Penalty",
                    "type": "soft",
                    "category": "Room",
                    "desc": "Penalizes assigning an exam to a room that is much larger than necessary, encouraging efficient use of space.",
                    "params": [
                        {
                            "key": "weight",
                            "data_type": "float",
                            "default_value": "1.0",
                            "desc": "Penalty multiplier for each unit of wasted space (capacity - students).",
                        }
                    ],
                },
                # Soft Constraints (Weight-based)
                {
                    "code": "INSTRUCTOR_CONFLICT",
                    "name": "Instructor Self-Invigilation Conflict",
                    "type": "soft",
                    "category": "Invigilator",
                    "desc": "Penalizes assigning an instructor to invigilate their own course's exam.",
                },
                {
                    "code": "CARRYOVER_STUDENT_CONFLICT",
                    "name": "Carryover Student Conflict",
                    "type": "soft",
                    "category": "Student",
                    "desc": "Penalizes scheduling conflicts for students with carryover courses, treating them as lower priority than hard conflicts.",
                },
                {
                    "code": "DAILY_WORKLOAD_BALANCE",
                    "name": "Daily Workload Balance",
                    "type": "soft",
                    "category": "Workload Balance",
                    "desc": "Penalizes scheduling a highly uneven number of exams across different days of the exam period.",
                },
                {
                    "code": "INVIGILATOR_LOAD_BALANCE",
                    "name": "Invigilator Load Balance",
                    "type": "soft",
                    "category": "Workload Balance",
                    "desc": "Penalizes an uneven distribution of invigilation duties among available staff.",
                },
                {
                    "code": "OVERBOOKING_PENALTY",
                    "name": "Overbooking Penalty",
                    "type": "soft",
                    "category": "Room",
                    "desc": "Applies a penalty for using a room's overbooking capacity.",
                },
                {
                    "code": "PREFERENCE_SLOTS",
                    "name": "Preference Slots",
                    "type": "soft",
                    "category": "Academic Policies",
                    "desc": "Penalizes scheduling exams outside of their preferred slots (e.g., a 'morning-only' exam scheduled in the afternoon).",
                },
                {
                    "code": "ROOM_DURATION_HOMOGENEITY",
                    "name": "Room Duration Homogeneity",
                    "type": "soft",
                    "category": "Optimization",
                    "desc": "Penalizes scheduling exams of different durations in the same room on the same day, encouraging logistical consistency.",
                },
            ]

            rules = [
                ConstraintRule(
                    code=r["code"],
                    name=r["name"],
                    type=r["type"],
                    category=r["category"],
                    description=r["desc"],
                )
                for r in rules_data
            ]
            session.add_all(rules)
            await session.flush()
            self.seeded_data["constraint_rules"] = len(rules)

            # 2. Seed parameters for the relevant rules
            rule_map = {rule.code: rule.id for rule in rules}
            parameters = []
            for r_data in rules_data:
                if "params" in r_data:
                    rule_id = rule_map[r_data["code"]]
                    for p_data in r_data["params"]:
                        parameters.append(
                            ConstraintParameter(
                                rule_id=rule_id,
                                key=p_data["key"],
                                data_type=p_data["data_type"],
                                default_value=p_data["default_value"],
                                description=p_data["desc"],
                            )
                        )
            session.add_all(parameters)
            self.seeded_data["constraint_parameters"] = len(parameters)

            # 3. Create a default Constraint Configuration
            admin_user = self.demo_users.get("admin")
            default_constraint_config = ConstraintConfiguration(
                name="Default System Constraints",
                description="A balanced set of rules for general-purpose timetabling.",
                is_default=True,
                created_by=admin_user.id if admin_user else None,
            )
            session.add(default_constraint_config)
            await session.flush()
            self.seeded_data["constraint_configurations"] = 1

            # 4. Create settings linking all rules to the default configuration
            settings = []
            for rule in rules:
                weight = (
                    100.0 if rule.type == "soft" else 1.0
                )  # Assign a significant default weight to soft constraints
                settings.append(
                    ConfigurationRuleSetting(
                        configuration_id=default_constraint_config.id,
                        rule_id=rule.id,
                        is_enabled=True,
                        weight=weight,
                    )
                )
            session.add_all(settings)
            self.seeded_data["configuration_rule_settings"] = len(settings)

            # 5. Create a default System Configuration that uses the constraint set
            default_system_config = SystemConfiguration(
                name="Default Solver Configuration",
                description="Standard solver settings using the default constraint set.",
                is_default=True,
                constraint_config_id=default_constraint_config.id,
                created_by=admin_user.id if admin_user else None,
                solver_parameters={"time_limit_seconds": 600},
            )
            session.add(default_system_config)
            self.seeded_data["system_configurations"] = 1

    async def _seed_timetable_support_entities(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding timetable support entities...")
            versions_ids = (
                (await session.execute(select(TimetableVersion.id))).scalars().all()
            )
            if not versions_ids:
                return

            conflicts = [
                TimetableConflict(
                    version_id=random.choice(versions_ids),
                    type="Student Conflict",
                    severity="high",
                    message=fake.sentence(),
                    is_resolved=random.choice([True, False]),
                )
                for _ in range(20)
            ]
            session.add_all(conflicts)
            self.seeded_data["timetable_conflicts"] += len(conflicts)

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
                    # FIXED: Added missing non-nullable fields
                    priority=random.choice(["low", "medium", "high"]),
                    is_resolved=random.choice([True, False]),
                )
                for _ in range(10)
            ]
            session.add_all(events)
            await session.flush()
            self.seeded_data["system_events"] += len(events)

            notifications = [
                UserNotification(
                    user_id=uid, event_id=e.id, is_read=random.choice([True, False])
                )
                for e in events
                for uid in random.sample(user_ids, min(3, len(user_ids)))
            ]
            session.add_all(notifications)
            self.seeded_data["user_notifications"] += len(notifications)

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
                for _ in range(50)
            ]
            session.add_all(logs)
            self.seeded_data["audit_logs"] += len(logs)

    async def _seed_file_upload_entities(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding file upload entities...")
            user_ids = (await session.execute(select(User.id))).scalars().all()
            session_ids = (
                (await session.execute(select(AcademicSession.id))).scalars().all()
            )
            if not user_ids or not session_ids:
                return

            upload_sessions = [
                FileUploadSession(
                    upload_type="students",
                    uploaded_by=random.choice(user_ids),
                    session_id=random.choice(session_ids),
                    status="completed",
                )
                for _ in range(3)
            ]
            session.add_all(upload_sessions)
            self.seeded_data["file_upload_sessions"] += len(upload_sessions)

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
                for i in range(5)
            ]
            session.add_all(presets)
            self.seeded_data["user_filter_presets"] += len(presets)

    async def _seed_feedback_and_reporting_entities(self):
        async with db_manager.get_db_transaction() as session:
            logger.info("  - Seeding feedback and reporting...")
            staff_ids = (await session.execute(select(Staff.id))).scalars().all()
            assignment_ids = (
                (await session.execute(select(TimetableAssignment.id))).scalars().all()
            )
            student_ids = (await session.execute(select(Student.id))).scalars().all()
            exam_ids = (await session.execute(select(Exam.id))).scalars().all()

            if staff_ids and assignment_ids:
                reqs = [
                    AssignmentChangeRequest(
                        staff_id=random.choice(staff_ids),
                        timetable_assignment_id=random.choice(assignment_ids),
                        reason="Personal",
                        status=random.choice(["pending", "approved"]),
                    )
                    for _ in range(10)
                ]
                session.add_all(reqs)
                self.seeded_data["assignment_change_requests"] += len(reqs)

            if student_ids and exam_ids:
                reports = [
                    ConflictReport(
                        student_id=random.choice(student_ids),
                        exam_id=random.choice(exam_ids),
                        description="Clash with another exam.",
                        status="pending",
                    )
                    for _ in range(15)
                ]
                session.add_all(reports)
                self.seeded_data["conflict_reports"] += len(reports)


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
        choices=range(6),
        default=1,
        help="Data size magnitude (0-5).",
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
