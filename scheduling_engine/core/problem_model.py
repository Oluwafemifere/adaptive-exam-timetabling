# scheduling_engine/core/problem_model.py

from __future__ import annotations
import math
import traceback
from typing import Dict, List, Set, Optional, Any, TYPE_CHECKING, Tuple
from uuid import UUID, uuid4
from dataclasses import dataclass, field, asdict
from datetime import datetime, time, date, timedelta
from enum import Enum
import logging
from collections import defaultdict
import uuid


from scheduling_engine.core.constraint_registry import ConstraintRegistry
from scheduling_engine.core.constraint_types import (
    ConstraintDefinition,
    ParameterDefinition,
    ConstraintType,
    ConstraintCategory,
)


if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from backend.app.services.scheduling.data_preparation_service import (
        ProblemModelCompatibleDataset,
    )

logger = logging.getLogger(__name__)


class ExamTypeEnum:
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

    def to_dict(self) -> Dict[str, Any]:
        """Converts the Timeslot object to a dictionary."""
        return {
            "id": str(self.id),
            "parent_day_id": str(self.parent_day_id),
            "name": self.name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_minutes": self.duration_minutes,
        }


@dataclass
class Day:
    id: UUID
    date: date
    timeslots: List[Timeslot] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Converts the Day object to a dictionary."""
        return {
            "id": str(self.id),
            "date": self.date.isoformat(),
            "timeslots": [ts.to_dict() for ts in self.timeslots],
        }


@dataclass
class Room:
    id: UUID
    code: str
    capacity: int
    exam_capacity: int
    has_computers: bool = False
    adjacent_seat_pairs: List[Tuple[int, int]] = field(default_factory=list)
    building_name: Optional[str] = None

    @property
    def overbookable(self) -> bool:
        return getattr(self, "_overbookable", False)

    @property
    def seat_indices(self) -> List[int]:
        return list(range(self.capacity))

    def to_dict(self) -> Dict[str, Any]:
        """Converts the Room object to a dictionary."""
        d = asdict(self)
        d["id"] = str(self.id)
        return d

    @classmethod
    def from_backend_data(cls, data: Dict[str, Any]) -> "Room":
        """FIXED: Create Room from backend data with proper field mapping and careful handling of adjacent_seat_pairs."""
        id_value = data["id"]
        uuid_obj = UUID(str(id_value)) if not isinstance(id_value, UUID) else id_value

        adjacent_pairs_value = data.get("adjacent_seat_pairs")
        if not isinstance(adjacent_pairs_value, list):
            if adjacent_pairs_value is not None:
                logger.warning(
                    f"Room {data.get('code', '')} has non-list adjacent_seat_pairs: {adjacent_pairs_value}. "
                    "Ignoring this field."
                )
            adjacent_pairs_value = []

        # --- START OF FIX ---
        # 1. Create the instance without the overbookable property first.
        room_instance = cls(
            id=uuid_obj,
            code=data.get("code", ""),
            capacity=int(data.get("capacity", 0)),
            exam_capacity=int(data.get("exam_capacity", data.get("capacity", 0))),
            has_computers=bool(data.get("has_computers", False)),
            adjacent_seat_pairs=adjacent_pairs_value,
            building_name=data.get("building_name"),
        )

        # 2. Explicitly set the internal '_overbookable' attribute that the property relies on.
        setattr(room_instance, "_overbookable", bool(data.get("overbookable", False)))

        return room_instance
        # --- END OF FIX ---


@dataclass
class Student:
    id: UUID
    department: Optional[str] = None
    registered_courses: Dict[UUID, str] = field(
        default_factory=dict
    )  # CourseID -> RegistrationType

    @classmethod
    def from_backend_data(cls, data: Dict[str, Any]) -> "Student":
        """FIXED: Create Student from backend data"""
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

    def to_dict(self) -> Dict[str, Any]:
        """Converts the Instructor object to a dictionary."""
        d = asdict(self)
        d["id"] = str(self.id)
        return d

    @classmethod
    def from_backend_data(cls, data: Dict[str, Any]) -> "Instructor":
        """Create Instructor from backend data for consistency."""
        id_value = data["id"]
        uuid_obj = UUID(str(id_value)) if not isinstance(id_value, UUID) else id_value
        return cls(
            id=uuid_obj,
            name=data.get("name", ""),
            email=data.get("email"),
            department=data.get("department"),
            availability=data.get("availability", {}),
        )


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

        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def from_backend_data(cls, data: Dict[str, Any]) -> "Staff":
        """Create Staff from backend data"""
        id_value = data["id"]
        if isinstance(id_value, UUID):
            uuid_obj = id_value
        else:
            uuid_obj = UUID(str(id_value))

        return cls(
            id=uuid_obj,
            name=data.get("name", ""),
            department=data.get("department"),
            can_invigilate=data.get("can_invigilate", True),
            max_concurrent_exams=data.get("max_concurrent_exams", 1),
        )


@dataclass
class Invigilator:
    """ENHANCED: Comprehensive Invigilator dataclass with backend integration"""

    id: UUID
    name: str
    email: Optional[str] = None
    department: Optional[str] = None
    can_invigilate: bool = True
    max_concurrent_exams: int = 1
    max_students_per_exam: int = 50
    availability: Dict[str, Any] = field(default_factory=dict)

    staff_number: Optional[str] = None
    staff_type: Optional[str] = None
    max_daily_sessions: int = 2
    max_consecutive_sessions: int = 1

    def __post_init__(self):
        """Validate invigilator data"""
        if not self.name:
            logger.warning(f"Invigilator {self.id} has no name")
        if self.max_concurrent_exams < 1:
            raise ValueError(f"Invigilator {self.id} max_concurrent_exams must be >= 1")
        if self.max_students_per_exam < 1:
            raise ValueError(
                f"Invigilator {self.id} max_students_per_exam must be >= 1"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Converts the Invigilator object to a dictionary."""
        d = asdict(self)
        d["id"] = str(self.id)
        return d

    @classmethod
    def from_backend_data(cls, data: Dict[str, Any]) -> "Invigilator":
        """Create Invigilator from backend data"""
        id_value = data["id"]
        if isinstance(id_value, UUID):
            uuid_obj = id_value
        else:
            uuid_obj = UUID(str(id_value))

        full_name = data.get("name", f"Staff {data.get('staff_number', '')}")

        return cls(
            id=uuid_obj,
            name=full_name,
            email=data.get("email"),
            department=data.get("department"),
            can_invigilate=data.get("can_invigilate", True),
            max_concurrent_exams=data.get("max_concurrent_exams", 1),
            max_students_per_exam=data.get("max_students_per_exam", 50),
            availability=data.get("availability", {}),
            staff_number=data.get("staff_number"),
            staff_type=data.get("staff_type"),
            max_daily_sessions=data.get("max_daily_sessions", 2),
            max_consecutive_sessions=data.get("max_consecutive_sessions", 1),
        )

    @classmethod
    def from_staff(cls, staff: Staff) -> "Invigilator":
        """Create an Invigilator from a Staff member"""
        return cls(
            id=staff.id,
            name=getattr(staff, "name", f"Staff {staff.id}"),
            email=getattr(staff, "email", None),
            department=getattr(staff, "department", None),
            can_invigilate=getattr(staff, "can_invigilate", True),
            max_concurrent_exams=getattr(staff, "max_concurrent_exams", 1),
            max_students_per_exam=getattr(staff, "max_students_per_exam", 50),
            availability=getattr(staff, "availability", {}),
        )


@dataclass
class Exam:
    id: UUID
    course_id: UUID
    duration_minutes: int
    expected_students: int
    is_practical: bool = False
    morning_only: bool = False
    actual_student_count: int = 0
    department_ids: Set[UUID] = field(default_factory=set)
    prerequisite_exams: Set[UUID] = field(default_factory=set)
    instructor_ids: Set[UUID] = field(default_factory=set)
    instructors: List[Dict[str, Any]] = field(default_factory=list, repr=False)
    departments: List[Dict[str, Any]] = field(default_factory=list, repr=False)
    faculty_ids: Set[UUID] = field(default_factory=set)
    faculties: List[Dict[str, Any]] = field(default_factory=list, repr=False)

    def __post_init__(self):
        """Initialize internal student dictionary to store registration type."""
        self._students: Dict[UUID, str] = {}  # Student ID -> Registration Type

    @property
    def students(self) -> Dict[UUID, str]:
        """Get students and their registration status for this exam."""
        return self._students

    @students.setter
    def students(self, value: Dict[UUID, str]) -> None:
        """Set students with type safety, expecting a dictionary."""
        if not isinstance(value, dict):
            raise TypeError(
                "Students must be a dictionary of {student_id: registration_type}"
            )
        self._students = value

    @property
    def enrollment(self) -> int:
        return self.expected_students

    @property
    def duration(self) -> int:
        """Alias for duration_minutes to maintain compatibility"""
        return self.duration_minutes

    def to_dict(self) -> Dict[str, Any]:
        """Converts the Exam object to a dictionary."""
        return {
            "id": str(self.id),
            "course_id": str(self.course_id),
            "duration_minutes": self.duration_minutes,
            "expected_students": self.expected_students,
            "is_practical": self.is_practical,
            "morning_only": self.morning_only,
            "actual_student_count": len(self._students),
            "prerequisite_exams": [str(e) for e in self.prerequisite_exams],
            "students": [
                {"student_id": str(s_id), "registration_type": reg_type}
                for s_id, reg_type in self._students.items()
            ],
            "course_code": getattr(self, "course_code", "N/A"),
            "course_title": getattr(self, "course_title", "N/A"),
            "instructor_ids": [str(inst_id) for inst_id in self.instructor_ids],
            "department_ids": [str(dept_id) for dept_id in self.department_ids],
            "faculty_ids": [str(fac_id) for fac_id in self.faculty_ids],
            "instructors": self.instructors,
            "departments": self.departments,
            "faculties": self.faculties,
        }

    def set_students(self, students_with_status: Dict[UUID, str]) -> None:
        """Set the complete student list for this exam with registration status."""
        self._students = students_with_status
        if len(self._students) > self.expected_students:
            self.expected_students = len(self._students)

    def add_student(self, student_id: UUID, registration_type: str = "normal") -> None:
        """Add a single student to this exam with their registration status."""
        self._students[student_id] = registration_type

    def remove_student(self, student_id: UUID) -> None:
        """Remove a student from this exam."""
        self._students.pop(student_id, None)

    def has_student(self, student_id: UUID) -> bool:
        """Check if a student is registered for this exam."""
        return student_id in self._students

    @classmethod
    def from_backend_data(cls, data: Dict[str, Any]) -> "Exam":
        """Create Exam from backend data with proper field mapping"""
        id_value = data["id"]
        course_id_value = data["course_id"]

        uuid_obj = UUID(str(id_value)) if not isinstance(id_value, UUID) else id_value
        course_uuid_obj = (
            UUID(str(course_id_value))
            if not isinstance(course_id_value, UUID)
            else course_id_value
        )

        exam = cls(
            id=uuid_obj,
            course_id=course_uuid_obj,
            duration_minutes=int(data.get("duration_minutes", 180)),
            expected_students=int(data.get("expected_students", 0)),
            is_practical=bool(data.get("is_practical", False)),
            morning_only=bool(data.get("morning_only", False)),
            prerequisite_exams=data.get("prerequisite_exams", set()),
        )

        if "instructors" in data and data["instructors"]:
            exam.instructors = data["instructors"]
            exam.instructor_ids = {
                UUID(str(inst["id"])) for inst in data["instructors"]
            }

        if "departments" in data and data["departments"]:
            exam.departments = data["departments"]
            exam.department_ids = {
                UUID(str(dept["id"])) for dept in data["departments"]
            }

        if "faculties" in data and data["faculties"]:
            exam.faculties = data["faculties"]
            exam.faculty_ids = {
                UUID(str(faculty["id"])) for faculty in data["faculties"]
            }

        if "students" in data and data["students"]:
            exam.set_students(data["students"])

        if "department_ids" in data and data["department_ids"]:
            exam.department_ids = {
                UUID(str(dept_id)) for dept_id in data["department_ids"]
            }

        if "faculty_ids" in data and data["faculty_ids"]:
            exam.faculty_ids = {UUID(str(fac_id)) for fac_id in data["faculty_ids"]}
        setattr(exam, "course_code", data.get("course_code", "N/A"))
        setattr(exam, "course_title", data.get("course_title", "N/A"))

        if "instructor_ids" in data and data["instructor_ids"]:
            exam.instructor_ids = data["instructor_ids"]

        # actual_student_count is now derived from the length of the students dict
        actual_count = len(exam.students)
        if actual_count > exam.expected_students:
            exam.expected_students = actual_count

        return exam


class ExamSchedulingProblem:
    """ENHANCED: Problem model with robust backend data integration and HITL support"""

    def __init__(
        self,
        session_id: UUID,
        exam_period_start: date,
        exam_period_end: date,
        db_session: Optional["AsyncSession"] = None,
        deterministic_seed: Optional[int] = None,
    ):
        self.id = uuid4()
        self.session_id = session_id
        self.exam_period_start = exam_period_start
        self.exam_period_end = exam_period_end

        # Core data structures
        self.holidays: Set[date] = set()
        self.days: Dict[UUID, Day] = {}
        self.deterministic_seed = deterministic_seed

        # Entities with UUID keys
        self.exams: Dict[UUID, Exam] = {}
        self.rooms: Dict[UUID, Room] = {}
        self.students: Dict[UUID, Student] = {}

        # Course registrations with UUID keys
        self._student_courses: Dict[UUID, Set[UUID]] = defaultdict(set)
        self.course_students: Dict[UUID, Set[UUID]] = defaultdict(set)
        self.day_timeslot_map: Dict[UUID, Set[UUID]] = defaultdict(set)

        # Enhanced invigilator management with UUID keys
        self.instructors: Dict[UUID, Instructor] = {}
        self.invigilators: Dict[UUID, Invigilator] = {}
        self.staff: Dict[UUID, Staff] = {}

        # --- HITL and Dynamic Configuration ---
        self.locks: List[Dict[str, Any]] = []
        self.constraint_definitions: List[ConstraintDefinition] = []
        self.module_map: Dict[str, str] = {
            # --- CORE (Always Enforced by Manager) ---
            "StartUniquenessConstraint": "scheduling_engine.constraints.hard_constraints.start_uniqueness.StartUniquenessConstraint",
            "OccupancyDefinitionConstraint": "scheduling_engine.constraints.hard_constraints.occupancy_definition.OccupancyDefinitionConstraint",
            "RoomAssignmentConsistencyConstraint": "scheduling_engine.constraints.hard_constraints.room_assignment_consistency.RoomAssignmentConsistencyConstraint",
            "RoomContinuityConstraint": "scheduling_engine.constraints.hard_constraints.room_continuity.RoomContinuityConstraint",
            "StartFeasibilityConstraint": "scheduling_engine.constraints.hard_constraints.start_feasibility.StartFeasibilityConstraint",
            "InvigilatorSinglePresenceConstraint": "scheduling_engine.constraints.hard_constraints.invigilator_single_presence.InvigilatorSinglePresenceConstraint",
            # --- DYNAMIC HARD (Configurable) ---
            "UNIFIED_STUDENT_CONFLICT": "scheduling_engine.constraints.hard_constraints.unified_student_conflict.UnifiedStudentConflictConstraint",
            "MAX_EXAMS_PER_STUDENT_PER_DAY": "scheduling_engine.constraints.hard_constraints.max_exams_per_student_per_day.MaxExamsPerStudentPerDayConstraint",
            "ROOM_CAPACITY_HARD": "scheduling_engine.constraints.hard_constraints.room_capacity_hard.RoomCapacityHardConstraint",
            "MINIMUM_INVIGILATORS": "scheduling_engine.constraints.hard_constraints.minimum_invigilators.MinimumInvigilatorsConstraint",
            "INSTRUCTOR_CONFLICT": "scheduling_engine.constraints.hard_constraints.instructor_conflict.InstructorConflictConstraint",
            "ROOM_SEQUENTIAL_USE": "scheduling_engine.constraints.hard_constraints.room_sequential_use.RoomSequentialUseConstraint",
            # --- DYNAMIC SOFT (Configurable) ---
            "MINIMUM_GAP": "scheduling_engine.constraints.soft_constraints.minimum_gap.MinimumGapConstraint",
            "OVERBOOKING_PENALTY": "scheduling_engine.constraints.soft_constraints.overbooking_penalty.OverbookingPenaltyConstraint",
            "PREFERENCE_SLOTS": "scheduling_engine.constraints.soft_constraints.preference_slots.PreferenceSlotsConstraint",
            "INVIGILATOR_LOAD_BALANCE": "scheduling_engine.constraints.soft_constraints.invigilator_load_balance.InvigilatorLoadBalanceConstraint",
            "CARRYOVER_STUDENT_CONFLICT": "scheduling_engine.constraints.soft_constraints.carryover_student_conflict.CarryoverStudentConflictConstraint",
            "INVIGILATOR_AVAILABILITY": "scheduling_engine.constraints.soft_constraints.invigilator_availability.InvigilatorAvailabilityConstraint",
            "DAILY_WORKLOAD_BALANCE": "scheduling_engine.constraints.soft_constraints.daily_workload_balance.DailyWorkloadBalanceConstraint",
            "ROOM_DURATION_HOMOGENEITY": "scheduling_engine.constraints.soft_constraints.room_duration_homogeneity.RoomDurationHomogeneityConstraint",
        }

        self.constraint_registry = ConstraintRegistry()
        # Scheduling parameters
        self.timeslots_per_day = 3
        self.max_concurrent_exams = 10
        self.min_gap_minutes = 60
        self.preferred_gap_slots = 2
        self.min_invigilators_per_room = 1
        self.max_students_per_invigilator = 50
        self.allow_back_to_back_exams = False
        self.require_same_day_practicals = True

        # Configuration parameters
        self.min_gap_slots = 1
        self.max_exams_per_day = 3
        self.overbook_rate = 0.1
        self.base_slot_duration_minutes: int = 180
        self.slot_generation_mode: str = "flexible"  # 'fixed' or 'flexible'
        self.flexible_slot_duration_minutes: int = 60  # Duration for flexible slots

        # Backend integration
        self.db_session = db_session
        self.data_prep_service: Optional["ExactDataFlowService"] = None

        if db_session:
            try:
                from backend.app.services.scheduling.data_preparation_service import (
                    ExactDataFlowService,
                )

                self.data_prep_service = ExactDataFlowService(db_session)
            except ImportError:
                logger.warning(
                    "DataPreparationService not available, using test data only"
                )

        # Caching for performance
        self.timeslots_cache: Optional[Dict[UUID, Timeslot]] = None
        self.timeslot_to_day: Optional[Dict[UUID, Day]] = None

    def add_staff(self, staff: Staff) -> None:
        """Add a staff member to the problem"""
        self.staff[staff.id] = staff

    def ensure_constraints_activated(self) -> None:
        """Ensure minimum constraints are activated - called from main.py"""
        if not self.constraint_registry.get_active_constraints():
            # Activate all constraints that were loaded and marked as enabled
            for definition in self.constraint_definitions:
                if definition.enabled:
                    self.constraint_registry.activate(definition.id)
            logger.info("Activated all enabled constraints from configuration.")

    def _parse_constraint_definitions(self, constraints_data: Dict[str, Any]) -> None:
        """Parses the raw constraint JSON from the DB into structured dataclasses."""
        self.constraint_definitions = []
        rules = constraints_data.get("rules", [])
        config_id = self._ensure_uuid(constraints_data.get("system_configuration_id"))

        # Define a comprehensive map for known constraints to ensure correct categorization.
        known_categories = {
            # Core/Foundational
            "StartUniquenessConstraint": ConstraintCategory.CORE,
            "StartFeasibilityConstraint": ConstraintCategory.CORE,
            "OccupancyDefinitionConstraint": ConstraintCategory.CORE,
            "RoomContinuityConstraint": ConstraintCategory.CORE,
            "RoomAssignmentConsistencyConstraint": ConstraintCategory.CORE,
            # Student Constraints
            "UnifiedStudentConflictConstraint": ConstraintCategory.STUDENT_CONSTRAINTS,
            "MAX_EXAMS_PER_STUDENT_PER_DAY": ConstraintCategory.STUDENT_CONSTRAINTS,
            "MaxExamsPerStudentPerDayConstraint": ConstraintCategory.STUDENT_CONSTRAINTS,
            "MinimumGapConstraint": ConstraintCategory.STUDENT_CONSTRAINTS,
            "MINIMUM_GAP": ConstraintCategory.STUDENT_CONSTRAINTS,
            # Resource Constraints
            "RoomCapacityHardConstraint": ConstraintCategory.RESOURCE_CONSTRAINTS,
            "RoomSequentialUseConstraint": ConstraintCategory.RESOURCE_CONSTRAINTS,
            # Invigilator Constraints
            "MinimumInvigilatorsConstraint": ConstraintCategory.INVIGILATOR_CONSTRAINTS,
            "MINIMUM_INVIGILATORS": ConstraintCategory.INVIGILATOR_CONSTRAINTS,
            "InvigilatorSinglePresenceConstraint": ConstraintCategory.INVIGILATOR_CONSTRAINTS,
            # Optimization Constraints
            "RoomDurationHomogeneityConstraint": ConstraintCategory.OPTIMIZATION_CONSTRAINTS,
        }

        for rule in rules:
            try:
                rule_code = rule["code"]
                category_enum = known_categories.get(
                    rule_code, ConstraintCategory.OTHER
                )

                custom_params_data = rule.get("custom_parameters") or []
                params = [
                    ParameterDefinition(
                        key=p["key"],
                        value=p.get("value"),
                        type=p.get("type", "any"),
                        default=p.get("default"),
                        description=p.get("description"),
                        options=p.get("options"),
                        validation=p.get("validation", {}),
                    )
                    for p in custom_params_data
                ]

                definition = ConstraintDefinition(
                    id=rule_code,
                    name=rule.get("name", rule_code),
                    description=rule.get("description", ""),
                    constraint_type=ConstraintType(rule.get("type", "soft")),
                    category=category_enum,
                    enabled=rule.get("is_enabled", True),
                    weight=float(rule.get("weight", 1.0)),
                    parameters=params,
                    config_id=config_id,
                    database_rule_id=self._ensure_uuid(rule.get("id")),
                )
                self.constraint_definitions.append(definition)
            except Exception as e:
                logger.error(
                    f"Failed to parse constraint rule {rule.get('code', 'N/A')}: {e}"
                )

        logger.info(
            f"Loaded and parsed {len(self.constraint_definitions)} constraint definitions."
        )

    @property
    def timeslots(self) -> Dict[UUID, Timeslot]:
        """Provide backward compatibility - timeslots accessed through days"""
        if self.timeslots_cache is None:
            self.timeslots_cache = {}
            for day in self.days.values():
                for timeslot in day.timeslots:
                    self.timeslots_cache[timeslot.id] = timeslot
        return self.timeslots_cache

    def get_day_for_timeslot(self, timeslot_id: UUID) -> Optional[Day]:
        """Get the day containing a specific timeslot"""
        if self.timeslot_to_day is None:
            self.timeslot_to_day = {}
            for day in self.days.values():
                for timeslot in day.timeslots:
                    self.timeslot_to_day[timeslot.id] = day
        return self.timeslot_to_day.get(timeslot_id)

    def get_timeslots_for_day(self, day_id: UUID) -> List[Timeslot]:
        """Get all timeslots for a specific day"""
        day = self.days.get(day_id)
        return day.timeslots if day else []

    def get_students_for_course(self, course_id: UUID) -> Set[UUID]:
        """Get all students registered for a specific course."""
        return self.course_students.get(course_id, set())

    async def load_from_backend(self, dataset: "ProblemModelCompatibleDataset") -> None:
        """Enhanced loading with comprehensive logging AND FIXED DATA MAPPING"""
        logger.info("=== PROBLEM MODEL LOADING START ===")
        logger.info(
            f"📦 DATASET INFO: {len(dataset.exams)} exams, {len(dataset.students)} students, {len(dataset.rooms)} rooms"
        )

        try:
            # Phase 1: Entity loading with validation
            logger.info("📋 PHASE 1: Loading entities...")
            entities_loaded = self._load_entities_with_validation(dataset)

            if hasattr(dataset, "instructors") and dataset.instructors:
                for instructor_data in dataset.instructors:
                    self.add_instructor(Instructor.from_backend_data(instructor_data))
                logger.info(f"✅ INSTRUCTORS: {len(self.instructors)} loaded")

            # Phase 2: Load HITL and Configuration Data
            logger.info("📋 PHASE 2: Loading HITL data and constraints...")
            self.locks = dataset.locks
            self._parse_constraint_definitions(dataset.constraints)
            self.constraint_registry.load_definitions(
                self.constraint_definitions, self.module_map
            )
            logger.info(
                f"✅ Loaded {len(self.locks)} locks and {len(self.constraint_definitions)} constraint definitions."
            )

            # Phase 3: Relationship validation
            logger.info("📋 PHASE 3: Validating relationships...")
            self._validate_dataset_relationships(dataset, entities_loaded)

            # Phase 4: Student-exam mapping application
            logger.info("📋 PHASE 4: Applying student-exam mappings...")
            self._apply_exam_student_data(dataset.exams)
            self._log_exam_student_statistics()

            # Phase 4a: Build course-student mappings for quick lookup
            logger.info("📋 PHASE 4a: Building course-student mappings...")
            self._build_course_student_mappings()

            # Phase 5: Day and timeslot configuration from dataset
            logger.info("📋 PHASE 5: Configuring days and timeslots from dataset...")
            self._configure_days_and_timeslots(dataset)

            # --- START OF FIX: Process and translate locks after timeslots are created ---
            # logger.info("📋 PHASE 5a: Translating HITL locks to specific timeslots...")
            # self._process_and_translate_locks(dataset)
            # --- END OF FIX ---

            # --- START OF FIX: Conditionally activate constraints based on config ---
            logger.info("📋 PHASE 5b: Activating constraints from configuration...")
            self._activate_constraints_from_config()
            # --- END OF FIX ---

            # Phase 6: Final validation
            logger.info("📋 PHASE 6: Final validation...")
            validation_result = self.validate_problem_data()

            if not validation_result.get("valid", False):
                logger.error(
                    f"🔴 VALIDATION FAILED: {validation_result.get('errors', [])}"
                )
                raise ValueError(
                    f"Problem data validation failed: {validation_result.get('errors')}"
                )

            logger.info("✅ Problem model loading completed successfully")

        except Exception as e:
            logger.error(f"❌ Problem model loading failed: {e}")
            logger.error(f"📍 Stack trace: {traceback.format_exc()}")
            raise

    # --- START OF FIX ---
    def _activate_constraints_from_config(self) -> None:
        """
        Activates all constraints that are marked as 'enabled' in the loaded
        database configuration. Also handles conditional activation based on
        problem settings like slot generation mode.
        """
        # 1. Activate all constraints marked as enabled in the configuration.
        activated_count = 0
        for definition in self.constraint_definitions:
            if definition.enabled:
                self.constraint_registry.activate(definition.id)
                activated_count += 1

        logger.info(
            f"Activated {activated_count} constraints based on 'enabled' flag in configuration."
        )

        # 2. Conditionally activate mode-specific constraints (if not already active).
        if self.slot_generation_mode == "flexible":
            logger.info(
                "Flexible slot mode detected. Ensuring mode-specific constraints are active."
            )
            constraints_to_activate = [
                "ROOM_SEQUENTIAL_USE",
                "ROOM_DURATION_HOMOGENEITY",
            ]
            for constraint_id in constraints_to_activate:
                if self.constraint_registry.get_definition(constraint_id):
                    # The activate method handles duplicates, so it's safe to call again.
                    self.constraint_registry.activate(constraint_id)
                else:
                    logger.warning(
                        f"Attempted to activate '{constraint_id}' for flexible mode, but it is not defined."
                    )
        else:
            logger.info(
                "Fixed slot mode detected. No additional conditional constraints needed."
            )

    # --- END OF FIX ---

    def _build_course_student_mappings(self):
        """Populates the self.course_students dictionary for quick lookups."""
        self.course_students.clear()
        for exam in self.exams.values():
            if exam.course_id and exam.students:
                # The keys of the exam.students dict are the student UUIDs
                self.course_students[exam.course_id].update(exam.students.keys())
        logger.info(f"Built mappings for {len(self.course_students)} courses.")

    def _log_exam_student_statistics(self) -> None:
        """Log detailed exam-student mapping statistics"""
        logger.info("=== EXAM-STUDENT MAPPING STATISTICS ===")
        total_mappings = sum(len(exam.students) for exam in self.exams.values())
        exams_with_students = sum(1 for exam in self.exams.values() if exam.students)
        logger.info(
            f"📊 MAPPING SUMMARY: {total_mappings} total mappings across {exams_with_students}/{len(self.exams)} exams."
        )

    def _load_entities_with_validation(
        self, dataset: ProblemModelCompatibleDataset
    ) -> Dict[str, int]:
        """Load entities with individual error handling and validation"""
        entities_loaded = {"exams": 0, "rooms": 0, "students": 0, "invigilators": 0}

        for exam_data in dataset.exams:
            try:
                self.add_exam(Exam.from_backend_data(exam_data))
                entities_loaded["exams"] += 1
            except Exception as e:
                logger.error(
                    f"Error loading exam {exam_data.get('id', 'unknown')}: {e}"
                )
        for room_data in dataset.rooms:
            try:
                self.add_room(Room.from_backend_data(room_data))
                entities_loaded["rooms"] += 1
            except Exception as e:
                logger.error(
                    f"Error loading room {room_data.get('id', 'unknown')}: {e}"
                )
        for student_data in dataset.students:
            try:
                self.add_student(Student.from_backend_data(student_data))
                entities_loaded["students"] += 1
            except Exception as e:
                logger.error(
                    f"Error loading student {student_data.get('id', 'unknown')}: {e}"
                )
        for invigilator_data in dataset.invigilators:
            try:
                self.add_invigilator(Invigilator.from_backend_data(invigilator_data))
                entities_loaded["invigilators"] += 1
            except Exception as e:
                logger.error(
                    f"Error loading invigilator {invigilator_data.get('id', 'unknown')}: {e}"
                )

        logger.info(f"Entities loaded: {entities_loaded}")
        return entities_loaded

    def _validate_dataset_relationships(
        self, dataset: ProblemModelCompatibleDataset, entities_loaded: Dict[str, int]
    ) -> None:
        """Validate relationships between entities in the dataset"""
        if entities_loaded["exams"] > 0 and entities_loaded["rooms"] > 0:
            max_exam_size = max(exam.expected_students for exam in self.exams.values())
            max_room_capacity = max(room.exam_capacity for room in self.rooms.values())
            if max_exam_size > max_room_capacity:
                raise ValueError(
                    f"Largest exam ({max_exam_size} students) exceeds largest room capacity ({max_room_capacity})"
                )

    def _generate_fallback_days(self) -> None:
        """
        Generates a default set of weekdays and timeslots as a fallback mechanism
        only when the dataset provides no schedule information.
        """
        logger.warning(
            "Executing fallback day generation. The schedule will be based on a default Mon-Fri, 3-slots-per-day structure."
        )
        # Default timeslot definitions if none are provided
        default_timeslots_def = [
            {"name": "Morning", "start": "09:00", "end": "12:00"},
            {"name": "Afternoon", "start": "13:00", "end": "16:00"},
            {"name": "Evening", "start": "17:00", "end": "20:00"},
        ]

        current_date = self.exam_period_start
        while current_date <= self.exam_period_end:
            # Skip weekends (Saturday=5, Sunday=6) and holidays
            if current_date.weekday() >= 5 or current_date in self.holidays:
                current_date += timedelta(days=1)
                continue

            day_id = uuid4()
            day_timeslots = []
            for ts_def in default_timeslots_def:
                start_t = time.fromisoformat(ts_def["start"])
                end_t = time.fromisoformat(ts_def["end"])
                duration = (
                    datetime.combine(date.min, end_t)
                    - datetime.combine(date.min, start_t)
                ).seconds // 60

                timeslot = Timeslot(
                    id=uuid4(),
                    parent_day_id=day_id,
                    name=ts_def["name"],
                    start_time=start_t,
                    end_time=end_t,
                    duration_minutes=duration,
                )
                day_timeslots.append(timeslot)

            day = Day(id=day_id, date=current_date, timeslots=day_timeslots)
            self.days[day.id] = day
            self.day_timeslot_map[day.id] = {slot.id for slot in day.timeslots}
            current_date += timedelta(days=1)

        logger.info(
            f"Generated {len(self.days)} fallback days with {len(self.timeslots)} total timeslots."
        )

    def _configure_days_and_timeslots(
        self, dataset: "ProblemModelCompatibleDataset"
    ) -> None:
        """
        FIXED: Configures days and timeslots from the dataset, supporting both
        fixed and flexible slot generation, with enhanced logging.
        """
        self.slot_generation_mode = getattr(dataset, "slot_generation_mode", "fixed")
        logger.info(
            f"Slot generation mode received from dataset: '{self.slot_generation_mode}'"
        )

        if not hasattr(dataset, "days") or not dataset.days:
            logger.warning(
                "Dataset contains no day/timeslot info. Using fallback generation."
            )
            self._generate_fallback_days()
            return

        logger.info(
            f"Loading {len(dataset.days)} days from dataset with mode '{self.slot_generation_mode}'."
        )
        for day_data in dataset.days:
            try:
                day_id = uuid4()
                day_date = date.fromisoformat(day_data["exam_date"])
                day_timeslots = []

                for ts_data in day_data.get("time_periods", []):
                    if self.slot_generation_mode == "flexible":
                        logger.debug(
                            f"Executing FLEXIBLE slot generation for {day_date}."
                        )
                        # Generate granular, hour-based slots
                        period_start_time = time.fromisoformat(ts_data["start_time"])
                        period_end_time = time.fromisoformat(ts_data["end_time"])
                        slot_duration = timedelta(
                            minutes=self.flexible_slot_duration_minutes
                        )
                        current_time = datetime.combine(date.today(), period_start_time)
                        end_datetime = datetime.combine(date.today(), period_end_time)

                        slot_counter = 1
                        while current_time < end_datetime:
                            slot_end_time = current_time + slot_duration
                            if slot_end_time > end_datetime:
                                break

                            timeslot = Timeslot(
                                id=uuid4(),
                                parent_day_id=day_id,
                                name=f"{ts_data['period_name']}_Slot{slot_counter}",
                                start_time=current_time.time(),
                                end_time=slot_end_time.time(),
                                duration_minutes=self.flexible_slot_duration_minutes,
                            )
                            day_timeslots.append(timeslot)
                            current_time = slot_end_time
                            slot_counter += 1
                    else:
                        logger.debug(f"Executing FIXED slot generation for {day_date}.")
                        # Original fixed-slot logic
                        start_t = time.fromisoformat(ts_data["start_time"])
                        end_t = time.fromisoformat(ts_data["end_time"])
                        duration = (
                            datetime.combine(date.min, end_t)
                            - datetime.combine(date.min, start_t)
                        ).seconds // 60
                        timeslot = Timeslot(
                            id=uuid4(),
                            parent_day_id=day_id,
                            name=ts_data["period_name"],
                            start_time=start_t,
                            end_time=end_t,
                            duration_minutes=duration,
                        )
                        day_timeslots.append(timeslot)

                if not day_timeslots:
                    logger.warning(f"Day {day_date} has no time periods. Skipping.")
                    continue

                day = Day(id=day_id, date=day_date, timeslots=day_timeslots)
                self.days[day.id] = day
                self.day_timeslot_map[day.id] = {slot.id for slot in day.timeslots}

            except Exception as e:
                logger.error(f"Failed to process day data: {day_data}. Error: {e}")
                continue

        if not self.days:
            logger.error("CRITICAL: Failed to load any valid days. Using fallback.")
            self._generate_fallback_days()
        else:
            logger.info(
                f"Successfully loaded {len(self.days)} days and {len(self.timeslots)} total timeslots."
            )

        # Set base slot duration for calculations
        if self.slot_generation_mode == "flexible":
            self.base_slot_duration_minutes = self.flexible_slot_duration_minutes
        elif self.timeslots:
            self.base_slot_duration_minutes = next(
                iter(self.timeslots.values())
            ).duration_minutes
        else:
            logger.warning("No timeslots loaded; using default duration of 180 mins.")
            self.base_slot_duration_minutes = 180
        logger.info(
            f"Base slot duration for calculations set to {self.base_slot_duration_minutes} minutes."
        )

    def get_exam_duration_in_slots(self, exam_id: UUID) -> int:
        """Calculates how many slots an exam occupies based on the base slot duration."""
        exam = self.exams.get(exam_id)
        if not exam or self.base_slot_duration_minutes <= 0:
            return 1
        return math.ceil(exam.duration_minutes / self.base_slot_duration_minutes)

    def is_start_feasible(self, exam_id: UUID, start_slot_id: UUID) -> bool:
        """Checks if an exam can start at a given slot and complete within the same day."""
        exam = self.exams.get(exam_id)
        if not exam:
            return False

        day = self.get_day_for_timeslot(start_slot_id)
        if not day:
            return False

        try:
            start_index = [ts.id for ts in day.timeslots].index(start_slot_id)
        except ValueError:
            return False

        duration_slots = self.get_exam_duration_in_slots(exam_id)
        return start_index + duration_slots <= len(day.timeslots)

    def _ensure_uuid(self, value: Any) -> UUID:
        """Ensure a value is a UUID object, converting from string if necessary"""
        return value if isinstance(value, UUID) else UUID(str(value))

    def _apply_exam_student_data(self, exam_data_list: List[Dict[str, Any]]) -> None:
        """Apply student data directly from exam objects in dataset"""
        for exam_data in exam_data_list:
            exam_id = self._ensure_uuid(exam_data["id"])
            if exam_id in self.exams:
                exam_obj = self.exams[exam_id]
                students_in_data = exam_data.get("students", {})
                if students_in_data:
                    # Convert student_id keys to UUID
                    students_with_uuid_keys = {
                        self._ensure_uuid(sid): reg_type
                        for sid, reg_type in students_in_data.items()
                    }
                    exam_obj.set_students(students_with_uuid_keys)

    def add_exam(self, exam: Exam) -> None:
        self.exams[exam.id] = exam

    def add_room(self, room: Room) -> None:
        self.rooms[room.id] = room

    def add_student(self, student: Student) -> None:
        self.students[student.id] = student

    def add_invigilator(self, invigilator: Invigilator) -> None:
        self.invigilators[invigilator.id] = invigilator

    def add_instructor(self, instructor: Instructor) -> None:
        self.instructors[instructor.id] = instructor

    def validate_problem_data(self) -> Dict[str, Any]:
        """Comprehensive problem data validation"""
        validation = {"valid": True, "errors": [], "warnings": [], "stats": {}}
        if not self.exams:
            validation["errors"].append("No exams defined")
        if not self.days:
            validation["errors"].append("No days defined")
        if not self.rooms:
            validation["errors"].append("No rooms defined")
        if not self.students:
            validation["errors"].append("No students defined")
        if validation["errors"]:
            validation["valid"] = False
        return validation

    def validate_invigilator_data(self) -> Dict[str, Any]:
        """Comprehensive invigilator data validation"""
        validation_result = {"valid": True, "errors": [], "warnings": [], "stats": {}}

        invigilators = self.invigilators
        if not invigilators:
            validation_result["valid"] = False
            validation_result["errors"].append("No invigilators available")
            return validation_result

        valid_count = 0
        invalid_count = 0
        total_capacity = 0

        for inv_id, invigilator in invigilators.items():
            try:
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

        if valid_count == 0:
            validation_result["valid"] = False
            validation_result["errors"].append("No valid invigilators found")

        return validation_result

    def _process_and_translate_locks(self, dataset: "ProblemModelCompatibleDataset"):
        """Translates high-level locks (by period) into low-level locks (by specific timeslot)."""
        if not dataset.locks:
            logger.info("No HITL locks to process.")
            self.locks = []
            return

        # 1. Create a lookup for period start times from the raw dataset
        period_id_to_start_time = {}
        for day_data in dataset.days:
            for period in day_data.get("time_periods", []):
                period_id_to_start_time[period["id"]] = time.fromisoformat(
                    period["start_time"]
                )

        # 2. Create a lookup for the generated timeslot IDs based on date and start time
        date_time_to_slot_id = {}
        for day in self.days.values():
            for slot in day.timeslots:
                date_time_to_slot_id[(day.date, slot.start_time)] = slot.id

        # 3. Process the raw locks
        processed_locks = []
        for raw_lock in dataset.locks:
            try:
                period_id = raw_lock.get("timeslot_period_id")
                lock_date_str = raw_lock.get("exam_date")

                if not period_id or not lock_date_str:
                    logger.warning(f"Skipping incomplete lock: {raw_lock}")
                    continue

                lock_date = date.fromisoformat(lock_date_str)
                start_time = period_id_to_start_time.get(period_id)

                if not start_time:
                    logger.warning(
                        f"Could not find start time for period_id {period_id} in lock. Skipping."
                    )
                    continue

                # Find the specific timeslot ID for the lock
                target_slot_id = date_time_to_slot_id.get((lock_date, start_time))

                if not target_slot_id:
                    logger.error(
                        f"Could not translate lock for date {lock_date} and time {start_time} to a specific timeslot. The timeslot may not exist. Skipping lock."
                    )
                    continue

                # Create the new lock structure that the constraint manager can use
                processed_lock = {
                    "exam_id": self._ensure_uuid(raw_lock["exam_id"]),
                    "time_slot_id": target_slot_id,
                    "room_ids": [
                        self._ensure_uuid(rid) for rid in raw_lock.get("room_ids") or []
                    ],
                }
                processed_locks.append(processed_lock)

            except Exception as e:
                logger.error(f"Failed to process lock {raw_lock}: {e}")

        self.locks = processed_locks
        logger.info(
            f"Successfully processed and translated {len(self.locks)} HITL locks."
        )
