# backend/app/services/data_management/database_seeder.py
"""
Comprehensive database seeding service that integrates with your existing fake_seed.py
and provides structured data management for the scheduling engine.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
from uuid import UUID
from datetime import datetime, date, time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from collections import defaultdict

from app.models import (
    # Infrastructure
    Building,
    RoomType,
    Room,
    TimeSlot,
    # Academic
    AcademicSession,
    Faculty,
    Department,
    Programme,
    Course,
    Student,
    CourseRegistration,
    # Scheduling
    Exam,
    Staff,
    ExamRoom,
    ExamInvigilator,
    # Users and System
    User,
    UserRole,
    UserRoleAssignment,
    # Constraints
    ConstraintCategory,
    ConstraintRule,
    SystemConfiguration,
)

logger = logging.getLogger(__name__)


class DatabaseSeeder:
    """
    Production-ready database seeding service that works with your existing
    fake_seed.py and provides clean interfaces for the scheduling engine.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.seeded_counts: Dict[str, int] = {}

    async def seed_for_scheduling_engine(
        self, session_id: UUID, validation_mode: bool = True
    ) -> Dict[str, Any]:
        """
        Seed data specifically optimized for scheduling engine testing.
        This creates a clean, consistent dataset that your scheduling engine can use.
        """
        try:
            logger.info(
                f"Starting scheduling engine data seeding for session {session_id}"
            )

            # Get or create the academic session
            session_data = await self._ensure_academic_session(session_id)

            # Seed core infrastructure optimized for scheduling
            infrastructure = await self._seed_scheduling_infrastructure()

            # Seed academic structure with controlled complexity
            academic = await self._seed_academic_structure_for_scheduling(session_id)

            # Create realistic course and student data
            courses_students = await self._seed_courses_and_students_for_scheduling(
                session_id, academic["departments"]
            )

            # Create exams with proper constraints
            exams = await self._create_scheduling_optimized_exams(
                session_id, courses_students["courses"]
            )

            # Seed staff with proper availability constraints
            staff = await self._seed_staff_for_scheduling(academic["departments"])

            # Create constraint system
            constraints = await self._seed_constraint_system()

            # Validate the seeded data
            if validation_mode:
                validation_result = await self._validate_seeded_data(session_id)
            else:
                validation_result = {"valid": True, "issues": []}

            result = {
                "success": True,
                "session_id": str(session_id),
                "seeded_data": {
                    "session": session_data,
                    "infrastructure": infrastructure,
                    "academic": academic,
                    "courses_students": courses_students,
                    "exams": exams,
                    "staff": staff,
                    "constraints": constraints,
                },
                "validation": validation_result,
                "statistics": self.seeded_counts,
            }

            logger.info(f"✅ Scheduling engine seeding completed: {self.seeded_counts}")
            return result

        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Seeding failed: {e}")
            raise

    async def _ensure_academic_session(self, session_id: UUID) -> Dict[str, Any]:
        """Get existing session or create a new one for testing"""
        # Check if session already exists
        stmt = select(AcademicSession).where(AcademicSession.id == session_id)
        result = await self.session.execute(stmt)
        session = result.scalar_one_or_none()

        if session:
            logger.info(f"Using existing academic session: {session.name}")
            return {
                "id": str(session.id),
                "name": session.name,
                "start_date": session.start_date.isoformat(),
                "end_date": session.end_date.isoformat(),
                "is_active": session.is_active,
            }

        # Create new session for testing
        session = AcademicSession(
            id=session_id,
            name=f"Test Session {datetime.now().strftime('%Y-%m')}",
            semester_system="semester",
            start_date=date(2024, 9, 1),
            end_date=date(2025, 8, 31),
            is_active=True,
        )

        self.session.add(session)
        await self.session.flush()
        self.seeded_counts["academic_sessions"] = 1

        logger.info(f"Created new academic session: {session.name}")
        return {
            "id": str(session.id),
            "name": session.name,
            "start_date": session.start_date.isoformat(),
            "end_date": session.end_date.isoformat(),
            "is_active": session.is_active,
        }

    async def _seed_scheduling_infrastructure(self) -> Dict[str, Any]:
        """Create infrastructure optimized for scheduling engine testing"""
        # Check if infrastructure already exists
        existing_buildings = await self.session.execute(select(Building))
        if existing_buildings.scalars().first():
            logger.info("Using existing infrastructure")
            return await self._get_existing_infrastructure_summary()

        # Create buildings
        buildings_data = [
            ("MAIN", "Main Building"),
            ("ENG", "Engineering Block"),
            ("SCI", "Science Block"),
            ("MGT", "Management Block"),
        ]

        buildings = {}
        for code, name in buildings_data:
            building = Building(code=code, name=name, is_active=True)
            self.session.add(building)
            await self.session.flush()
            buildings[code] = building

        # Create room types
        room_types_data = [
            ("Lecture Hall", "Standard lecture hall"),
            ("Computer Lab", "Computer laboratory"),
            ("Auditorium", "Large auditorium"),
            ("Classroom", "Regular classroom"),
        ]

        room_types = {}
        for name, desc in room_types_data:
            room_type = RoomType(name=name, description=desc, is_active=True)
            self.session.add(room_type)
            await self.session.flush()
            room_types[name] = room_type

        # Create rooms with strategic capacities for scheduling
        rooms_config = [
            # Main Building - mixed capacities
            ("MAIN", "MAIN001", "Main Auditorium", 200, "Auditorium"),
            ("MAIN", "MAIN101", "Main Lecture Hall 1", 120, "Lecture Hall"),
            ("MAIN", "MAIN102", "Main Lecture Hall 2", 100, "Lecture Hall"),
            ("MAIN", "MAIN201", "Main Classroom 1", 60, "Classroom"),
            ("MAIN", "MAIN202", "Main Classroom 2", 50, "Classroom"),
            # Engineering Block - tech-focused
            ("ENG", "ENG101", "Engineering Lab 1", 40, "Computer Lab"),
            ("ENG", "ENG102", "Engineering Lab 2", 40, "Computer Lab"),
            ("ENG", "ENG201", "Engineering Lecture Hall", 80, "Lecture Hall"),
            ("ENG", "ENG202", "Engineering Classroom", 45, "Classroom"),
            # Science Block
            ("SCI", "SCI101", "Science Lecture Hall", 90, "Lecture Hall"),
            ("SCI", "SCI201", "Science Lab", 35, "Computer Lab"),
            ("SCI", "SCI202", "Science Classroom", 50, "Classroom"),
            # Management Block
            ("MGT", "MGT101", "Management Hall", 150, "Lecture Hall"),
            ("MGT", "MGT201", "Management Room 1", 70, "Classroom"),
            ("MGT", "MGT202", "Management Room 2", 55, "Classroom"),
        ]

        rooms = []
        for building_code, room_code, name, capacity, room_type_name in rooms_config:
            room = Room(
                code=room_code,
                name=name,
                capacity=capacity,
                exam_capacity=int(capacity * 0.7),  # 70% for exams
                building_id=buildings[building_code].id,
                room_type_id=room_types[room_type_name].id,
                has_projector=(capacity > 60),  # Larger rooms have projectors
                has_ac=True,
                has_computers=(room_type_name == "Computer Lab"),
                is_active=True,
            )
            self.session.add(room)
            rooms.append(room)

        # Create time slots optimized for scheduling
        time_slots_config = [
            ("Morning Slot 1", time(8, 0), time(11, 0), 180),
            ("Morning Slot 2", time(9, 0), time(12, 0), 180),
            ("Afternoon Slot 1", time(12, 0), time(15, 0), 180),
            ("Afternoon Slot 2", time(13, 0), time(16, 0), 180),
            ("Evening Slot", time(16, 0), time(19, 0), 180),
        ]

        time_slots = []
        for name, start_time, end_time, duration in time_slots_config:
            slot = TimeSlot(
                name=name,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration,
                is_active=True,
            )
            self.session.add(slot)
            time_slots.append(slot)

        await self.session.commit()

        self.seeded_counts.update(
            {
                "buildings": len(buildings),
                "room_types": len(room_types),
                "rooms": len(rooms),
                "time_slots": len(time_slots),
            }
        )

        return {
            "buildings": len(buildings),
            "room_types": len(room_types),
            "rooms": len(rooms),
            "time_slots": len(time_slots),
        }

    async def _seed_academic_structure_for_scheduling(
        self, session_id: UUID
    ) -> Dict[str, Any]:
        """Create academic structure optimized for scheduling complexity"""
        # Create faculties
        faculties_data = [
            ("Engineering", "ENG"),
            ("Science", "SCI"),
            ("Management", "MGT"),
        ]

        faculties = []
        for name, code in faculties_data:
            faculty = Faculty(name=name, code=code, is_active=True)
            self.session.add(faculty)
            await self.session.flush()
            faculties.append(faculty)

        # Create departments
        departments_data = [
            ("Computer Engineering", "CPE", "ENG"),
            ("Electrical Engineering", "EEE", "ENG"),
            ("Computer Science", "CSC", "SCI"),
            ("Mathematics", "MTH", "SCI"),
            ("Business Administration", "BUS", "MGT"),
        ]

        departments = []
        faculty_map = {f.code: f for f in faculties}

        for name, code, faculty_code in departments_data:
            department = Department(
                name=name,
                code=code,
                faculty_id=faculty_map[faculty_code].id,
                is_active=True,
            )
            self.session.add(department)
            await self.session.flush()
            departments.append(department)

        # Create programmes
        programmes_data = [
            ("B.Eng Computer Engineering", "BCPE", "CPE", "undergraduate", 5),
            ("B.Eng Electrical Engineering", "BEEE", "EEE", "undergraduate", 5),
            ("B.Sc Computer Science", "BCSC", "CSC", "undergraduate", 4),
            ("B.Sc Mathematics", "BMTH", "MTH", "undergraduate", 4),
            ("B.Sc Business Administration", "BBUS", "BUS", "undergraduate", 4),
        ]

        programmes = []
        dept_map = {d.code: d for d in departments}

        for name, code, dept_code, degree_type, duration in programmes_data:
            programme = Programme(
                name=name,
                code=code,
                department_id=dept_map[dept_code].id,
                degree_type=degree_type,
                duration_years=duration,
                is_active=True,
            )
            self.session.add(programme)
            programmes.append(programme)

        await self.session.commit()

        self.seeded_counts.update(
            {
                "faculties": len(faculties),
                "departments": len(departments),
                "programmes": len(programmes),
            }
        )

        return {
            "faculties": len(faculties),
            "departments": departments,  # Return objects for further use
            "programmes": programmes,
        }

    async def _seed_courses_and_students_for_scheduling(
        self, session_id: UUID, departments: List[Department]
    ) -> Dict[str, Any]:
        """Create courses and students with realistic scheduling constraints"""

        # Create courses for each department with strategic levels and conflicts
        courses_data = [
            # Computer Engineering (100-level conflicts)
            ("CPE101", "Introduction to Engineering", 3, 100, 1, False, False),
            ("CPE102", "Engineering Mathematics I", 3, 100, 1, False, False),
            ("CPE103", "Engineering Physics", 3, 100, 2, False, False),
            # Computer Engineering (200-level)
            ("CPE201", "Data Structures", 3, 200, 1, False, False),
            ("CPE202", "Digital Logic Design", 3, 200, 1, True, False),  # Practical
            ("CPE203", "Circuit Analysis", 3, 200, 2, False, False),
            # Computer Science (100-level conflicts with CPE)
            ("CSC101", "Introduction to Computing", 3, 100, 1, False, False),
            ("CSC102", "Programming Fundamentals", 4, 100, 1, True, False),  # Practical
            ("CSC103", "Discrete Mathematics", 3, 100, 2, False, False),
            # Computer Science (200-level)
            ("CSC201", "Object-Oriented Programming", 4, 200, 1, True, False),
            ("CSC202", "Database Systems", 3, 200, 1, True, False),
            ("CSC203", "Computer Architecture", 3, 200, 2, False, False),
            # Mathematics (shared courses - high conflict potential)
            ("MTH101", "Calculus I", 4, 100, 1, False, True),  # Morning only
            ("MTH102", "Linear Algebra", 3, 100, 2, False, False),
            ("MTH201", "Calculus II", 4, 200, 1, False, True),  # Morning only
            # Business Administration
            ("BUS101", "Introduction to Business", 3, 100, 1, False, False),
            ("BUS201", "Business Statistics", 3, 200, 1, False, False),
            ("BUS202", "Marketing Principles", 3, 200, 2, False, False),
        ]

        courses = []
        dept_map = {d.code: d for d in departments}

        for (
            code,
            title,
            units,
            level,
            semester,
            is_practical,
            morning_only,
        ) in courses_data:
            # Determine department from course code
            dept_code = code[:3]  # First 3 characters
            if dept_code not in dept_map:
                continue

            course = Course(
                code=code,
                title=title,
                credit_units=units,
                course_level=level,
                semester=semester,
                is_practical=is_practical,
                morning_only=morning_only,
                exam_duration_minutes=180,
                department_id=dept_map[dept_code].id,
                is_active=True,
            )
            self.session.add(course)
            courses.append(course)

        await self.session.flush()

        # Create students with strategic registrations for conflict testing
        programmes = await self._get_programmes()
        students = []

        # Create students for each programme
        for i, programme in enumerate(programmes):
            for j in range(20):  # 20 students per programme
                matric_number = f"BU/2024/{programme.code}/{j+1:03d}"

                student = Student(
                    matric_number=matric_number,
                    entry_year=2024,
                    current_level=100 if j < 15 else 200,  # Mix of levels
                    student_type="regular",
                    programme_id=programme.id,
                    is_active=True,
                )
                self.session.add(student)
                students.append(student)

        await self.session.flush()

        # Create course registrations with strategic conflicts
        registrations = []
        for student in students:
            # Get courses for student's level and programme
            student_courses = [
                c for c in courses if c.course_level <= student.current_level
            ]

            # Register for courses based on programme
            programme_prefix = student.matric_number.split("/")[2]  # Get programme code

            for course in student_courses:
                # Create strategic conflicts
                should_register = False

                # Students register for their department courses
                if course.code.startswith(programme_prefix):
                    should_register = True

                # Cross-registration for shared courses (creates conflicts)
                elif course.code.startswith("MTH"):  # Math courses
                    should_register = True
                elif course.code in ["CSC101", "CPE101"] and programme_prefix in [
                    "CSC",
                    "CPE",
                ]:
                    should_register = True  # Shared intro courses

                if should_register:
                    registration = CourseRegistration(
                        student_id=student.id,
                        course_id=course.id,
                        session_id=session_id,
                        registration_type="regular",
                    )
                    self.session.add(registration)
                    registrations.append(registration)

        await self.session.commit()

        self.seeded_counts.update(
            {
                "courses": len(courses),
                "students": len(students),
                "course_registrations": len(registrations),
            }
        )

        return {
            "courses": courses,
            "students": len(students),
            "registrations": len(registrations),
        }

    async def _get_programmes(self) -> List[Programme]:
        """Get all programmes"""
        stmt = select(Programme)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _create_scheduling_optimized_exams(
        self, session_id: UUID, courses: List[Course]
    ) -> Dict[str, Any]:
        """Create exams with proper expected student counts"""
        exams = []

        for course in courses:
            # Count registered students for this course
            count_query = select(CourseRegistration).where(
                CourseRegistration.course_id == course.id,
                CourseRegistration.session_id == session_id,
            )
            result = await self.session.execute(count_query)
            registered_count = len(list(result.scalars().all()))

            if registered_count > 0:  # Only create exam if students are registered
                exam = Exam(
                    course_id=course.id,
                    session_id=session_id,
                    duration_minutes=course.exam_duration_minutes or 180,
                    expected_students=registered_count,
                    requires_special_arrangements=course.is_practical,
                    status="pending",
                )
                self.session.add(exam)
                exams.append(exam)

        await self.session.commit()

        self.seeded_counts["exams"] = len(exams)

        return {
            "exams_created": len(exams),
            "total_expected_students": sum(e.expected_students for e in exams),
        }

    async def _seed_staff_for_scheduling(
        self, departments: List[Department]
    ) -> Dict[str, Any]:
        """Create staff with realistic availability constraints"""
        staff_data = [
            # Computer Engineering
            (
                "CPE001",
                "Dr. Ahmed Ibrahim",
                "CPE",
                "academic",
                "Senior Lecturer",
                True,
                3,
                2,
            ),
            ("CPE002", "Eng. Fatima Yusuf", "CPE", "academic", "Lecturer", True, 2, 1),
            (
                "CPE003",
                "Mr. Usman Kano",
                "CPE",
                "administrative",
                "Lab Technician",
                True,
                4,
                2,
            ),
            # Computer Science
            (
                "CSC001",
                "Prof. Khadija Musa",
                "CSC",
                "academic",
                "Professor",
                True,
                2,
                1,
            ),
            (
                "CSC002",
                "Dr. Maryam Bello",
                "CSC",
                "academic",
                "Senior Lecturer",
                True,
                3,
                2,
            ),
            (
                "CSC003",
                "Mr. Ibrahim Suleiman",
                "CSC",
                "administrative",
                "IT Officer",
                True,
                3,
                2,
            ),
            # Mathematics
            (
                "MTH001",
                "Dr. Aisha Garba",
                "MTH",
                "academic",
                "Senior Lecturer",
                True,
                2,
                1,
            ),
            (
                "MTH002",
                "Mr. Yusuf Abdullahi",
                "MTH",
                "academic",
                "Lecturer",
                True,
                3,
                2,
            ),
            # General administrative staff
            (
                "ADM001",
                "Mrs. Zainab Aliyu",
                None,
                "administrative",
                "Exam Officer",
                True,
                4,
                3,
            ),
            (
                "ADM002",
                "Mr. Haruna Danjuma",
                None,
                "administrative",
                "Security",
                True,
                5,
                3,
            ),
            (
                "ADM003",
                "Miss Halima Umar",
                None,
                "administrative",
                "Registry",
                True,
                3,
                2,
            ),
        ]

        staff_members = []
        dept_map = {d.code: d for d in departments}

        for (
            staff_number,
            name,
            dept_code,
            staff_type,
            position,
            can_invigilate,
            max_daily,
            max_consecutive,
        ) in staff_data:
            # Create user first (simplified for testing)
            first_name, last_name = (
                name.replace("Dr. ", "")
                .replace("Prof. ", "")
                .replace("Eng. ", "")
                .replace("Mr. ", "")
                .replace("Mrs. ", "")
                .replace("Miss ", "")
                .split(" ", 1)
            )

            # Find or create user
            user_result = await self.session.execute(
                select(User).where(
                    User.first_name == first_name, User.last_name == last_name
                )
            )
            user = user_result.scalar_one_or_none()

            if not user:
                email = f"{first_name.lower()}.{last_name.lower()}@baze.edu.ng"
                user = User(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True,
                )
                self.session.add(user)
                await self.session.flush()

            staff = Staff(
                user_id=user.id,
                staff_number=staff_number,
                department_id=(
                    dept_map[dept_code].id
                    if dept_code and dept_code in dept_map
                    else None
                ),
                staff_type=staff_type,
                position=position,
                can_invigilate=can_invigilate,
                max_daily_sessions=max_daily,
                max_consecutive_sessions=max_consecutive,
                is_active=True,
            )
            self.session.add(staff)
            staff_members.append(staff)

        await self.session.commit()

        self.seeded_counts["staff"] = len(staff_members)

        return {
            "staff_created": len(staff_members),
            "academic_staff": sum(
                1 for s in staff_members if s.staff_type == "academic"
            ),
            "administrative_staff": sum(
                1 for s in staff_members if s.staff_type == "administrative"
            ),
        }

    async def _seed_constraint_system(self) -> Dict[str, Any]:
        """Create constraint categories and rules for scheduling"""
        # Check if constraints already exist
        existing = await self.session.execute(select(ConstraintCategory))
        if existing.scalars().first():
            logger.info("Using existing constraint system")
            return {"constraints_created": "existing"}

        # Create constraint categories
        categories_data = [
            ("Hard Constraints", "Must be satisfied for valid timetable", "CP_SAT"),
            ("Soft Constraints", "Preferences to optimize", "GA"),
            ("User Preferences", "Manually configured preferences", "both"),
        ]

        categories = []
        for name, description, enforcement_layer in categories_data:
            category = ConstraintCategory(
                name=name, description=description, enforcement_layer=enforcement_layer
            )
            self.session.add(category)
            await self.session.flush()
            categories.append(category)

        # Create constraint rules
        hard_category = categories[0]
        soft_category = categories[1]

        rules_data = [
            # Hard constraints
            (
                hard_category.id,
                "NO_STUDENT_CONFLICT",
                "No Student Conflicts",
                "hard",
                1.0,
                {"type": "student_conflict", "violation_penalty": 1000},
            ),
            (
                hard_category.id,
                "ROOM_CAPACITY",
                "Room Capacity Limits",
                "hard",
                1.0,
                {"type": "capacity_constraint", "buffer_percentage": 0},
            ),
            (
                hard_category.id,
                "STAFF_AVAILABILITY",
                "Staff Availability",
                "hard",
                1.0,
                {"type": "staff_constraint", "max_violations": 0},
            ),
            # Soft constraints
            (
                soft_category.id,
                "ROOM_UTILIZATION",
                "Optimal Room Utilization",
                "soft",
                0.8,
                {"type": "utilization", "target_range": [0.7, 0.9]},
            ),
            (
                soft_category.id,
                "TIME_DISTRIBUTION",
                "Balanced Time Distribution",
                "soft",
                0.6,
                {"type": "distribution", "preference": "morning"},
            ),
            (
                soft_category.id,
                "STAFF_BALANCE",
                "Balanced Staff Workload",
                "soft",
                0.5,
                {"type": "workload", "max_imbalance": 2},
            ),
        ]

        rules = []
        for category_id, code, name, constraint_type, weight, definition in rules_data:
            rule = ConstraintRule(
                category_id=category_id,
                code=code,
                name=name,
                description=f"Constraint rule: {name}",
                constraint_type=constraint_type,
                default_weight=weight,
                constraint_definition=definition,
                is_active=True,
                is_configurable=True,
            )
            self.session.add(rule)
            rules.append(rule)

        await self.session.commit()

        self.seeded_counts.update(
            {"constraint_categories": len(categories), "constraint_rules": len(rules)}
        )

        return {"categories": len(categories), "rules": len(rules)}

    async def _get_existing_infrastructure_summary(self) -> Dict[str, Any]:
        """Get summary of existing infrastructure"""
        buildings_count = await self.session.execute(select(Building))
        rooms_count = await self.session.execute(select(Room))
        time_slots_count = await self.session.execute(select(TimeSlot))

        return {
            "buildings": len(list(buildings_count.scalars().all())),
            "rooms": len(list(rooms_count.scalars().all())),
            "time_slots": len(list(time_slots_count.scalars().all())),
        }

    async def _validate_seeded_data(self, session_id: UUID) -> Dict[str, Any]:
        """Validate the seeded data for scheduling engine compatibility"""
        issues = []

        try:
            # Check basic counts
            exams_count = await self.session.execute(
                select(Exam).where(Exam.session_id == session_id)
            )
            exams = list(exams_count.scalars().all())

            if not exams:
                issues.append("No exams found for the session")

            # Check for students without registrations
            students_without_registrations = await self.session.execute(
                text(
                    """
                SELECT COUNT(*) FROM exam_system.students s
                WHERE NOT EXISTS (
                    SELECT 1 FROM exam_system.course_registrations cr 
                    WHERE cr.student_id = s.id AND cr.session_id = :session_id
                )
                """
                ),
                {"session_id": str(session_id)},
            )

            orphaned_students = (
                students_without_registrations.scalar() or 0
            )  # Handle None case
            if orphaned_students > 0:
                issues.append(
                    f"{orphaned_students} students have no course registrations"
                )

            # Check for courses without students
            courses_without_students = await self.session.execute(
                text(
                    """
                SELECT COUNT(*) FROM exam_system.courses c
                WHERE NOT EXISTS (
                    SELECT 1 FROM exam_system.course_registrations cr 
                    WHERE cr.course_id = c.id AND cr.session_id = :session_id
                )
                """
                ),
                {"session_id": str(session_id)},
            )

            empty_courses = courses_without_students.scalar() or 0  # Handle None case
            if empty_courses > 0:
                issues.append(f"{empty_courses} courses have no student registrations")

            # Check staff availability
            available_staff = await self.session.execute(
                select(Staff).where(
                    Staff.can_invigilate == True, Staff.is_active == True
                )
            )
            staff_count = len(list(available_staff.scalars().all()))

            if staff_count < len(exams) * 0.5:  # At least 0.5 staff per exam
                issues.append(
                    f"Insufficient staff: {staff_count} available for {len(exams)} exams"
                )

            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "exams_count": len(exams),
                "staff_count": staff_count,
            }

        except Exception as e:
            return {
                "valid": False,
                "issues": [f"Validation error: {str(e)}"],
                "exams_count": 0,
                "staff_count": 0,
            }
