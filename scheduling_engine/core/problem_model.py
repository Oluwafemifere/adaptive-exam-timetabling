# Enhanced Problem Model for CP-SAT integration with UUID-only implementation
# MODIFIED: Day-centric timeslot architecture

"""
MODIFIED Problem Model - Day-centric timeslot architecture

Critical Changes:
1. Added Day class with exactly 3 timeslots per day
2. Removed independent timeslot management
3. Timeslots are now managed through Day objects
4. Added validation to ensure exactly 3 timeslots per day
"""

from __future__ import annotations
import math
from typing import Dict, List, Set, Optional, Any, TYPE_CHECKING, Tuple
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from datetime import datetime, time, date, timedelta
from enum import Enum
import logging
from collections import defaultdict
import uuid
from pydantic import Field
from .constraint_types import ConstraintType
from .solution import TimetableSolution, ExamAssignment, SolutionStatus
from .constraint_registry import ConstraintRegistry

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from .constraint_registry import ConstraintRegistry
    from backend.app.services.scheduling.data_preparation_service import (
        DataPreparationService,
        PreparedDataset,
    )

logger = logging.getLogger(__name__)


class ExamType(Enum):
    REGULAR = "regular"
    MAKEUP = "makeup"
    CARRYOVER = "carryover"
    SUPPLEMENTARY = "supplementary"


@dataclass
class Timeslot:
    id: UUID
    parent_day_id: UUID
    name: str
    start_time: time
    end_time: time
    duration_minutes: int


@dataclass
class Day:
    id: UUID
    date: date
    timeslots: List[Timeslot] = field(default_factory=list)

    def __post_init__(self):
        templates = [
            ("Morning", time(9, 0), time(12, 0)),
            ("Afternoon", time(14, 0), time(17, 0)),
            ("Evening", time(18, 0), time(21, 0)),
        ]
        self.timeslots.clear()
        for name, start, end in templates:
            slot = Timeslot(
                id=uuid4(),
                parent_day_id=self.id,
                name=name,
                start_time=start,
                end_time=end,
                duration_minutes=(end.hour - start.hour) * 60,
            )
            self.timeslots.append(slot)

        # Validation: Ensure exactly 3 timeslots
        if len(self.timeslots) != 3:
            raise ValueError(
                f"Day {self.id} must have exactly 3 timeslots, got {len(self.timeslots)}"
            )


@dataclass
class Room:
    id: UUID
    code: str
    capacity: int
    exam_capacity: int
    has_computers: bool = False
    adjacent_seat_pairs: List[Tuple[int, int]] = field(default_factory=list)

    @property
    def overbookable(self) -> bool:
        return getattr(self, "_overbookable", False)

    @property
    def seat_indices(self) -> List[int]:
        return list(range(self.capacity))

    @classmethod
    def from_backend_data(cls, data: Dict[str, Any]) -> "Room":
        # Preserve UUID type
        id_value = data["id"]
        if isinstance(id_value, UUID):
            uuid_obj = id_value
        else:
            uuid_obj = UUID(str(id_value))

        return cls(
            id=uuid_obj,
            code=data.get("code", ""),
            capacity=int(data.get("capacity", 0)),
            exam_capacity=int(data.get("exam_capacity", data.get("capacity", 0))),
            has_computers=bool(data.get("has_computers", False)),
            adjacent_seat_pairs=data.get("adjacent_seat_pairs", []),
        )


@dataclass
class Student:
    id: UUID
    department: Optional[str] = None
    registered_courses: Set[UUID] = field(default_factory=set)

    @classmethod
    def from_backend_data(cls, data: Dict[str, Any]) -> "Student":
        # Preserve UUID type
        id_value = data["id"]
        if isinstance(id_value, UUID):
            uuid_obj = id_value
        else:
            uuid_obj = UUID(str(id_value))

        s = cls(id=uuid_obj, department=data.get("department"))
        return s


@dataclass
class Instructor:
    id: UUID
    name: str
    email: Optional[str] = None
    department: Optional[str] = None
    availability: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Staff:
    def __init__(
        self,
        id: Optional[UUID] = None,
        name: Optional[str] = None,
        department: Optional[str] = None,
        can_invigilate: bool = True,
        max_concurrent_exams: int = 1,
        **kwargs,
    ):
        self.id = id or uuid4()
        self.name = name
        self.department = department
        self.can_invigilate = can_invigilate
        self.max_concurrent_exams = max_concurrent_exams

        # Handle any additional attributes from kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)


@dataclass
class Invigilator:
    """FIXED: Enhanced Invigilator dataclass with validation"""

    id: UUID
    name: str
    email: Optional[str] = None
    department: Optional[str] = None
    can_invigilate: bool = True
    max_concurrent_exams: int = 1
    max_students_per_exam: int = 50
    availability: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """FIXED: Validate invigilator data on creation"""
        if not self.name:
            logger.warning(f"Invigilator {self.id} has no name")

        if self.max_concurrent_exams < 1:
            raise ValueError(f"Invigilator {self.id} max_concurrent_exams must be >= 1")

        if self.max_students_per_exam < 1:
            raise ValueError(
                f"Invigilator {self.id} max_students_per_exam must be >= 1"
            )

    @classmethod
    def from_staff(cls, staff: Staff) -> "Invigilator":
        """Create an Invigilator from a Staff member"""
        return cls(
            id=staff.id,
            name=getattr(staff, "name", f"Staff_{staff.id}"),
            email=getattr(staff, "email", None),
            department=getattr(staff, "department", None),
            can_invigilate=getattr(staff, "can_invigilate", True),
            max_concurrent_exams=getattr(staff, "max_concurrent_exams", 1),
            max_students_per_exam=getattr(staff, "max_students_per_exam", 50),
            availability=getattr(staff, "availability", {}),
        )

    @classmethod
    def from_instructor(cls, instructor: Instructor) -> "Invigilator":
        """Create an Invigilator from an Instructor"""
        return cls(
            id=instructor.id,
            name=instructor.name or f"Instructor_{instructor.id}",
            email=instructor.email,
            department=instructor.department,
            can_invigilate=True,  # Instructors can always invigilate
            max_concurrent_exams=1,
            max_students_per_exam=30,
            availability=instructor.availability,
        )


@dataclass
class Exam:
    id: UUID
    course_id: UUID
    duration_minutes: int
    expected_students: int
    is_practical: bool = False
    morning_only: bool = False
    prerequisite_exams: Set[UUID] = field(default_factory=set)

    @property
    def enrollment(self) -> int:
        return self.expected_students

    @property
    def students(self) -> Set[UUID]:
        return getattr(self, "_students", set())

    @property
    def duration(self) -> int:
        """Alias for duration_minutes to maintain compatibility"""
        return self.duration_minutes

    @property
    def instructor_id(self) -> Optional[UUID]:
        return getattr(self, "_instructor_id", None)

    @instructor_id.setter
    def instructor_id(self, value: Optional[UUID]):
        self._instructor_id = value

    @property
    def allowed_rooms(self) -> Set[UUID]:
        return getattr(self, "_allowed_rooms", set())

    @allowed_rooms.setter
    def allowed_rooms(self, value: Set[UUID]):
        self._allowed_rooms = value

    def set_students(self, student_ids: Set[UUID]):
        self._students = student_ids

    def add_student(self, student_id: UUID):
        if not hasattr(self, "_students"):
            self._students = set()
        self._students.add(student_id)

    @classmethod
    def from_backend_data(cls, data: Dict[str, Any]) -> "Exam":
        # Preserve UUID types
        id_value = data["id"]
        course_id_value = data["course_id"]

        if isinstance(id_value, UUID):
            uuid_obj = id_value
        else:
            uuid_obj = UUID(str(id_value))

        if isinstance(course_id_value, UUID):
            course_uuid_obj = course_id_value
        else:
            course_uuid_obj = UUID(str(course_id_value))

        return cls(
            id=uuid_obj,
            course_id=course_uuid_obj,
            duration_minutes=int(data.get("duration_minutes", 180)),
            expected_students=int(data.get("expected_students", 0)),
            is_practical=bool(data.get("is_practical", False)),
            morning_only=bool(data.get("morning_only", False)),
        )


class ExamSchedulingProblem:
    """ENHANCED: Problem model with configurable Day-centric timeslot architecture"""

    def __init__(
        self,
        session_id: UUID,
        exam_period_start: date,
        exam_period_end: date,
        db_session: Optional["AsyncSession"] = None,
        deterministic_seed: Optional[int] = None,
        exam_days_count: Optional[
            int
        ] = None,  # ENHANCED: New parameter for configurable days
    ):
        """ENHANCED: Day-centric initialization with configurable day count"""
        self.id = uuid4()
        self.session_id = session_id
        self.exam_period_start = exam_period_start
        self.exam_period_end = exam_period_end
        self.exam_days_count = exam_days_count  # ENHANCED: Store configured day count

        self.holidays: Set[date] = set()  # Changed to set for faster lookups

        self.days: Dict[UUID, Day] = {}
        self.deterministic_seed = deterministic_seed

        # Entities with UUID keys
        self.exams: Dict[UUID, Exam] = {}
        self.rooms: Dict[UUID, Room] = {}
        self.students: Dict[UUID, Student] = {}

        # ENHANCED: Course registrations with UUID keys
        self._student_courses: Dict[UUID, Set[UUID]] = defaultdict(set)
        self._course_students: Dict[UUID, Set[UUID]] = defaultdict(set)

        # Constraint registry - initialize with global definitions
        self.constraint_registry = ConstraintRegistry()
        self.constraint_registry.configure_complete()
        self._initialize_constraint_registry()
        self.active_constraints: List[str] = []

        # Configuration parameters
        self.min_gap_slots = 1
        self.max_exams_per_day = 3
        self.overbook_rate = 0.1

        # ENHANCED: Enhanced invigilator management with UUID keys
        self.instructors: Dict[UUID, Instructor] = {}
        self._invigilators: Dict[UUID, Invigilator] = {}
        self.staff: Dict[UUID, Staff] = {}

        # Scheduling parameters
        self.timeslots_per_day = 3
        self.max_concurrent_exams = 10
        self.min_gap_minutes = 60
        self.preferred_gap_slots = 2
        self.min_invigilators_per_room = 1
        self.max_students_per_invigilator = 50
        self.allow_back_to_back_exams = False
        self.require_same_day_practicals = True

        # Backend initialization
        self.db_session = db_session
        self.data_prep_service: Optional["DataPreparationService"] = None
        if db_session:
            try:
                from backend.app.services.scheduling.data_preparation_service import (
                    DataPreparationService,
                )

                self.data_prep_service = DataPreparationService(db_session)
            except ImportError:
                logger.warning(
                    "DataPreparationService not available, using test data only"
                )

        # Precompute timeslot cache and mapping
        self._timeslots_cache: Optional[Dict[UUID, Timeslot]] = None
        self._timeslot_to_day: Optional[Dict[UUID, Day]] = None

    def configure_exam_days(self, days_count: int) -> None:
        """ENHANCED: Configure the number of exam days and regenerate day structure"""
        if days_count <= 0:
            raise ValueError(f"days_count must be positive, got {days_count}")

        logger.info(f"Configuring exam schedule for {days_count} days")
        self.exam_days_count = days_count

        # Regenerate days with new count
        self.days = self._generate_days_with_timeslots()

        logger.info(
            f"Generated {len(self.days)} days with {len(self.timeslots)} total timeslots"
        )

        # Clear cache to force recomputation
        self._timeslots_cache = None
        self._timeslot_to_day = None

    def _generate_days_with_timeslots(self) -> Dict[UUID, Day]:
        """CRITICAL FIX: Generate days with consistent count and logging"""
        days = {}
        current_date = self.exam_period_start
        days_generated = 0

        # CRITICAL: Use configurable day count with clear logging
        target_days = (
            self.exam_days_count if self.exam_days_count else 10
        )  # Default to 10

        logger.info(f"CRITICAL: Generating exactly {target_days} days...")

        holidays_set = self.holidays  # Local variable for faster access

        while days_generated < target_days and current_date <= self.exam_period_end:
            # Only weekdays, exclude holidays
            if current_date.weekday() < 5 and current_date not in holidays_set:
                day = Day(id=uuid4(), date=current_date)
                days[day.id] = day
                days_generated += 1
                logger.debug(
                    f"Generated day {days_generated}: {current_date} with 3 timeslots"
                )

            current_date += timedelta(days=1)

            # Safety break
            if (current_date - self.exam_period_start).days > 365:
                break

        # CRITICAL: Log final counts consistently
        total_timeslots = sum(len(day.timeslots) for day in days.values())
        logger.info(
            f"CRITICAL: Generated {len(days)} days with exactly {total_timeslots} timeslots"
        )
        logger.info(
            f"CRITICAL: Days count: {len(days)}, Timeslots count: {total_timeslots}"
        )

        # CRITICAL: Validate exactly 3 timeslots per day
        for day in days.values():
            if len(day.timeslots) != 3:
                raise ValueError(
                    f"Day {day.id} has {len(day.timeslots)} timeslots, expected 3"
                )

        return days

    def generate_days(self):
        """Generate days with exactly 3 timeslots each"""
        if not self.exam_days_count:
            raise ValueError("exam_days_count must be set before generating days")

        self.days = {}
        current_date = self.exam_period_start
        days_generated = 0

        while days_generated < self.exam_days_count:
            if current_date.weekday() < 5:  # Only weekdays
                day = Day(id=uuid4(), date=current_date)
                self.days[day.id] = day
                days_generated += 1
            current_date += timedelta(days=1)

        # Validate we have the expected number of timeslots
        expected_slots = len(self.days) * 3
        actual_slots = len(self.timeslots)
        if actual_slots != expected_slots:
            raise ValueError(
                f"Time slot generation failed: "
                f"expected {expected_slots}, got {actual_slots}"
            )

        # Clear cache to force recomputation
        self._timeslots_cache = None
        self._timeslot_to_day = None

    @property
    def timeslots(self) -> Dict[UUID, Timeslot]:
        """Provide backward compatibility - timeslots accessed through days"""
        if self._timeslots_cache is None:
            self._timeslots_cache = {}
            for day in self.days.values():
                for timeslot in day.timeslots:
                    self._timeslots_cache[timeslot.id] = timeslot
        return self._timeslots_cache

    def get_day_for_timeslot(self, timeslot_id: UUID) -> Optional[Day]:
        """Get the day containing a specific timeslot"""
        if self._timeslot_to_day is None:
            self._timeslot_to_day = {}
            for day in self.days.values():
                for timeslot in day.timeslots:
                    self._timeslot_to_day[timeslot.id] = day

        return self._timeslot_to_day.get(timeslot_id)

    def get_timeslots_for_day(self, day_id: UUID) -> List[Timeslot]:
        """Get all timeslots for a specific day"""
        day = self.days.get(day_id)
        return day.timeslots if day else []

    def validate_timeslot_structure(self) -> Dict[str, Any]:
        """ENHANCED: Validate timeslot structure and day relationships"""
        validation = {"valid": True, "errors": [], "warnings": [], "stats": {}}

        total_days = len(self.days)
        total_timeslots = len(self.timeslots)
        expected_timeslots = total_days * 3

        # Basic count validation
        if total_timeslots != expected_timeslots:
            validation["valid"] = False
            validation["errors"].append(
                f"Timeslot count mismatch: expected {expected_timeslots} (3 per day), got {total_timeslots}"
            )

        # Validate each day has exactly 3 timeslots
        for day_id, day in self.days.items():
            if len(day.timeslots) != 3:
                validation["valid"] = False
                validation["errors"].append(
                    f"Day {day_id} has {len(day.timeslots)} timeslots, expected 3"
                )

        # Validate parent-child relationships
        orphaned_timeslots = 0
        timeslot_to_day_map = self._timeslot_to_day or {}

        for timeslot in self.timeslots.values():
            parent_day = timeslot_to_day_map.get(timeslot.id)
            if not parent_day or timeslot.parent_day_id != parent_day.id:
                orphaned_timeslots += 1

        if orphaned_timeslots > 0:
            validation["valid"] = False
            validation["errors"].append(
                f"Found {orphaned_timeslots} orphaned timeslots"
            )

        # Check for weekends
        weekend_days = [day for day in self.days.values() if day.date.weekday() >= 5]
        if weekend_days:
            validation["warnings"].append(f"Found {len(weekend_days)} weekend days")

        validation["stats"] = {
            "total_days": total_days,
            "total_timeslots": total_timeslots,
            "expected_timeslots": expected_timeslots,
            "weekend_days": len(weekend_days),
            "orphaned_timeslots": orphaned_timeslots,
        }

        return validation

    def _initialize_constraint_registry(self):
        """Initialize constraint registry with global constraint definitions."""
        try:
            # Here you would load constraint definitions from a registry
            logger.info(
                "Initialized problem constraint registry with core-preloaded definitions only"
            )
        except ImportError as e:
            logger.warning(f"Could not initialize constraint registry: {e}")
            logger.info("Constraint registry will start empty")

    def add_holiday(self, holiday_date: date) -> None:
        """Add a holiday date to exclude from scheduling"""
        if holiday_date not in self.holidays:
            self.holidays.add(holiday_date)
            logger.info(f"Added holiday: {holiday_date}")

    def get_valid_exam_days(self) -> List[date]:
        """Get valid exam days (weekdays, excluding holidays)"""
        holidays_set = self.holidays  # Local variable for faster access
        return [day.date for day in self.days.values() if day.date not in holidays_set]

    # REMOVED: validate_timeslot_distribution method - now guaranteed by Day structure

    def add_instructor(self, instructor: Instructor) -> None:
        self.instructors[instructor.id] = instructor

    def add_staff(self, staff: Staff) -> None:
        self.staff[staff.id] = staff

    @property
    def invigilators(self) -> Dict[UUID, Invigilator]:
        """Return combined mapping of all invigilators"""
        combined = {}

        # Add staff who can invigilate
        for staff in self.staff.values():
            if getattr(staff, "can_invigilate", True):
                invigilator = Invigilator.from_staff(staff)
                combined[invigilator.id] = invigilator

        # Add instructors as invigilators
        for instructor in self.instructors.values():
            invigilator = Invigilator.from_instructor(instructor)
            combined[invigilator.id] = invigilator

        return combined

    def validate_invigilator_data(self) -> Dict[str, Any]:
        """FIXED: Comprehensive invigilator data validation"""
        validation_result = {"valid": True, "errors": [], "warnings": [], "stats": {}}

        invigilators = self._invigilators
        if not invigilators:
            validation_result["valid"] = False
            validation_result["errors"].append("No invigilators available")
            return validation_result

        valid_count = 0
        invalid_count = 0
        total_capacity = 0

        for inv_id, invigilator in invigilators.items():
            try:
                # Validate each invigilator
                if not hasattr(invigilator, "id") or not invigilator.id:
                    validation_result["warnings"].append(
                        f"Invigilator missing ID: {inv_id}"
                    )
                    continue

                if not getattr(invigilator, "can_invigilate", True):
                    validation_result["warnings"].append(
                        f"Invigilator {inv_id} cannot invigilate"
                    )
                    continue

                max_students = getattr(invigilator, "max_students_per_exam", 50)
                if max_students <= 0:
                    validation_result["errors"].append(
                        f"Invigilator {inv_id} has invalid max_students_per_exam: {max_students}"
                    )
                    invalid_count += 1
                    continue

                total_capacity += max_students
                valid_count += 1

            except Exception as e:
                validation_result["errors"].append(
                    f"Error validating invigilator {inv_id}: {e}"
                )
                invalid_count += 1

        validation_result["stats"] = {
            "total_invigilators": len(invigilators),
            "valid_invigilators": valid_count,
            "invalid_invigilators": invalid_count,
            "total_capacity": total_capacity,
        }

        # Basic validation
        if valid_count == 0:
            validation_result["valid"] = False
            validation_result["errors"].append("No valid invigilators found")

        return validation_result

    def add_exam(self, exam: Exam) -> None:
        self.exams[exam.id] = exam

    # REMOVED: add_timeslot method - timeslots are now managed through Day objects

    def add_room(self, room: Room) -> None:
        self.rooms[room.id] = room

    def add_student(self, student: Student) -> None:
        self.students[student.id] = student

    def add_invigilator(self, invigilator: Invigilator) -> None:
        """Add an invigilator to the problem"""
        if not hasattr(self, "_invigilators"):
            self._invigilators = {}
        self.invigilators[invigilator.id] = invigilator

    def register_student_course(self, student_id: UUID, course_id: UUID) -> None:
        """FIXED: Register student-course relationship with UUIDs"""
        self._student_courses[student_id].add(course_id)
        self._course_students[course_id].add(student_id)

    def get_timeslot_index(self, timeslot_id: UUID) -> int:
        """Get the index/position of a time slot within its day"""
        day = self.get_day_for_timeslot(timeslot_id)
        if not day:
            return -1

        for i, timeslot in enumerate(day.timeslots):
            if timeslot.id == timeslot_id:
                return i
        return -1

    def get_day_index(self, date_obj: date) -> int:
        """Get the index of a day in the exam period"""
        for i, day in enumerate(self.days.values()):
            if day.date == date_obj:
                return i
        return -1

    def activate_constraint_categories(self, categories: List[str]) -> None:
        """Activate constraint categories for the scheduling problem."""
        logger.info(f"Activating constraint categories: {categories}")

        # Map categories to configuration methods
        if set(categories) == {"CORE"}:
            self.constraint_registry.configure_minimal()
        elif set(categories) == {"CORE", "STUDENT_CONSTRAINTS"}:
            self.constraint_registry.configure_basic()
        elif set(categories) == {"CORE", "STUDENT_CONSTRAINTS", "RESOURCE_CONSTRAINTS"}:
            self.constraint_registry.configure_with_resources()
        elif set(categories) == {
            "CORE",
            "STUDENT_CONSTRAINTS",
            "RESOURCE_CONSTRAINTS",
            "INVIGILATOR_CONSTRAINTS",
        }:
            self.constraint_registry.configure_complete()
        else:
            logger.warning(f"Unknown category combination: {categories}, using minimal")
            self.constraint_registry.configure_minimal()

        # Update active constraints list
        self.active_constraints = list(
            self.constraint_registry.get_active_constraints()
        )
        logger.info(f"Active constraints: {sorted(self.active_constraints)}")

    def ensure_constraints_activated(self) -> None:
        """Ensure at least CORE constraints are activated."""
        active_constraints = self.constraint_registry.get_active_constraints()

        if not active_constraints:
            logger.warning(
                "No constraints activated, activating CORE constraints by default"
            )
            self.constraint_registry._activate_category("CORE")

            active_constraints = self.constraint_registry.get_active_constraints()
            logger.info(f"Default activated constraints: {sorted(active_constraints)}")
        else:
            logger.info(f"Existing active constraints: {sorted(active_constraints)}")

    def get_students_for_course(self, course_id: UUID) -> Set[UUID]:
        """Get all students registered for a specific course"""
        return self._course_students.get(course_id, set())

    def get_courses_for_student(self, student_id: UUID) -> Set[UUID]:
        """Get all courses a student is registered for"""
        return self._student_courses.get(student_id, set())

    async def load_from_backend(self) -> None:
        """Populate entities from backend via DataPreparationService"""
        if not self.data_prep_service:
            raise ValueError(
                "No data prep service available - cannot load from backend"
            )

        from backend.app.services.scheduling.data_preparation_service import (
            PreparedDataset,
        )

        dataset: PreparedDataset = await self.data_prep_service.build_dataset(
            self.session_id
        )

        # Load entities (preserving UUID types)
        for exam_data in dataset.exams:
            self.add_exam(Exam.from_backend_data(exam_data))

        # REMOVED: Timeslot loading - timeslots are now managed through Day objects

        for room_data in dataset.rooms:
            self.add_room(Room.from_backend_data(room_data))

        # Load course registrations with UUID preservation
        for reg in dataset.course_registrations:
            # Ensure UUIDs are preserved
            if isinstance(reg["student_id"], UUID):
                sid = reg["student_id"]
            else:
                sid = UUID(str(reg["student_id"]))

            if isinstance(reg["course_id"], UUID):
                cid = reg["course_id"]
            else:
                cid = UUID(str(reg["course_id"]))

            self.register_student_course(sid, cid)

            if sid not in self.students:
                self.add_student(Student.from_backend_data({"id": sid}))

    def get_students_for_exam(self, exam_id: UUID) -> Set[UUID]:
        """Get students registered for the course of this exam"""
        exam = self.exams[exam_id]
        return self._course_students.get(exam.course_id, set())

    def activate_constraint(self, code: str) -> None:
        self.constraint_registry.activate(code)
        if code.upper() not in self.active_constraints:
            self.active_constraints.append(code.upper())

    def populate_exam_students(self):
        """FIXED: Properly populate students for each exam using course registrations"""
        logger.info("FIXED: Populating exam students from course registrations...")

        total_mappings = 0
        exams_without_students = []
        exam_student_counts = {}

        for exam in self.exams.values():
            # Get students registered for this exam's course
            students_for_course = self._course_students.get(exam.course_id, set())

            if not students_for_course:
                logger.warning(
                    f"No students found for exam {exam.id} (course {exam.course_id})"
                )
                exams_without_students.append(exam.id)
                exam.expected_students = 0
                exam_student_counts[exam.id] = 0
                continue

            # Set the students for this exam
            if hasattr(exam, "set_students"):
                exam.set_students(students_for_course)
            else:
                logger.warning(f"Method does not exist")

            # CRITICAL: Update expected_students to match actual registered students
            actual_student_count = len(students_for_course)
            exam.expected_students = actual_student_count
            exam_student_counts[exam.id] = actual_student_count

            total_mappings += actual_student_count

            logger.debug(f"Exam {exam.id}: {actual_student_count} students registered")

        # Log detailed statistics
        if exam_student_counts:
            min_students = (
                min(exam_student_counts.values()) if exam_student_counts else 0
            )
            max_students = (
                max(exam_student_counts.values()) if exam_student_counts else 0
            )
            avg_students = total_mappings / len(self.exams) if self.exams else 0

            logger.info(f"FIXED: Student-exam mapping complete:")
            logger.info(f"  Total student-exam mappings: {total_mappings}")
            logger.info(f"  Exams without students: {len(exams_without_students)}")
            logger.info(
                f"  Students per exam - Min: {min_students}, Max: {max_students}, Avg: {avg_students:.1f}"
            )

        # Don't fail on missing students in test mode - just warn
        if exams_without_students:
            logger.warning(
                f"WARNING: {len(exams_without_students)} exams have no students"
            )
            logger.info("This may be expected in test scenarios with sparse data")

        if total_mappings == 0:
            logger.warning("WARNING: No student-exam mappings created")
            logger.warning(
                "This may cause solver issues but continuing for test purposes"
            )
            return

        # Validate that students are mapped to exams
        students_with_exams = set()
        for exam in self.exams.values():
            if hasattr(exam, "students") and exam.students:
                students_with_exams.update(exam.students)

        students_without_exams = set(self.students.keys()) - students_with_exams
        if students_without_exams:
            logger.info(
                f"INFO: {len(students_without_exams)} students have no exams (may be normal)"
            )

        logger.info("FIXED: populate_exam_students completed successfully")

    def validate_problem_data(self) -> Dict[str, Any]:
        """FIXED: Comprehensive problem data validation"""
        validation = {"valid": True, "errors": [], "warnings": [], "stats": {}}

        # Basic entity validation
        entities = {
            "exams": len(self.exams),
            "days": len(self.days),
            "rooms": len(self.rooms),
            "students": len(self.students),
        }

        for entity_name, count in entities.items():
            if count == 0:
                validation["errors"].append(f"No {entity_name} defined")
                validation["valid"] = False

        validation["stats"].update(entities)

        # Validate each day has exactly 3 timeslots
        for day_id, day in self.days.items():
            if len(day.timeslots) != 3:
                validation["errors"].append(
                    f"Day {day_id} has {len(day.timeslots)} timeslots, expected 3"
                )
                validation["valid"] = False

        # Invigilator validation
        inv_validation = self.validate_invigilator_data()
        validation["valid"] = validation["valid"] and inv_validation["valid"]
        validation["errors"].extend(inv_validation["errors"])
        validation["warnings"].extend(inv_validation["warnings"])
        validation["stats"]["invigilators"] = inv_validation["stats"]

        # Student-course mapping validation
        total_registrations = sum(
            len(courses) for courses in self._student_courses.values()
        )

        if total_registrations == 0:
            validation["warnings"].append("No student-course registrations found")

        validation["stats"]["student_registrations"] = total_registrations

        return validation

    def build_cpsat_model(self, builder) -> None:
        """Encode variables, register constraints, and build CP-SAT model"""
        # Validate before building
        validation = self.validate_problem_data()
        if not validation["valid"]:
            error_msg = f"Problem validation failed: {validation['errors']}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Get the model and shared variables from the builder
        model, shared_vars = builder.build()
        self.cpsat_model = model

    def solve(self, solver_manager) -> TimetableSolution:
        """Run CP-SAT solver and extract solution"""
        status, solution = solver_manager.solve()
        return solution

    def export_solution(self, solution: TimetableSolution) -> Dict[str, Any]:
        """Convert solution to dict for downstream use"""
        return solution.to_dict()
