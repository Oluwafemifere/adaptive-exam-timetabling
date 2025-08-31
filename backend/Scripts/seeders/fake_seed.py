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
from typing import Any, Dict, Set
from faker import Faker
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date
# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select, text, cast, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import ARRAY, TEXT

# Import from the backend app
from app.database import db_manager
from app.models import (
    # Infrastructure
    Building,
    RoomType,
    Room,
    # Academic
    AcademicSession,
    Faculty,
    Department,
    Programme,
    TimeSlot,
    Course,
    # People
    Student,
    CourseRegistration,
    Exam,
    # Users and Staff
    User,
    UserRole,
    UserRoleAssignment,
    AuditLog,
    TimetableEdit,
    TimetableVersion,
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

        await init_db(database_url=self.database_url, create_tables=False)
        logger.info("✅ Database initialized")
        # Initialize database connection using the app's database manager
        if drop_existing:
            logger.info("🧹 Clearing existing data...")
            await self._clear_all_data()

        # Seed in dependency order
        await self._seed_users_and_roles()
        await self._seed_infrastructure()
        await self._seed_academic_structure()
        await self._seed_time_slots()
        await self._seed_courses()
        await self._seed_students_and_registrations()
        await self._seed_exams()

        logger.info("🎉 Comprehensive fake data seeding completed!")
        await self.print_summary()

    async def _clear_all_data(self):
        """Clear all existing data to start fresh"""
        async with db_manager.get_db_transaction() as session:
            # Delete in reverse dependency order to respect foreign keys
            tables_to_clear = [
                "user_role_assignments",
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
            target_users = min(SCALE_LIMITS["users"], 100)  # Limit for development

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
                    )
                    session.add(exam)
                    exams_created += 1

            self.seeded_data["exams"] = exams_created
            logger.info(f"✓ Exams: {exams_created} exams created")

    async def _seed_timetable_versions(self):
        """Seed timetable versions for editing"""
        async with db_manager.get_db_transaction() as session:
            logger.info("📋 Seeding timetable versions...")

            # Get academic sessions
            sessions = (await session.execute(select(AcademicSession))).scalars().all()
            users = (await session.execute(select(User))).scalars().all()

            versions_created = 0
            for session in sessions:
                if versions_created >= SCALE_LIMITS["timetable_versions"]:
                    break

                # Create multiple versions per session
                for i in range(1, 4):  # Up to 3 versions per session
                    if versions_created >= SCALE_LIMITS["timetable_versions"]:
                        break

                    version_name = f"Version {i}.0 - {session.name}"
                    existing = (
                        await session.execute(
                            select(TimetableVersion).where(
                                TimetableVersion.name == version_name,
                                TimetableVersion.session_id == session.id,
                            )
                        )
                    ).scalar_one_or_none()

                    if not existing:
                        version = TimetableVersion(
                            name=version_name,
                            session_id=session.id,
                            generated_by=choice(users).id if users else None,
                            is_active=(i == 1),  # First version is active
                            generated_at=fake.date_time_this_year(),
                            notes=fake.sentence() if randint(1, 3) == 1 else None,
                        )
                        session.add(version)
                        versions_created += 1

            self.seeded_data["timetable_versions"] = versions_created
            logger.info(f"✓ Timetable Versions: {versions_created} versions created")

    async def _seed_audit_logs(self):
        """Seed audit logs for system activities"""
        async with db_manager.get_db_transaction() as session:
            logger.info("📝 Seeding audit logs...")

            # Get entities to log actions for
            users = (await session.execute(select(User))).scalars().all()
            exams = (await session.execute(select(Exam))).scalars().all()
            courses = (await session.execute(select(Course))).scalars().all()

            logs_created = 0
            entity_types = ["user", "exam", "course", "student", "room"]
            actions = ["create", "update", "delete", "view", "export"]

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

    async def _seed_timetable_edits(self):
        """Seed timetable edits for exam scheduling"""
        async with db_manager.get_db_transaction() as session:
            logger.info("Seeding timetable edits...")

            # Get required entities
            versions = (await session.execute(select(TimetableVersion))).scalars().all()
            exams = (await session.execute(select(Exam))).scalars().all()
            users = (await session.execute(select(User))).scalars().all()
            time_slots = (await session.execute(select(TimeSlot))).scalars().all()

            if not versions or not exams or not users:
                logger.warning("Skipping timetable edits - missing required data")
                return

            edits_created = 0
            edit_types = [
                "reschedule",
                "room_change",
                "duration_change",
                "cancel",
                "reinstate",
            ]

            for _ in range(SCALE_LIMITS["timetable_edits"]):
                version = choice(versions)
                exam = choice(exams)
                user = choice(users)
                edit_type = choice(edit_types)

                old_values = None
                new_values = None

                # RESCHEDULE
                if edit_type == "reschedule":
                    exam_date = getattr(exam, "exam_date", None)

                    # Build old value safely
                    if isinstance(exam_date, (date, dt_datetime)):
                        old_values = {"exam_date": exam_date.isoformat()}
                    elif exam_date is not None:
                        # fallback for string-like dates or custom types
                        try:
                            parsed = dt_datetime.fromisoformat(str(exam_date))
                            old_values = {"exam_date": str(exam_date)}
                            exam_date = parsed
                        except Exception:
                            old_values = {"exam_date": str(exam_date)}
                            exam_date = None
                    else:
                        old_values = None

                    # Create new date
                    if isinstance(exam_date, (date, dt_datetime)):
                        new_dt = exam_date + timedelta(days=randint(1, 7))
                    else:
                        # fake likely returns a date object; keep it safe
                        new_dt = fake.date_this_year()

                    # ensure isoformat present
                    if isinstance(new_dt, (date, dt_datetime)):
                        new_values = {"exam_date": new_dt.isoformat()}
                    else:
                        new_values = {"exam_date": str(new_dt)}

                # ROOM CHANGE
                elif edit_type == "room_change":
                    room_id = getattr(exam, "room_id", None)
                    old_values = (
                        {"room_id": str(room_id)}
                        if room_id is not None
                        else {"room_id": None}
                    )
                    new_values = {"room_id": str(uuid4())}

                # DURATION CHANGE
                elif edit_type == "duration_change":
                    old_duration = getattr(exam, "duration_minutes", None)
                    if old_duration is None:
                        # choose a sensible default if missing
                        base = randint(60, 180)
                        old_values = {"duration_minutes": None}
                    else:
                        base = int(old_duration)
                        old_values = {"duration_minutes": base}

                    new_duration = max(1, base + randint(-30, 30))
                    new_values = {"duration_minutes": new_duration}

                # CANCEL
                elif edit_type == "cancel":
                    old_values = {"status": getattr(exam, "status", "scheduled")}
                    new_values = {"status": "cancelled"}

                # REINSTATE
                elif edit_type == "reinstate":
                    old_values = {"status": getattr(exam, "status", "cancelled")}
                    new_values = {"status": "scheduled"}

                edit = TimetableEdit(
                    version_id=version.id,
                    exam_id=exam.id,
                    edited_by=user.id,
                    edit_type=edit_type,
                    old_values=old_values,
                    new_values=new_values,
                    reason=(fake.sentence() if randint(1, 3) == 1 else None),
                    validation_status=choice(["pending", "approved", "rejected"]),
                )

                session.add(edit)
                edits_created += 1

                # flush in batches to reduce memory usage
                if edits_created % 50 == 0:
                    await session.flush()

            # final flush to persist remaining
            if edits_created % 50 != 0:
                await session.flush()

            self.seeded_data["timetable_edits"] = edits_created
            logger.info(f"Timetable Edits: {edits_created} edits created")

    async def print_summary(self):
        """Print summary of seeded data"""
        logger.info("\n" + "=" * 50)
        logger.info("📊 FAKE DATA SEEDING SUMMARY")
        logger.info("=" * 50)
        for entity, count in self.seeded_data.items():
            limit = SCALE_LIMITS.get(entity, "N/A")
            logger.info(f"{entity.replace('_', ' ').title()}: {count:,} / {limit}")
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
