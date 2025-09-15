# scheduling_engine/core/problem_model.py - FIXED VERSION

"""
Enhanced Problem Model for CP-SAT integration
with modular constraint registry and CP-SAT pipeline.

CRITICAL FIXES:
- Strong invigilator data validation
- Fail-fast on invalid configurations
- Deterministic data generation controls
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
class TimeSlot:
    id: UUID
    name: str
    start_time: time
    end_time: time
    duration_minutes: int
    date: Optional[date] = None
    is_active: bool = True
    duration_slots: int = field(init=False)

    def __post_init__(self):
        self.duration_slots = math.ceil(self.duration_minutes / 60)

    @classmethod
    def from_backend_data(cls, data: Dict[str, Any]) -> TimeSlot:
        start_time_str = data.get("start_time", "09:00")
        end_time_str = data.get("end_time", "12:00")
        uuid_obj = UUID(str(data["id"]))
        # Handle time parsing more robustly
        if isinstance(start_time_str, str):
            hh, mm = map(int, start_time_str.split(":"))
            start_time_obj = time(hh, mm)
        else:
            start_time_obj = start_time_str

        if isinstance(end_time_str, str):
            hh2, mm2 = map(int, end_time_str.split(":"))
            end_time_obj = time(hh2, mm2)
        else:
            end_time_obj = end_time_str

        date_value = data.get("date", None)
        if isinstance(date_value, str):
            date_obj = date.fromisoformat(date_value)
        else:
            date_obj = date_value
        return cls(
            id=uuid_obj,
            name=data.get("name", ""),
            start_time=start_time_obj,
            end_time=end_time_obj,
            duration_minutes=int(data.get("duration_minutes", 180)),
            date=date_obj,  # set date properly
            is_active=bool(data.get("is_active", True)),
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
    def from_backend_data(cls, data: Dict[str, Any]) -> Room:
        # Handle UUID conversion more robustly
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
    def from_backend_data(cls, data: Dict[str, Any]) -> Student:
        # Handle UUID conversion more robustly
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
    name: str = ""
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
    """
    FIXED: Enhanced Invigilator dataclass with validation
    """

    id: UUID
    name: str = ""
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
    def from_staff(cls, staff: "Staff") -> "Invigilator":
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
    def from_instructor(cls, instructor: "Instructor") -> "Invigilator":
        """Create an Invigilator from an Instructor"""
        return cls(
            id=instructor.id,
            name=instructor.name or f"Instructor_{instructor.id}",
            email=instructor.email,
            department=instructor.department,
            can_invigilate=True,
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
    def from_backend_data(cls, data: Dict[str, Any]) -> Exam:
        # Handle UUID conversion more robustly
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
    """
    FIXED: Problem model with enhanced validation and deterministic controls
    """

    def __init__(
        self,
        session_id: UUID,
        exam_period_start: date,
        exam_period_end: date,
        db_session: Optional[AsyncSession] = None,
        deterministic_seed: Optional[int] = None,  # FIXED: Add seed control
    ):
        self.id = uuid4()
        self.session_id = session_id
        self.exam_period_start = exam_period_start
        self.exam_period_end = exam_period_end
        self.days = self._generate_days(exam_period_start, exam_period_end)
        self.deterministic_seed = deterministic_seed  # FIXED: Store seed

        # Entities
        self.exams: Dict[UUID, Exam] = {}
        self.time_slots: Dict[UUID, TimeSlot] = {}
        self.rooms: Dict[UUID, Room] = {}
        self.students: Dict[UUID, Student] = {}

        # Course registrations
        self._student_courses: Dict[UUID, Set[UUID]] = defaultdict(set)
        self._course_students: Dict[UUID, Set[UUID]] = defaultdict(set)

        # Constraint registry - initialize with global definitions
        self.constraint_registry = ConstraintRegistry()
        self._initialize_constraint_registry()
        self._active_constraints: List[str] = []

        # Configuration parameters
        self.min_gap_slots = 1
        self.max_exams_per_day = 3
        self.overbook_rate = 0.1

        # FIXED: Enhanced invigilator management
        self.instructors: Dict[UUID, "Instructor"] = {}
        self._invigilators: Dict[UUID, "Invigilator"] = {}
        self.staff: Dict[UUID, "Staff"] = {}

        # Scheduling parameters
        self.time_slots_per_day = 3
        self.max_concurrent_exams = 10
        self.min_gap_minutes = 60
        self.preferred_gap_slots = 2
        self.min_invigilators_per_room = 1
        self.max_students_per_invigilator = 50
        self.allow_back_to_back_exams = False
        self.require_same_day_practicals = True

        # Backend initialization
        self.db_session = db_session
        self.data_prep_service: Optional[DataPreparationService] = None

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

    def _initialize_constraint_registry(self):
        """Initialize constraint registry with global constraint definitions."""
        try:
            logger.info(
                "Initialized problem constraint registry with core-preloaded definitions only"
            )
        except ImportError as e:
            logger.warning(f"Could not initialize constraint registry: {e}")
            logger.info("Constraint registry will start empty")

    def _generate_days(self, start: date, end: date) -> List[date]:
        d, days = start, []
        while d <= end:
            days.append(d)
            d += timedelta(days=1)
        return days

    @property
    def invigilators(self):
        """FIXED: Return combined mapping with enhanced validation"""
        combined = dict(getattr(self, "_invigilators", {}))

        # Add staff who can invigilate
        for sid, staff in getattr(self, "staff", {}).items():
            if getattr(staff, "can_invigilate", True):
                try:
                    # Convert staff to invigilator with validation
                    invigilator = Invigilator.from_staff(staff)
                    combined[sid] = invigilator
                except Exception as e:
                    logger.error(f"Failed to convert staff {sid} to invigilator: {e}")

        # Add instructors as invigilators
        for iid, instructor in getattr(self, "instructors", {}).items():
            if iid not in combined:  # Don't override existing
                try:
                    invigilator = Invigilator.from_instructor(instructor)
                    combined[iid] = invigilator
                except Exception as e:
                    logger.error(
                        f"Failed to convert instructor {iid} to invigilator: {e}"
                    )

        return combined

    def validate_invigilator_data(self) -> Dict[str, Any]:
        """FIXED: Comprehensive invigilator data validation"""
        validation_result = {"valid": True, "errors": [], "warnings": [], "stats": {}}

        invigilators = self.invigilators

        if not invigilators:
            validation_result["valid"] = False
            validation_result["errors"].append("No invigilators available")
            return validation_result

        # Validate each invigilator
        valid_count = 0
        invalid_count = 0
        total_capacity = 0

        for inv_id, invigilator in invigilators.items():
            try:
                # Basic validation
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

        # Overall validation
        validation_result["stats"] = {
            "total_invigilators": len(invigilators),
            "valid_invigilators": valid_count,
            "invalid_invigilators": invalid_count,
            "total_capacity": total_capacity,
        }

        if valid_count == 0:
            validation_result["valid"] = False
            validation_result["errors"].append("No valid invigilators found")

        # Check capacity vs demand
        total_students = sum(exam.expected_students for exam in self.exams.values())
        if total_capacity < total_students:
            validation_result["warnings"].append(
                f"Total invigilator capacity ({total_capacity}) may be insufficient for total students ({total_students})"
            )

        return validation_result

    def add_exam(self, exam: Exam) -> None:
        self.exams[exam.id] = exam

    def add_time_slot(self, slot: TimeSlot) -> None:
        self.time_slots[slot.id] = slot

    def add_room(self, room: Room) -> None:
        self.rooms[room.id] = room

    def add_student(self, student: Student) -> None:
        self.students[student.id] = student

    def register_student_course(self, student_id: UUID, course_id: UUID) -> None:
        self._student_courses[student_id].add(course_id)
        self._course_students[course_id].add(student_id)

    def get_time_slot_index(self, time_slot_id: UUID) -> int:
        """Get the index/position of a time slot"""
        slot_ids = list(self.time_slots.keys())
        try:
            return slot_ids.index(time_slot_id)
        except ValueError:
            return -1

    def get_day_index(self, date_obj: date) -> int:
        """Get the index of a day in the exam period"""
        try:
            return self.days.index(date_obj)
        except ValueError:
            return -1

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

        for exam_data in dataset.exams:
            self.add_exam(Exam.from_backend_data(exam_data))

        for slot_data in dataset.time_slots:
            self.add_time_slot(TimeSlot.from_backend_data(slot_data))

        for room_data in dataset.rooms:
            self.add_room(Room.from_backend_data(room_data))

        for reg in dataset.course_registrations:
            sid, cid = UUID(str(reg["student_id"])), UUID(str(reg["course_id"]))
            self.register_student_course(sid, cid)

            if sid not in self.students:
                self.add_student(Student.from_backend_data({"id": str(sid)}))

    def get_students_for_exam(self, exam_id: UUID) -> Set[UUID]:
        """Get students registered for the course of this exam"""
        exam = self.exams[exam_id]
        return self._course_students.get(exam.course_id, set())

    def activate_constraint(self, code: str) -> None:
        self.constraint_registry.activate(code)
        if code.upper() not in self._active_constraints:
            self._active_constraints.append(code.upper())

    def populate_exam_students(self):
        """Populate students for each exam based on course registrations"""
        for exam in self.exams.values():
            # Get students registered for this exam's course
            students_for_course = self.get_students_for_course(exam.course_id)
            exam.set_students(students_for_course)

            # Set allowed rooms (for now, allow all rooms)
            exam.allowed_rooms = set(self.rooms.keys())

            # Update expected_students if we have actual registration data
            if students_for_course:
                exam.expected_students = max(
                    exam.expected_students, len(students_for_course)
                )

    def validate_problem_data(self) -> Dict[str, Any]:
        """FIXED: Comprehensive problem data validation"""
        validation = {"valid": True, "errors": [], "warnings": [], "stats": {}}

        # Basic entity validation
        entities = {
            "exams": len(self.exams),
            "time_slots": len(self.time_slots),
            "rooms": len(self.rooms),
            "students": len(self.students),
        }

        for entity_name, count in entities.items():
            if count == 0:
                validation["errors"].append(f"No {entity_name} defined")
                validation["valid"] = False

        validation["stats"].update(entities)

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
        self._cpsat_model = model

    def solve(self, solver_manager) -> TimetableSolution:
        """Run CP-SAT solver and extract solution"""
        status, solution = solver_manager.solve()
        return solution

    def export_solution(self, solution: TimetableSolution) -> Dict[str, Any]:
        """Convert solution to dict for downstream use"""
        return solution.to_dict()
