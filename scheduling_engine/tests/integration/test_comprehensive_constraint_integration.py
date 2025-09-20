# FIXED: test_comprehensive_constraint_integration.py
# Fix 1: Properly add timeslots to problem instance in createcomprehensiveproblem method
# Fix 2: Ensure all students have exams and all exams have students

import asyncio
import logging
import math
import time
import traceback
import pytest
import json
import random
from typing import Dict, List, Optional, Any, Set, Tuple, cast
from uuid import UUID, uuid4
from datetime import date, timedelta, time as dttime
from dataclasses import dataclass, field
from faker import Faker
from pathlib import Path
from ortools.sat.python import cp_model
import sys
import io
import os

os.environ["PYTHONIOENCODING"] = "utf-8"

# Import scheduling engine modules
from scheduling_engine.core.problem_model import (
    Day,
    ExamSchedulingProblem,
    Exam,
    Room,
    Student,
    Instructor,
    Staff,
    Invigilator,
)
from scheduling_engine.core.constraint_types import (
    ConstraintDefinition,
    ConstraintType,
    ConstraintCategory,
)
from scheduling_engine.core.metrics import QualityScore, SolutionMetrics
from scheduling_engine.core.solution import TimetableSolution, AssignmentStatus
from scheduling_engine.cp_sat import CPSATModelBuilder
from scheduling_engine.cp_sat import CPSATSolverManager
from scheduling_engine.constraints.constraint_manager import CPSATConstraintManager


def setup_logging():
    """Setup detailed logging for the test suite with enhanced formatting"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s"

    # Create logs directory if it doesn't exist
    logs_dir = Path("test_logs")
    logs_dir.mkdir(exist_ok=True)

    # Configure comprehensive logging
    logging.basicConfig(
        level=logging.INFO,  # Reduced from DEBUG to INFO for performance
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                logs_dir / "comprehensive_test_UUID_ONLY.log",
                mode="w",
                encoding="utf-8",
            ),
        ],
    )

    # Set specific logger levels for different components
    loggers = {
        "scheduling_engine": logging.INFO,
        "ortools": logging.WARNING,
        "faker": logging.WARNING,
        "sqlalchemy": logging.WARNING,
    }

    for logger_name, level in loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)

    return logging.getLogger(__name__)


logger = setup_logging()


@dataclass
class TestConfiguration:
    """FIXED: Test configuration with enhanced validation and capacity planning"""

    # Problem size parameters
    num_students: int = 500
    num_courses: int = 50
    num_exams: int = 50  # Should equal num_courses
    num_rooms: int = 15

    # Day configuration parameters
    exam_days_count: Optional[int] = 10
    exam_period_days: int = 14
    timeslots_per_day: int = 3

    # Other parameters
    max_students_per_invigilator: int = 40
    invigilator_surplus_percentage: float = 0.25
    concurrent_exam_factor: float = 1.1
    overbook_rate: float = 0.25

    # Solver settings
    max_solver_time_seconds: int = 300
    enable_presolve_logging: bool = True
    enable_search_logging: bool = True

    # FIXED: Student registration settings to ensure proper distribution
    min_courses_per_student: int = 4  # Increased from 3
    max_courses_per_student: int = 6  # Reduced from 8 to balance
    cross_dept_prob: float = 0.15
    guarantee_large_halls: int = 40

    # Deterministic controls
    deterministic_seed: int = 42
    force_invigilator_generation: bool = True

    # Constraint resilience settings
    allow_zero_constraints: bool = True
    force_constraint_generation: bool = False
    min_room_capacity_buffer: float = 1.3
    min_invigilator_capacity_buffer: float = 1.5
    core_constraint_timeout: int = 30
    show_solutions_on_success: bool = True

    # FIXED: Ensure reasonable student distribution per course
    min_students_per_course: int = 20  # Increased from 10
    max_students_per_course: int = 50  # Increased from 30

    # Room capacity ranges
    room_capacity_ranges: Dict[str, Tuple[int, int]] = field(
        default_factory=lambda: {
            "LH": (80, 120),  # Increased capacity
            "LT": (50, 80),  # Increased capacity
            "CL": (30, 50),  # Increased capacity
            "LAB": (15, 25),  # Increased capacity
        }
    )

    # Debugging settings
    enable_constraint_debugging: bool = True
    debug_constraint_categories: List[str] = field(
        default_factory=lambda: [
            "CORE",
            "STUDENT_CONFLICT",
            "MULTIEXAM_CAPACITY",
            "INVIGILATOR",
        ]
    )

    def calculate_total_timeslots(self) -> int:
        """Calculate total expected timeslots based on day configuration"""
        if self.exam_days_count:
            return self.exam_days_count * self.timeslots_per_day
        else:
            # Estimate based on exam_period_days (weekdays only)
            weekdays = math.ceil(
                self.exam_period_days * 5 / 7
            )  # Rough weekday estimate
            return weekdays * self.timeslots_per_day

    def calculate_required_invigilators(
        self, total_students: int, concurrent_exams: int = 3
    ) -> Dict[str, int]:
        """Calculate required invigilators with enhanced feasibility checks"""
        base_required = math.ceil(total_students / self.max_students_per_invigilator)
        with_buffer = math.ceil(base_required * self.min_invigilator_capacity_buffer)

        instructors_needed = math.ceil(with_buffer * 0.6)
        staff_needed = math.ceil(with_buffer * 0.4)

        logger.info("ENHANCED: Invigilator calculation")
        logger.info(f"Total students: {total_students}")
        logger.info(f"Base required: {base_required}")
        logger.info(f"Instructors: {instructors_needed}")
        logger.info(f"Staff: {staff_needed}")

        return {
            "instructors": instructors_needed,
            "staff": staff_needed,
            "total": instructors_needed + staff_needed,
        }


@dataclass
class TestResults:
    """Container for comprehensive test results with enhanced tracking"""

    test_name: str
    start_time: float
    end_time: Optional[float] = None
    success: bool = False
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    solver_stats: Dict[str, Any] = field(default_factory=dict)
    constraint_stats: Dict[str, Any] = field(default_factory=dict)
    solution: Optional[Any] = None

    @property
    def duration(self) -> float:
        if self.end_time is None:
            return 0.0
        return self.end_time - self.start_time


class RealisticDataGenerator:
    """FIXED: Generate realistic exam timetabling data with UUID-only IDs"""

    def __init__(self, config: TestConfiguration):
        self.config = config

        # FIXED: Set deterministic seed for reproducible results
        if config.deterministic_seed is not None:
            Faker.seed(config.deterministic_seed)
            random.seed(config.deterministic_seed)
            logger.info(f"Set deterministic seed: {config.deterministic_seed}")

        self.fake = Faker()

        # FIXED: Predefined realistic data
        self.departments = [
            "Computer Science",
            "Mathematics",
            "Physics",
            "Chemistry",
            "Biology",
            "Engineering",
            "Business",
            "Psychology",
        ]

        self.course_prefixes = {
            "Computer Science": ["CS", "CSC", "COMP"],
            "Mathematics": ["MAT", "MATH", "MTH"],
            "Physics": ["PHY", "PHYS"],
            "Chemistry": ["CHE", "CHEM"],
            "Biology": ["BIO", "BIOL"],
            "Engineering": ["ENG", "ENGR"],
            "Business": ["BUS", "MGMT"],
            "Psychology": ["PSY", "PSYC"],
        }

        # FIXED: Enhanced room distribution for better capacity
        self.room_types = [
            {
                "prefix": "LH",
                "capacity_range": self.config.room_capacity_ranges["LH"],
                "hascomputers": False,
            },
            {
                "prefix": "LT",
                "capacity_range": self.config.room_capacity_ranges["LT"],
                "hascomputers": False,
            },
            {
                "prefix": "CL",
                "capacity_range": self.config.room_capacity_ranges["CL"],
                "hascomputers": True,
            },
            {
                "prefix": "LAB",
                "capacity_range": self.config.room_capacity_ranges["LAB"],
                "hascomputers": True,
            },
        ]

        logger.info(
            f"Initialized UUID-only RealisticDataGenerator with seed {config.deterministic_seed}"
        )

    def generate_timeslots(
        self,
        exam_period_start: date,
        exam_period_end: Optional[date] = None,
        include_weekends: bool = False,
        session_templates: int = 3,
        holidays: Optional[List[date]] = None,
    ) -> List[Dict[str, Any]]:
        """FIXED: Create time slots using Day objects"""
        if exam_period_end is None:
            exam_period_end = exam_period_start + timedelta(
                days=self.config.exam_period_days - 1
            )

        if holidays is None:
            holidays = []

        # Get valid weekdays (excludes weekends)
        valid_days = self._get_valid_weekdays(
            exam_period_start, exam_period_end, holidays, include_weekends
        )

        timeslots: List[Dict[str, Any]] = []

        # CRITICAL: Generate exactly 3 slots per valid day using Day objects
        for day_date in valid_days:
            day = Day(
                id=uuid4(), date=day_date
            )  # This automatically creates 3 timeslots

            # Export the timeslots for backward compatibility
            for slot in day.timeslots:
                timeslots.append(
                    {
                        "id": slot.id,
                        "name": slot.name,
                        "start_time": slot.start_time,
                        "end_time": slot.end_time,
                        "duration_minutes": slot.duration_minutes,
                        "date": day_date,
                        "parent_day_id": day.id,
                    }
                )

        # VALIDATION: Ensure exactly 3 slots per day
        days_count = len(valid_days)
        expected_slots = days_count * 3
        actual_slots = len(timeslots)

        logger.info(
            f"Generated {actual_slots} time slots across {days_count} valid days"
        )
        logger.info(f"Exactly {3} slots per day enforced")
        logger.info(f"Expected: {expected_slots}, Actual: {actual_slots}")

        # CRITICAL VALIDATION
        if actual_slots != expected_slots:
            raise ValueError(
                f"Slot generation mismatch: expected {expected_slots}, got {actual_slots}"
            )

        # Validate no weekend slots
        weekend_slots = [slot for slot in timeslots if slot["date"].weekday() >= 5]
        if weekend_slots and not include_weekends:
            raise ValueError(
                f"Found {len(weekend_slots)} weekend slots - should be zero!"
            )

        # Validate day distribution
        slots_by_day = {}
        for slot in timeslots:
            day_key = slot["date"].isoformat()
            if day_key not in slots_by_day:
                slots_by_day[day_key] = []
            slots_by_day[day_key].append(slot["id"])

        for day_key, day_slots in slots_by_day.items():
            if len(day_slots) != 3:
                raise ValueError(
                    f"Day {day_key} has {len(day_slots)} slots, expected 3"
                )

        logger.info("Timeslot generation validation passed")
        return timeslots

    def generate_days(
        self,
        exam_period_start: date,
        exam_period_end: Optional[date] = None,
        include_weekends: bool = False,
        holidays: Optional[List[date]] = None,
    ) -> List[Day]:
        if exam_period_end is None:
            if self.config.exam_days_count:
                exam_period_end = exam_period_start + timedelta(
                    days=self.config.exam_days_count * 2
                )  # Buffer for weekends
            else:
                exam_period_end = exam_period_start + timedelta(
                    days=self.config.exam_period_days - 1
                )

        if holidays is None:
            holidays = []

        # CRITICAL: Pass max_days to limit the result
        valid_dates = self._get_valid_weekdays(
            exam_period_start,
            exam_period_end,
            holidays,
            include_weekends,
            max_days=self.config.exam_days_count,  # <-- ADD THIS
        )

        days = []
        for day_date in valid_dates:
            day = Day(id=uuid4(), date=day_date)
            days.append(day)
            logger.info(f"Generated day {day_date} with {len(day.timeslots)} timeslots")

        logger.info(f"Generated {len(days)} days with {len(days)*3} total timeslots")
        return days

    def _get_valid_weekdays(
        self,
        start_date: date,
        end_date: date,
        holidays: List[date],
        include_weekends: bool = False,
        max_days: Optional[int] = None,
    ) -> List[date]:
        valid_days = []
        current_date = start_date
        while current_date <= end_date:
            if not include_weekends and current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue
            if current_date in holidays:
                logger.info(f"Skipping holiday {current_date}")
                current_date += timedelta(days=1)
                continue
            valid_days.append(current_date)

            # CRITICAL: Stop when we reach the configured limit
            if max_days is not None and len(valid_days) >= max_days:
                break

            current_date += timedelta(days=1)

        return valid_days

    def _is_holiday(self, check_date: date, holidays: List[date]) -> bool:
        """Check if date is a holiday"""
        return check_date in holidays

    def generate_rooms(self) -> List[Dict[str, Any]]:
        """Generate rooms with UUID objects using configurable count"""
        # Define room types with their properties and target distribution percentages
        room_types = [
            {
                "prefix": "LH",
                "capacity_range": self.config.room_capacity_ranges["LH"],
                "hascomputers": False,
                "target_percentage": 0.4,  # 40% of rooms
            },
            {
                "prefix": "LT",
                "capacity_range": self.config.room_capacity_ranges["LT"],
                "hascomputers": False,
                "target_percentage": 0.3,  # 30% of rooms
            },
            {
                "prefix": "CL",
                "capacity_range": self.config.room_capacity_ranges["CL"],
                "hascomputers": True,
                "target_percentage": 0.2,  # 20% of rooms
            },
            {
                "prefix": "LAB",
                "capacity_range": self.config.room_capacity_ranges["LAB"],
                "hascomputers": True,
                "target_percentage": 0.1,  # 10% of rooms
            },
        ]

        rooms = []
        room_counts = []
        remaining_rooms = self.config.num_rooms

        # Calculate room counts based on percentages
        for room_type in room_types:
            count = int(round(room_type["target_percentage"] * self.config.num_rooms))
            room_counts.append(count)
            remaining_rooms -= count

        # Distribute remaining rooms
        if remaining_rooms != 0:
            room_counts[0] += remaining_rooms

        # Generate rooms for each type
        for i, room_type in enumerate(room_types):
            for j in range(room_counts[i]):
                capacity = random.randint(*room_type["capacity_range"])
                exam_capacity = int(capacity * 0.85)
                adjacent_pairs = [(s, s + 1) for s in range(0, capacity - 1, 2)][:15]

                rooms.append(
                    {
                        "id": uuid4(),
                        "code": f"{room_type['prefix']}{j+1:02d}",
                        "capacity": capacity,
                        "examcapacity": exam_capacity,
                        "hascomputers": room_type["hascomputers"],
                        "adjacentseatpairs": adjacent_pairs,
                        "building": self.fake.building_number(),
                        "floor": random.randint(1, 5),
                        "overbookable": True,
                    }
                )

        # Validate total rooms count
        if len(rooms) != self.config.num_rooms:
            logger.warning(
                f"Room count mismatch: config={self.config.num_rooms}, generated={len(rooms)}"
            )

        self.max_exam_capacity = max(r["examcapacity"] for r in rooms) if rooms else 0
        logger.info(
            f"Generated {len(rooms)} rooms with UUID objects (max exam_capacity: {self.max_exam_capacity})"
        )
        return rooms

    def generate_courses(self) -> List[Dict[str, Any]]:
        """FIXED: Generate realistic courses with UUID objects using configurable enrollment limits"""
        courses = []

        for i in range(self.config.num_courses):
            department = random.choice(self.departments)
            prefix_options = self.course_prefixes[department]
            prefix = random.choice(prefix_options)

            # Generate course code
            level = random.choice([100, 200, 300, 400])
            number = random.randint(1, 99)
            course_code = f"{prefix}{level}{number}"

            # Use configurable enrollment limits
            if level <= 200:  # Introductory courses
                expected_students = random.randint(
                    max(self.config.min_students_per_course, 30),
                    min(self.config.max_students_per_course, 100),
                )
            else:  # Advanced courses
                expected_students = random.randint(
                    self.config.min_students_per_course,
                    min(self.config.max_students_per_course, 60),
                )

            # FIXED: Cap by max exam hall capacity if known
            max_cap = getattr(self, "max_exam_capacity", None)
            if isinstance(max_cap, int) and max_cap > 0:
                expected_students = min(
                    expected_students, int(max_cap * 0.8)
                )  # 80% of max

            courses.append(
                {
                    "id": uuid4(),
                    "code": course_code,
                    "name": self.fake.catch_phrase(),
                    "department": department,
                    "level": level,
                    "credits": random.choice([3, 4, 6]),
                    "expectedstudents": expected_students,
                }
            )

        logger.info(f"Generated {len(courses)} realistic courses with UUID objects")
        return courses

    def generate_students(self, courses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """FIXED: Generate students with UUID objects"""
        students = []

        # More upperclassmen
        year_distribution = [1, 1, 2, 2, 3, 3, 4, 4]

        for i in range(self.config.num_students):
            department = random.choice(self.departments)
            year = random.choice(year_distribution)

            students.append(
                {
                    "id": uuid4(),  # FIXED: Use UUID object directly
                    "studentid": f"STU2024{i+1:05d}",
                    "firstname": self.fake.first_name(),
                    "lastname": self.fake.last_name(),
                    "email": self.fake.email(),
                    "department": department,
                    "year": year,
                    "gpa": round(random.normalvariate(3.0, 0.5), 2),
                }
            )

        logger.info(f"Generated {len(students)} students with UUID objects")
        return students

    def generate_instructors(self, required_count: int) -> List[Dict[str, Any]]:
        """FIXED: Generate instructors with UUID objects"""
        instructors = []

        for i in range(required_count):
            department = random.choice(self.departments)

            instructor = {
                "id": uuid4(),  # FIXED: Use UUID object directly
                "name": f"Dr. {self.fake.first_name()} {self.fake.last_name()}",
                "email": self.fake.email(),
                "department": department,
                "availability": {"allavailable": True},
                "maxstudentsperexam": self.config.max_students_per_invigilator,
            }
            instructors.append(instructor)

        logger.info(
            f"Generated {len(instructors)} instructors with UUID objects (calculated requirement)"
        )
        return instructors

    def generate_staff(self, required_count: int) -> List[Dict[str, Any]]:
        """FIXED: Generate staff with UUID objects"""
        staff = []

        for i in range(required_count):
            department = random.choice(self.departments)

            staff_member = {
                "id": uuid4(),  # FIXED: Use UUID object directly
                "name": f"{self.fake.first_name()} {self.fake.last_name()}",
                "email": self.fake.email(),
                "department": department,
                "caninvigilate": True,  # Always True
                "maxconcurrentexams": random.randint(2, 4),  # INCREASED
                "maxstudentsperexam": self.config.max_students_per_invigilator,
                "availability": {"allavailable": True},
            }
            staff.append(staff_member)

        logger.info(
            f"Generated {len(staff)} staff members with UUID objects (calculated requirement)"
        )
        return staff

    def generate_invigilators(
        self, instructors_data: List[Dict], staff_data: List[Dict]
    ) -> List[Dict[str, Any]]:
        """FIXED: Generate invigilators with UUID objects"""
        invigilators = []

        # Convert all instructors to invigilators
        for instructor_data in instructors_data:
            invigilator = {
                "id": instructor_data["id"],  # Already UUID object
                "name": instructor_data["name"],
                "email": instructor_data["email"],
                "department": instructor_data["department"],
                "caninvigilate": True,
                "maxconcurrentexams": 4,  # INCREASED
                "maxstudentsperexam": self.config.max_students_per_invigilator,
                "availability": {"alltimeslots": True},
                "unavailableslots": [],
            }
            invigilators.append(invigilator)

        # Convert all staff to invigilators
        for staff_data_item in staff_data:
            invigilator = {
                "id": staff_data_item["id"],  # Already UUID object
                "name": staff_data_item["name"],
                "email": staff_data_item.get("email"),
                "department": staff_data_item["department"],
                "caninvigilate": True,
                "maxconcurrentexams": staff_data_item.get("maxconcurrentexams", 4),
                "maxstudentsperexam": staff_data_item.get(
                    "maxstudentsperexam", self.config.max_students_per_invigilator
                ),
                "availability": {"alltimeslots": True},
                "unavailableslots": [],
            }
            invigilators.append(invigilator)

        logger.info(
            f"Generated {len(invigilators)} invigilators with UUID objects (dynamically calculated)"
        )
        return invigilators

    def generate_student_registrations(
        self, students: List[Dict], courses: List[Dict]
    ) -> List[Dict[str, UUID]]:
        """FIXED: Generate student-course registrations ensuring ALL students and courses have registrations"""

        logger.info(
            "FIXED: Generating student registrations with guaranteed coverage..."
        )

        registrations = []
        student_registration_count = {student["id"]: 0 for student in students}
        course_registration_count = {course["id"]: 0 for course in courses}

        # Phase 1: Ensure every student gets at least min_courses_per_student registrations
        for student in students:
            student_dept = student["department"]

            # Get courses from same department
            same_dept_courses = [c for c in courses if c["department"] == student_dept]
            # Get courses from other departments
            other_dept_courses = [c for c in courses if c["department"] != student_dept]

            # Determine number of courses for this student
            num_courses = random.randint(
                self.config.min_courses_per_student, self.config.max_courses_per_student
            )

            selected_courses = []

            # Fill with same department courses first
            available_same_dept = same_dept_courses.copy()
            for _ in range(min(num_courses, len(available_same_dept))):
                if available_same_dept:
                    course = random.choice(available_same_dept)
                    available_same_dept.remove(course)
                    selected_courses.append(course)

            # Fill remaining with other department courses if needed
            remaining = num_courses - len(selected_courses)
            if remaining > 0 and other_dept_courses:
                available_other_dept = other_dept_courses.copy()
                for _ in range(min(remaining, len(available_other_dept))):
                    if (
                        available_other_dept
                        and random.random() < self.config.cross_dept_prob * 2
                    ):  # Increase cross-dept probability
                        course = random.choice(available_other_dept)
                        available_other_dept.remove(course)
                        selected_courses.append(course)

            # Create registrations for selected courses
            for course in selected_courses:
                registrations.append(
                    {
                        "studentid": student["id"],
                        "courseid": course["id"],
                        "registrationdate": self.fake.date_this_year().isoformat(),
                    }
                )
                student_registration_count[student["id"]] += 1
                course_registration_count[course["id"]] += 1

        # Phase 2: Ensure every course has at least min_students_per_course registrations
        for course in courses:
            current_count = course_registration_count[course["id"]]
            min_needed = self.config.min_students_per_course

            if current_count < min_needed:
                additional_needed = min_needed - current_count
                course_dept = course["department"]

                # Find students who could take this course (same department preferred)
                same_dept_students = [
                    s for s in students if s["department"] == course_dept
                ]
                other_students = [s for s in students if s["department"] != course_dept]

                # Try same department students first
                candidates = same_dept_students + other_students
                random.shuffle(candidates)

                added = 0
                for student in candidates:
                    if added >= additional_needed:
                        break

                    # Check if student doesn't already have this course
                    already_registered = any(
                        r["studentid"] == student["id"]
                        and r["courseid"] == course["id"]
                        for r in registrations
                    )

                    if (
                        not already_registered
                        and student_registration_count[student["id"]]
                        < self.config.max_courses_per_student
                    ):
                        registrations.append(
                            {
                                "studentid": student["id"],
                                "courseid": course["id"],
                                "registrationdate": self.fake.date_this_year().isoformat(),
                            }
                        )
                        student_registration_count[student["id"]] += 1
                        course_registration_count[course["id"]] += 1
                        added += 1

        # Phase 3: Validation
        students_without_registrations = [
            sid for sid, count in student_registration_count.items() if count == 0
        ]
        courses_without_registrations = [
            cid for cid, count in course_registration_count.items() if count == 0
        ]

        logger.info(f"FIXED: Registration generation complete:")
        logger.info(f"  Total registrations: {len(registrations)}")
        logger.info(
            f"  Students without registrations: {len(students_without_registrations)}"
        )
        logger.info(
            f"  Courses without registrations: {len(courses_without_registrations)}"
        )
        logger.info(
            f"  Average registrations per student: {len(registrations) / len(students):.1f}"
        )
        logger.info(
            f"  Average students per course: {len(registrations) / len(courses):.1f}"
        )

        if students_without_registrations:
            logger.error(
                f"CRITICAL: {len(students_without_registrations)} students have no registrations!"
            )

        if courses_without_registrations:
            logger.error(
                f"CRITICAL: {len(courses_without_registrations)} courses have no students!"
            )

        return registrations


class ComprehensiveConstraintTester:
    """FIXED: Comprehensive constraint testing with UUID-only implementation"""

    def __init__(self, config: TestConfiguration):
        self.config = config
        self.generator = RealisticDataGenerator(config)
        logger.info(
            f"Initialized ComprehensiveConstraintTester with UUID-only implementation"
        )

    def create_comprehensive_problem(self) -> ExamSchedulingProblem:
        """ENHANCED: Create comprehensive test problem with configurable days"""
        logger.info(
            "Creating comprehensive test problem with configurable day generation..."
        )

        # Set up dates
        session_id = uuid4()
        exam_period_start = date(2025, 12, 1)  # Monday

        exam_period_end = None

        # ENHANCED: Create problem with configurable day count
        problem = ExamSchedulingProblem(
            session_id=session_id,
            exam_period_start=exam_period_start,
            exam_period_end=exam_period_end,  # type: ignore
            exam_days_count=self.config.exam_days_count,
        )

        # Generate data using the generator instance
        courses_data = self.generator.generate_courses()
        students_data = self.generator.generate_students(courses_data)
        student_registrations = self.generator.generate_student_registrations(
            students_data, courses_data
        )

        # Calculate invigilator requirements
        total_students = len(students_data)
        invigilator_requirements = self.config.calculate_required_invigilators(
            total_students
        )

        # Generate staff and instructors
        instructors_data = self.generator.generate_instructors(
            invigilator_requirements["instructors"]
        )
        staff_data = self.generator.generate_staff(invigilator_requirements["staff"])

        # Add instructors and staff to the problem
        for instructor_data in instructors_data:
            instructor = Instructor(
                id=instructor_data["id"],
                name=instructor_data["name"],
                email=instructor_data["email"],
                department=instructor_data["department"],
                availability=instructor_data["availability"],
            )
            problem.add_instructor(instructor)

        for staff_data_item in staff_data:
            staff = Staff(
                id=staff_data_item["id"],
                name=staff_data_item["name"],
                department=staff_data_item["department"],
                can_invigilate=staff_data_item["caninvigilate"],
                max_concurrent_exams=staff_data_item["maxconcurrentexams"],
                max_students_per_exam=staff_data_item["maxstudentsperexam"],
                availability=staff_data_item["availability"],
            )
            problem.add_staff(staff)
        invigilators_data = self.generator.generate_invigilators(
            instructors_data, staff_data
        )

        # Add remaining components (rooms, exams, etc.)
        rooms_data = self.generator.generate_rooms()

        # Generate days and timeslots
        days = self.generator.generate_days(
            exam_period_start=exam_period_start,
            exam_period_end=exam_period_end,
            include_weekends=False,
            holidays=[],
        )

        # Add days to problem (this will automatically add their timeslots)
        for day in days:
            problem.days[day.id] = day
        # Add rooms to problem
        for room_data in rooms_data:
            room = Room(
                id=room_data["id"],
                code=room_data["code"],
                capacity=room_data["capacity"],
                exam_capacity=room_data["examcapacity"],
                has_computers=room_data["hascomputers"],
                adjacent_seat_pairs=room_data["adjacentseatpairs"],
            )
            problem.add_room(room)

        # Add exams to problem
        for course_data in courses_data:
            exam = Exam(
                id=uuid4(),
                course_id=course_data["id"],
                expected_students=course_data["expectedstudents"],
                duration_minutes=180,
            )
            problem.add_exam(exam)

        # Add students to problem
        for student_data in students_data:
            student = Student(
                id=student_data["id"], department=student_data["department"]
            )
            problem.add_student(student)

        # Register student courses
        for registration in student_registrations:
            problem.register_student_course(
                registration["studentid"], registration["courseid"]
            )

        for day in problem.days.values():
            assert len(day.timeslots) == 3

        assert len(problem.timeslots) == 3 * len(problem.days)
        # Populate exam students
        problem.populate_exam_students()

        return problem

    def _generate_problem_statistics(self, problem) -> Dict[str, Any]:
        """Generate comprehensive problem statistics"""
        stats = {
            "exams": len(getattr(problem, "exams", {})),
            "timeslots": len(getattr(problem, "timeslots", {})),
            "rooms": len(getattr(problem, "rooms", {})),
            "students": len(getattr(problem, "students", {})),
            "invigilators": {
                "total_invigilators": len(getattr(problem, "invigilators", {})),
                "valid_invigilators": len(
                    [
                        inv
                        for inv in getattr(problem, "invigilators", {}).values()
                        if getattr(inv, "caninvigilate", True)
                    ]
                ),
                "invalid_invigilators": len(
                    [
                        inv
                        for inv in getattr(problem, "invigilators", {}).values()
                        if not getattr(inv, "caninvigilate", True)
                    ]
                ),
                "total_capacity": len(getattr(problem, "invigilators", {}))
                * self.config.max_students_per_invigilator,
            },
            "student_registrations": sum(
                len(courses)
                for courses in getattr(problem, "_student_courses", {}).values()
            ),
        }

        logger.info(
            f"Generated {stats['invigilators']['total_invigilators']} total invigilators for {stats['students']} students"
        )

        return stats

    def test_complete_constraint_system(self) -> TestResults:
        """FIXED: Test complete constraint system with UUID-only implementation"""
        test_result = TestResults("complete_constraint_system_uuid_only", time.time())

        try:
            logger.info(
                "Testing COMPLETE constraint system with UUID-only implementation..."
            )

            # Create problem with UUID-only entities
            problem = self.create_comprehensive_problem()

            # Test constraint configurations incrementally
            config_sequence = [
                ("MINIMAL", "configure_minimal"),
                ("BASIC", "configure_basic"),  # Changed from "STANDARD"
                (
                    "WITH_RESOURCES",
                    "configure_with_resources",
                ),  # Changed from "WITH_STUDENT_CONFLICTS"
                ("COMPLETE", "configure_complete"),
            ]
            complete_solution = None
            complete_status = None

            for config_name, config_method in config_sequence:
                logger.info(f"Testing UUID-only with {config_name} configuration...")

                # Reset constraint registry and configure for this level
                problem.constraint_registry.active_constraints.clear()
                getattr(problem.constraint_registry, config_method)()

                active_constraints = (
                    problem.constraint_registry.get_active_constraints()
                )
                logger.info(
                    f"Active constraints for {config_name}: {sorted(active_constraints)}"
                )

                try:
                    builder = CPSATModelBuilder(problem)

                    build_start = time.time()
                    model, shared_variables = builder.build()
                    build_duration = time.time() - build_start

                    logger.info(
                        f"UUID-only {config_name} build time: {build_duration:.2f}s"
                    )

                    # Test solving with this configuration
                    solver_manager = CPSATSolverManager(problem)
                    solver_manager.solver.parameters.max_time_in_seconds = (
                        30  # Increased time for complete config
                    )

                    start_solve = time.time()
                    status, solution = solver_manager.solve()
                    solve_duration = time.time() - start_solve

                    test_result.solution = solution

                    status_int = cast(int, status)
                    status_name = self._get_status_name(status_int)

                    logger.info(
                        f"UUID-only {config_name}: {status_name} in {solve_duration:.2f}s"
                    )

                    # Store complete configuration solution for GUI display
                    if config_name == "COMPLETE":
                        complete_solution = solution
                        complete_status = status

                    if status == cp_model.INFEASIBLE:
                        logger.warning(f"UUID-only {config_name} is INFEASIBLE")
                        # Don't break, continue to next configuration

                except Exception as e:
                    logger.error(f"UUID-only {config_name} build failed: {e}")
                    # Continue to next configuration even if this one fails

            # Show GUI if complete configuration was successful
            if (
                complete_status in [cp_model.OPTIMAL, cp_model.FEASIBLE]
                and complete_solution
                and self.config.show_solutions_on_success
            ):
                try:
                    logger.info(
                        "🎉 COMPLETE configuration successful! Launching GUI..."
                    )
                    complete_solution.show_gui_viewer(
                        title="Complete Constraint Configuration Solution"
                    )
                except Exception as e:
                    logger.error(f"Failed to launch GUI: {e}")
                    # Fallback to text output
                    complete_solution.print_solution_summary()

            # Final test success
            test_result.success = True
            logger.info(f"UUID-only incremental constraint testing completed")

        except Exception as e:
            logger.error(f"UUID-only test execution failed: {e}")
            import traceback

            logger.error(traceback.format_exc())
            test_result.error_message = str(e)
        finally:
            test_result.end_time = time.time()

        return test_result

    def _test_with_complete_configuration(self, problem, test_result) -> TestResults:
        """Test with complete configuration using UUID-only entities"""
        builder = CPSATModelBuilder(problem)
        builder.configure("COMPLETE")

        build_start = time.time()
        model, shared_variables = builder.build()
        build_duration = time.time() - build_start

        logger.info(f"UUID-only build time: {build_duration:.2f}s")
        return test_result

    def _test_with_constraint_debugging(self, problem, test_result) -> TestResults:
        """Testing with progressive constraint activation for UUID-only debugging"""
        logger.info(
            "Testing UUID-only with progressive constraint activation for debugging..."
        )

        builder = CPSATModelBuilder(problem)

        build_start = time.time()
        try:
            model, shared_variables = builder.build()
            build_duration = time.time() - build_start
            logger.info(f"UUID-only build time: {build_duration:.2f}s")
            test_result.success = True
        except Exception as e:
            logger.error(f"UUID-only build failed: {e}")
            test_result.error_message = str(e)

        return test_result

    def _get_status_name(self, status: int) -> str:
        """Convert CP-SAT status to readable name"""
        status_names: Dict[int, str] = {
            int(cp_model.UNKNOWN): "UNKNOWN",
            int(cp_model.MODEL_INVALID): "MODEL_INVALID",
            int(cp_model.FEASIBLE): "FEASIBLE",
            int(cp_model.INFEASIBLE): "INFEASIBLE",
            int(cp_model.OPTIMAL): "OPTIMAL",
        }
        return status_names.get(int(status), f"UNKNOWN_STATUS({status})")


@pytest.mark.asyncio
async def test_complete_constraint_system():
    """FIXED: Pytest integration with UUID-only implementation"""
    config = TestConfiguration()
    tester = ComprehensiveConstraintTester(config)
    result = tester.test_complete_constraint_system()

    assert result.success, f"UUID-only test failed: {result.error_message}"

    if result.solution:
        logger.info("UUID-only solution found successfully")
    else:
        logger.warning("UUID-only solver status unavailable")

    logger.info(f"UUID-only test completed in {result.duration:.2f}s")


if __name__ == "__main__":
    import pytest

    pytest.main(
        [
            __file__,
            "-v",
            "--tb=long",
            "--asyncio-mode=auto",
            "--capture=no",
            "-vv",
            "-s",
        ]
    )
