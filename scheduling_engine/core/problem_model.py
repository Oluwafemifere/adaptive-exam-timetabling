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

# from ..data_flow_tracker import track_data_flow, DataFlowTracker

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

    def __post_init__(self):
        # This now serves as a fallback only if timeslots are not provided
        # during object creation, which the corrected problem model now does.
        if not self.timeslots:
            logger.warning(
                f"Day {self.id} is creating default timeslots as none were provided."
            )
            templates = [
                ("Morning", time(9, 0), time(12, 0)),
                ("Afternoon", time(12, 0), time(15, 0)),
                ("Evening", time(15, 0), time(18, 0)),
            ]

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

        # Ensure exactly 3 timeslots per day
        if len(self.timeslots) != 3:
            logger.warning(
                f"Day {self.id} has {len(self.timeslots)} timeslots, expected 3"
            )

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

        # Carefully handle adjacent_seat_pairs which may be null or a dictionary
        adjacent_pairs_value = data.get("adjacent_seat_pairs")
        if not isinstance(adjacent_pairs_value, list):
            if adjacent_pairs_value is not None:
                logger.warning(
                    f"Room {data.get('code', '')} has non-list adjacent_seat_pairs: {adjacent_pairs_value}. "
                    "This field is being ignored as it doesn't match the expected format List[Tuple[int, int]]."
                )
            adjacent_pairs_value = []

        return cls(
            id=uuid_obj,
            code=data.get("code", ""),
            capacity=int(data.get("capacity", 0)),
            exam_capacity=int(data.get("exam_capacity", data.get("capacity", 0))),
            has_computers=bool(data.get("has_computers", False)),
            adjacent_seat_pairs=adjacent_pairs_value,
            # --- START OF FIX: Ensure building_name is read ---
            building_name=data.get("building_name"),
            # --- END OF FIX ---
        )


@dataclass
class Student:
    id: UUID
    department: Optional[str] = None
    registered_courses: Set[UUID] = field(default_factory=set)

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

        # Handle any additional attributes from kwargs
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

    # Additional fields from backend
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

        # --- START OF FIX: Use the name provided by the data mapper ---
        # The data_preparation_service now correctly constructs the full name.
        full_name = data.get("name", f"Staff {data.get('staff_number', '')}")
        # --- END OF FIX ---

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
    department_name: Optional[str] = None
    prerequisite_exams: Set[UUID] = field(default_factory=set)
    instructor_ids: Set[UUID] = field(default_factory=set)

    def __post_init__(self):
        """Initialize internal student set"""
        self._students: Set[UUID] = set()

    @property
    def students(self) -> Set[UUID]:
        """Get students registered for this exam"""
        return self._students

    @students.setter
    def students(self, value: Set[UUID]) -> None:
        """Set students with type safety"""
        self._students = value

    @property
    def enrollment(self) -> int:
        return self.expected_students

    @property
    def duration(self) -> int:
        """Alias for duration_minutes to maintain compatibility"""
        return self.duration_minutes

    @property
    def allowed_rooms(self) -> Set[UUID]:
        return getattr(self, "_allowed_rooms", set())

    @allowed_rooms.setter
    def allowed_rooms(self, value: Set[UUID]):
        self._allowed_rooms = value

    def to_dict(self) -> Dict[str, Any]:
        """Converts the Exam object to a dictionary."""
        return {
            "id": str(self.id),
            "course_id": str(self.course_id),
            "duration_minutes": self.duration_minutes,
            "expected_students": self.expected_students,
            "is_practical": self.is_practical,
            "morning_only": self.morning_only,
            "actual_student_count": self.actual_student_count,
            "prerequisite_exams": [str(e) for e in self.prerequisite_exams],
            "students": [str(s) for s in self._students],
            "course_code": getattr(self, "course_code", "N/A"),
            "course_title": getattr(self, "course_title", "N/A"),
            "allowed_rooms": [str(r) for r in self.allowed_rooms],
            "instructor_ids": [str(inst_id) for inst_id in self.instructor_ids],
            "department_name": self.department_name,
        }

    def set_students(self, student_ids: Set[UUID]) -> None:
        """Set the complete student list for this exam"""
        self._students = set(student_ids)  # Ensure it's a set of UUIDs
        # Update expected students to match actual if not already set correctly
        if len(self._students) > self.expected_students:
            self.expected_students = len(self._students)

    def add_student(self, student_id: UUID) -> None:
        """Add a single student to this exam"""
        self._students.add(student_id)

    def remove_student(self, student_id: UUID) -> None:
        """Remove a student from this exam"""
        self._students.discard(student_id)

    def has_student(self, student_id: UUID) -> bool:
        """Check if a student is registered for this exam"""
        return student_id in self._students

    @classmethod
    def from_backend_data(cls, data: Dict[str, Any]) -> "Exam":
        """Create Exam from backend data with proper field mapping"""
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

        exam = cls(
            id=uuid_obj,
            course_id=course_uuid_obj,
            duration_minutes=int(data.get("duration_minutes", 180)),
            expected_students=int(data.get("expected_students", 0)),
            is_practical=bool(data.get("is_practical", False)),
            morning_only=bool(data.get("morning_only", False)),
        )

        # Set additional attributes
        if "students" in data and data["students"]:
            # Convert students to proper UUID set
            student_uuids = set()
            for student_id in data["students"]:
                try:
                    student_uuid = (
                        UUID(str(student_id))
                        if not isinstance(student_id, UUID)
                        else student_id
                    )
                    student_uuids.add(student_uuid)
                except Exception as e:
                    logger.error(f"Error converting student ID {student_id}: {e}")

            exam.set_students(student_uuids)

        # --- START OF FIX: Map department_name and other attributes ---
        exam.department_name = data.get("department_name")
        setattr(exam, "course_code", data.get("course_code", "N/A"))
        setattr(exam, "course_title", data.get("course_title", "N/A"))

        if "instructor_ids" in data and data["instructor_ids"]:
            exam.instructor_ids = {
                UUID(str(inst_id)) for inst_id in data["instructor_ids"]
            }
        # --- END OF FIX ---

        if "actual_student_count" in data:
            # Use actual count if it's higher than expected
            actual_count = int(data["actual_student_count"])
            if actual_count > exam.expected_students:
                exam.expected_students = actual_count

        if "allowed_rooms" in data:
            exam.allowed_rooms = data["allowed_rooms"]

        return exam


class ExamSchedulingProblem:
    """ENHANCED: Problem model with robust backend data integration"""

    def __init__(
        self,
        session_id: UUID,
        exam_period_start: date,
        exam_period_end: date,
        db_session: Optional["AsyncSession"] = None,
        deterministic_seed: Optional[int] = None,
        exam_days_count: Optional[int] = None,
    ):
        self.id = uuid4()
        self.session_id = session_id
        self.exam_period_start = exam_period_start
        self.exam_period_end = exam_period_end
        self.exam_days_count = exam_days_count

        # Core data structures
        self.holidays: Set[date] = set()
        self.days: Dict[UUID, Day] = {}
        self._date_range_configured = True
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
        self.timeslot_templates: List[Dict[str, Any]] = []

    def add_staff(self, staff: Staff) -> None:
        """Add a staff member to the problem"""
        self.staff[staff.id] = staff

    def ensure_constraints_activated(self) -> None:
        """Ensure minimum constraints are activated - called from main.py"""
        # Activate core constraints if none are active
        if not self.constraint_registry.get_active_constraints():
            self.constraint_registry.configure_basic()
            logger.info("Activated basic constraints as fallback")

    def _generate_days_with_timeslots(self) -> Dict[UUID, Day]:
        """
        FIXED: Generate days with timeslots based on loaded templates using the
        configured exam period dates.
        """
        days = {}
        current_date = self.exam_period_start
        days_generated = 0

        # Use the actual exam period to generate weekdays
        target_days = (
            self.exam_days_count
            if self.exam_days_count
            else ((self.exam_period_end - self.exam_period_start).days + 1)
        )

        logger.info(
            f"Generating weekdays from {self.exam_period_start} to {self.exam_period_end} "
            f"(target: {target_days} days)"
        )
        holidays_set = self.holidays

        while days_generated < target_days and current_date <= self.exam_period_end:
            # Only generate for weekdays and non-holidays
            if current_date.weekday() < 5 and current_date not in holidays_set:
                day_id = uuid4()
                day_timeslots = []

                # Create timeslots from the templates
                for template in self.timeslot_templates:
                    try:
                        start_t = time.fromisoformat(template["start_time"])
                        end_t = time.fromisoformat(template["end_time"])
                        duration = (end_t.hour - start_t.hour) * 60 + (
                            end_t.minute - start_t.minute
                        )

                        slot = Timeslot(
                            id=uuid4(),
                            parent_day_id=day_id,
                            name=template["name"],
                            start_time=start_t,
                            end_time=end_t,
                            duration_minutes=duration,
                        )
                        day_timeslots.append(slot)
                    except (ValueError, KeyError) as e:
                        logger.error(
                            f"Skipping invalid timeslot template {template}: {e}"
                        )
                        continue

                # Pass the generated timeslots directly to the Day constructor
                day = Day(id=day_id, date=current_date, timeslots=day_timeslots)
                days[day.id] = day
                self.day_timeslot_map[day.id] = {slot.id for slot in day.timeslots}
                days_generated += 1

            current_date += timedelta(days=1)

        # Log actual days generated
        logger.info(
            f"Generated {len(days)} days with {sum(len(day.timeslots) for day in days.values())} "
            f"total timeslots using exam period {self.exam_period_start} to {self.exam_period_end}"
        )
        return days

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

    # @track_data_flow("load_frrom_backend", include_stats=True)
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
                    try:
                        instructor = Instructor.from_backend_data(instructor_data)
                        self.add_instructor(instructor)
                    except Exception as e:
                        logger.error(
                            f"Error loading instructor {instructor_data.get('id', 'unknown')}: {e}"
                        )
                logger.info(f"✅ INSTRUCTORS: {len(self.instructors)} loaded")
            else:
                logger.warning("🟡 WARNING: No instructors loaded from dataset!")

            for entity_type, count in entities_loaded.items():
                if count == 0:
                    # Make this a warning for students/invigilators, but an error for exams/rooms
                    if entity_type in ["exams", "rooms"]:
                        logger.error(f"🔴 CRITICAL: No {entity_type} loaded!")
                    else:
                        logger.warning(f"🟡 WARNING: No {entity_type} loaded!")
                else:
                    logger.info(f"✅ {entity_type.upper()}: {count} loaded")

            # Phase 2: Relationship validation
            logger.info("📋 PHASE 2: Validating relationships...")
            self._validate_dataset_relationships(dataset, entities_loaded)

            # Phase 3: Student-exam mapping application
            logger.info("📋 PHASE 3: Applying student-exam mappings...")

            # --- START OF CRITICAL FIX ---
            # Use course_registrations from the dataset to populate the internal dictionaries.
            # This ensures constraints like MaxExamsPerStudentPerDay have the data they need.
            if dataset.course_registrations:
                logger.info(
                    f"Populating internal student-course mappings from {len(dataset.course_registrations)} registrations."
                )
                for reg in dataset.course_registrations:
                    student_id = self._ensure_uuid(reg["student_id"])
                    course_id = self._ensure_uuid(reg["course_id"])
                    if (
                        student_id in self.students and course_id
                    ):  # Check course_id exists
                        self.register_student_course(student_id, course_id)
            else:
                logger.warning(
                    "No course registrations found in the dataset to build internal mappings."
                )
            # --- END OF CRITICAL FIX ---

            if dataset.student_exam_mappings:
                self._apply_exact_student_exam_mappings(dataset.student_exam_mappings)
                self._log_exam_student_statistics()

            # This call is now supplemental to the registration data above
            self.populate_exam_students()
            if hasattr(dataset, "timeslot_templates") and dataset.timeslot_templates:
                self.timeslot_templates = dataset.timeslot_templates
                logger.info(
                    f"Loaded {len(self.timeslot_templates)} timeslot templates from dataset."
                )
            else:
                logger.warning(
                    "No timeslot templates in dataset. Falling back to hardcoded defaults."
                )
                self.timeslot_templates = [
                    {
                        "name": "Morning",
                        "start_time": "09:00:00",
                        "end_time": "12:00:00",
                    },
                    {
                        "name": "Afternoon",
                        "start_time": "12:00:00",
                        "end_time": "15:00:00",
                    },
                    {
                        "name": "Evening",
                        "start_time": "15:00:00",
                        "end_time": "18:00:00",
                    },
                ]
                # Phase 4: Day and timeslot configuration
            logger.info("📋 PHASE 4: Configuring days and timeslots...")
            self._configure_days_and_timeslots(dataset)

            # Phase 5: Final validation
            logger.info("📋 PHASE 5: Final validation...")
            validation_result = self.validate_problem_data()

            if not validation_result.get("valid", False):
                logger.error(
                    f"🔴 VALIDATION FAILED: {validation_result.get('errors', [])}"
                )

                # Attempt recovery
                logger.warning("🔧 Attempting data recovery...")
                self._attempt_data_recovery(validation_result)

            logger.info("✅ Problem model loading completed successfully")

        except Exception as e:
            logger.error(f"❌ Problem model loading failed: {e}")
            logger.error(f"📍 Stack trace: {traceback.format_exc()}")
            raise

    def _log_exam_student_statistics(self) -> None:
        """Log detailed exam-student mapping statistics"""
        logger.info("=== EXAM-STUDENT MAPPING STATISTICS ===")

        total_mappings = 0
        exams_with_students = 0
        exams_without_students = []
        student_distribution = []

        for exam_id, exam in self.exams.items():
            student_count = len(exam.students) if hasattr(exam, "students") else 0
            total_mappings += student_count

            if student_count > 0:
                exams_with_students += 1
                student_distribution.append(student_count)
            else:
                course_code = getattr(exam, "course_code", "Unknown")
                exams_without_students.append(
                    {
                        "exam_id": exam_id,
                        "course_code": course_code,
                        "expected_students": getattr(exam, "expected_students", 0),
                    }
                )

        logger.info(f"📊 MAPPING SUMMARY:")
        logger.info(f"  📈 Total mappings: {total_mappings}")
        logger.info(
            f"  ✅ Exams with students: {exams_with_students}/{len(self.exams)}"
        )
        logger.info(f"  ❌ Exams without students: {len(exams_without_students)}")

        if student_distribution:
            avg_students = sum(student_distribution) / len(student_distribution)
            min_students = min(student_distribution)
            max_students = max(student_distribution)
            logger.info(
                f"  📈 Students per exam - Min: {min_students}, Max: {max_students}, Avg: {avg_students:.1f}"
            )

        if exams_without_students:
            logger.warning(f"🚨 EXAMS WITHOUT STUDENTS:")
            for exam_info in exams_without_students[:5]:  # Log first 5
                logger.warning(
                    f"  👻 {exam_info['course_code']} (ID: {exam_info['exam_id']})"
                )

    # @track_data_flow("load_exams")
    def _load_exams(self, exam_data_list: List[Dict[str, Any]]) -> int:
        """Load exams with tracking"""
        exams_loaded = 0
        for exam_data in exam_data_list:
            try:
                self._validate_exam_data(exam_data)
                exam = Exam.from_backend_data(exam_data)
                self.add_exam(exam)
                exams_loaded += 1
            except Exception as e:
                logger.error(
                    f"Error loading exam {exam_data.get('id', 'unknown')}: {e}"
                )
                continue

        return exams_loaded

    # @track_data_flow("load_rooms")
    def _load_rooms(self, room_data_list: List[Dict[str, Any]]) -> int:
        """Load rooms with tracking"""
        rooms_loaded = 0
        for room_data in room_data_list:
            try:
                self._validate_room_data(room_data)
                room = Room.from_backend_data(room_data)
                self.add_room(room)
                rooms_loaded += 1
            except Exception as e:
                logger.error(
                    f"Error loading room {room_data.get('id', 'unknown')}: {e}"
                )
                continue

        return rooms_loaded

    def _validate_dataset_relationships(
        self, dataset: ProblemModelCompatibleDataset, entities_loaded: Dict[str, int]
    ) -> None:
        """Validate relationships between entities in the dataset"""
        validation_errors = []
        warnings = []

        # Check exam-student relationships
        if entities_loaded["exams"] > 0 and entities_loaded["students"] > 0:
            # Check if we have any student-exam mappings
            if (
                not hasattr(dataset, "student_exam_mappings")
                or not dataset.student_exam_mappings
            ):
                warnings.append("No student-exam mappings found")

            # Check if exams have students assigned
            exams_with_students = 0
            for exam in self.exams.values():
                if hasattr(exam, "_students") and exam._students:
                    exams_with_students += 1

            if exams_with_students == 0 and len(self.exams) > 0:
                warnings.append("No exams have students assigned")

        # Check room capacity vs exam requirements
        if entities_loaded["exams"] > 0 and entities_loaded["rooms"] > 0:
            max_exam_size = max(exam.expected_students for exam in self.exams.values())
            max_room_capacity = max(room.exam_capacity for room in self.rooms.values())

            if max_exam_size > max_room_capacity:
                validation_errors.append(
                    f"Largest exam ({max_exam_size} students) exceeds largest room capacity ({max_room_capacity})"
                )

        # Check invigilator coverage
        if entities_loaded["exams"] > 0 and entities_loaded["invigilators"] > 0:
            total_invigilator_capacity = sum(
                invigilator.max_students_per_exam
                for invigilator in self.invigilators.values()
            )
            total_student_exams = sum(
                exam.expected_students for exam in self.exams.values()
            )

            if total_invigilator_capacity < total_student_exams:
                warnings.append(
                    f"Insufficient invigilator capacity ({total_invigilator_capacity}) for total student exams ({total_student_exams})"
                )

        if validation_errors:
            error_msg = f"Dataset relationship validation failed: {'; '.join(validation_errors)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if warnings:
            logger.warning(f"Dataset relationship warnings: {'; '.join(warnings)}")

    def _attempt_data_recovery(self, validation_result: Dict[str, Any]) -> None:
        """Attempt to recover from data validation errors"""
        logger.warning("Attempting data recovery after validation failures...")

        recovery_actions = []

        # Fix day timeslot issues
        for day_id, day in self.days.items():
            if len(day.timeslots) != 3:
                original_count = len(day.timeslots)
                # Ensure exactly 3 timeslots
                slot_templates = [
                    ("Morning", time(9, 0), time(12, 0)),
                    ("Afternoon", time(12, 0), time(15, 0)),
                    ("Evening", time(15, 0), time(18, 0)),
                ]

                # Clear existing and create new ones
                day.timeslots.clear()
                for name, start, end in slot_templates:
                    slot = Timeslot(
                        id=uuid4(),
                        parent_day_id=day.id,
                        name=name,
                        start_time=start,
                        end_time=end,
                        duration_minutes=(end.hour - start.hour) * 60,
                    )
                    day.timeslots.append(slot)

                recovery_actions.append(
                    f"Fixed day {day_id} timeslots: {original_count} -> 3"
                )

        # Ensure minimum room capacity for exams
        if self.exams and self.rooms:
            max_exam_size = max(exam.expected_students for exam in self.exams.values())
            max_room_capacity = max(room.exam_capacity for room in self.rooms.values())

            if max_exam_size > max_room_capacity:
                # Increase room capacities temporarily
                for room in self.rooms.values():
                    if room.exam_capacity < max_exam_size:
                        room.exam_capacity = max_exam_size
                        recovery_actions.append(
                            f"Increased room {room.code} capacity to {max_exam_size}"
                        )

        # Ensure at least some invigilators if none exist
        if not self.invigilators and self.staff:
            recovery_actions.append("Creating invigilators from staff")
            for staff_member in self.staff.values():
                if getattr(staff_member, "can_invigilate", True):
                    invigilator = Invigilator.from_staff(staff_member)
                    self.add_invigilator(invigilator)

        if recovery_actions:
            logger.info(f"Data recovery actions: {recovery_actions}")
        else:
            logger.warning("No specific recovery actions were taken")

    def _validate_room_data(self, room_data: Dict[str, Any]) -> None:
        """Validate room data before loading"""
        required_fields = ["id", "code", "capacity"]
        for field in required_fields:
            if field not in room_data or room_data[field] is None:
                raise ValueError(f"Room missing required field: {field}")

        # Validate capacity values
        capacity = room_data.get("capacity", 0)
        exam_capacity = room_data.get("exam_capacity", capacity)

        if capacity <= 0:
            raise ValueError(
                f"Room {room_data['code']} has invalid capacity: {capacity}"
            )

        if exam_capacity <= 0:
            raise ValueError(
                f"Room {room_data['code']} has invalid exam capacity: {exam_capacity}"
            )

        if exam_capacity > capacity * 2:  # Allow some overbooking but not excessive
            logger.warning(
                f"Room {room_data['code']} has high exam capacity ({exam_capacity}) compared to normal capacity ({capacity})"
            )

    def _validate_student_data(self, student_data: Dict[str, Any]) -> None:
        """Validate student data before loading"""
        required_fields = ["id"]
        for field in required_fields:
            if field not in student_data or student_data[field] is None:
                raise ValueError(f"Student missing required field: {field}")

        # Validate UUID format
        try:
            student_id = student_data["id"]
            if not isinstance(student_id, UUID):
                UUID(str(student_id))
        except ValueError as e:
            raise ValueError(f"Invalid student ID format: {student_data['id']}") from e

        # Validate department if present
        department = student_data.get("department")
        if department and not isinstance(department, str):
            logger.warning(
                f"Student {student_data['id']} has non-string department: {department}"
            )

    def _validate_invigilator_data(self, invigilator_data: Dict[str, Any]) -> None:
        """Validate invigilator data before loading"""
        required_fields = ["id", "name"]
        for field in required_fields:
            if field not in invigilator_data or invigilator_data[field] is None:
                raise ValueError(f"Invigilator missing required field: {field}")

        # Validate UUID format
        try:
            invigilator_id = invigilator_data["id"]
            if not isinstance(invigilator_id, UUID):
                UUID(str(invigilator_id))
        except ValueError as e:
            raise ValueError(
                f"Invalid invigilator ID format: {invigilator_data['id']}"
            ) from e

        # Validate numerical constraints
        max_concurrent = invigilator_data.get("max_concurrent_exams", 1)
        if max_concurrent < 0:
            raise ValueError(
                f"Invigilator {invigilator_data['name']} has invalid max_concurrent_exams: {max_concurrent}"
            )

        max_students = invigilator_data.get("max_students_per_exam", 50)
        if max_students <= 0:
            raise ValueError(
                f"Invigilator {invigilator_data['name']} has invalid max_students_per_exam: {max_students}"
            )

        # Validate availability structure if present
        availability = invigilator_data.get("availability", {})
        if availability and not isinstance(availability, dict):
            logger.warning(
                f"Invigilator {invigilator_data['name']} has invalid availability format"
            )

    def _validate_dataset_completeness(
        self, dataset: ProblemModelCompatibleDataset
    ) -> None:
        """Validate that dataset contains all required components"""
        validation_errors = []

        if not dataset.exams:
            validation_errors.append("No exams in dataset")
        if not dataset.rooms:
            validation_errors.append("No rooms in dataset")
        if not dataset.students:
            validation_errors.append("No students in dataset")
        if not dataset.course_registrations:
            logger.warning("No course registrations in dataset")

        # Check for minimum required data
        if len(dataset.exams) < 1:
            validation_errors.append("At least one exam required")
        if len(dataset.rooms) < 1:
            validation_errors.append("At least one room required")

        if validation_errors:
            error_msg = f"Dataset validation failed: {'; '.join(validation_errors)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _load_entities_with_validation(
        self, dataset: ProblemModelCompatibleDataset
    ) -> Dict[str, int]:
        """Load entities with individual error handling and validation"""
        entities_loaded = {"exams": 0, "rooms": 0, "students": 0, "invigilators": 0}

        # Load exams with enhanced validation
        for exam_data in dataset.exams:
            try:
                self._validate_exam_data(exam_data)
                exam = Exam.from_backend_data(exam_data)
                self.add_exam(exam)
                entities_loaded["exams"] += 1
            except Exception as e:
                logger.error(
                    f"Error loading exam {exam_data.get('id', 'unknown')}: {e}"
                )
                continue

        # Load rooms
        for room_data in dataset.rooms:
            try:
                self._validate_room_data(room_data)
                room = Room.from_backend_data(room_data)
                self.add_room(room)
                entities_loaded["rooms"] += 1
            except Exception as e:
                logger.error(
                    f"Error loading room {room_data.get('id', 'unknown')}: {e}"
                )
                continue

        # Load students
        for student_data in dataset.students:
            try:
                self._validate_student_data(student_data)
                student = Student.from_backend_data(student_data)
                self.add_student(student)
                entities_loaded["students"] += 1
            except Exception as e:
                logger.error(
                    f"Error loading student {student_data.get('id', 'unknown')}: {e}"
                )
                continue

        # Load invigilators
        for invigilator_data in dataset.invigilators:
            try:
                self._validate_invigilator_data(invigilator_data)
                invigilator = Invigilator.from_backend_data(invigilator_data)
                self.add_invigilator(invigilator)
                entities_loaded["invigilators"] += 1
            except Exception as e:
                logger.error(
                    f"Error loading invigilator {invigilator_data.get('id', 'unknown')}: {e}"
                )
                continue

        logger.info(f"Entities loaded: {entities_loaded}")
        return entities_loaded

    def _validate_exam_data(self, exam_data: Dict[str, Any]) -> None:
        """Validate exam data before loading"""
        required_fields = ["id", "course_id", "duration_minutes"]
        for field in required_fields:
            if field not in exam_data or exam_data[field] is None:
                raise ValueError(f"Missing required field: {field}")

        if exam_data.get("expected_students", 0) < 0:
            raise ValueError("expected_students cannot be negative")

    def _configure_days_and_timeslots(
        self, dataset: ProblemModelCompatibleDataset
    ) -> None:
        """Configure days and timeslots with comprehensive fallbacks"""
        if dataset.days:
            try:
                self.days = {
                    UUID(str(day["id"])): Day(id=UUID(str(day["id"])), date=day["date"])
                    for day in dataset.days
                }

                # Add timeslots to days
                for day_data in dataset.days:
                    day_id = UUID(str(day_data["id"]))
                    day = self.days[day_id]
                    day_timeslots = set()
                    for ts_data in day_data.get("timeslots", []):
                        timeslot = Timeslot(
                            id=UUID(str(ts_data["id"])),
                            parent_day_id=UUID(str(ts_data["parent_day_id"])),
                            name=ts_data["name"],
                            start_time=ts_data["start_time"],
                            end_time=ts_data["end_time"],
                            duration_minutes=ts_data["duration_minutes"],
                        )
                        day.timeslots.append(timeslot)
                        day_timeslots.add(timeslot.id)
                    self.day_timeslot_map[day_id] = day_timeslots

                logger.info(f"Loaded {len(self.days)} days from dataset")

            except Exception as e:
                logger.error(
                    f"Error loading days from dataset: {e}, using fallback generation"
                )
                self._generate_fallback_days()
        else:
            logger.warning("No days in dataset, generating fallback days")
            self._generate_fallback_days()

    def _generate_fallback_days(self) -> None:
        """Generate fallback days when dataset doesn't provide them"""
        try:
            if self.exam_days_count:
                self.configure_exam_days(self.exam_days_count)
            else:
                # Default to 10 exam days
                self.configure_exam_days(10)
            logger.info("Generated fallback days successfully")
        except Exception as e:
            logger.error(f"Failed to generate fallback days: {e}")
            raise

    async def _attempt_dataset_recovery(
        self, dataset: ProblemModelCompatibleDataset, error_msg: str
    ) -> None:
        """Attempt to recover from dataset loading errors"""
        logger.warning(f"Attempting dataset recovery after error: {error_msg}")

        try:
            # Basic recovery: ensure we have minimal data
            if not self.exams and dataset.exams:
                logger.info("Attempting to load exams in recovery mode")
                for exam_data in dataset.exams[:10]:  # Limit to first 10 for recovery
                    try:
                        exam = Exam.from_backend_data(exam_data)
                        self.add_exam(exam)
                    except Exception:
                        continue

            if not self.rooms and dataset.rooms:
                logger.info("Attempting to load rooms in recovery mode")
                for room_data in dataset.rooms[:5]:  # Limit to first 5
                    try:
                        room = Room.from_backend_data(room_data)
                        self.add_room(room)
                    except Exception:
                        continue

            # Ensure we have days
            if not self.days:
                self._generate_fallback_days()

            logger.info("Dataset recovery completed with limited data")

        except Exception as recovery_error:
            logger.error(f"Dataset recovery failed: {recovery_error}")

    def _apply_exact_student_exam_mappings(
        self, student_exam_mappings: Dict[str, Set[str]]
    ) -> None:
        """Apply student-exam mappings with exact compatibility"""
        logger.info("Applying EXACT student-exam mappings...")

        mappings_applied = 0
        for student_id_str, exam_ids in student_exam_mappings.items():
            try:
                student_id = UUID(student_id_str)
                for exam_id_str in exam_ids:
                    exam_id = UUID(exam_id_str)
                    if exam_id in self.exams:
                        self.exams[exam_id].add_student(student_id)
                        mappings_applied += 1
            except Exception as e:
                logger.error(f"Error applying mapping student {student_id_str}: {e}")

        logger.info(f"Applied {mappings_applied} exact student-exam mappings")

    def _generate_days_based_on_period(self) -> None:
        """Generate days based on the exam period dates"""
        if not self._date_range_configured:
            logger.warning("Date range not configured, using default generation")
            # Ensure we have valid dates
            if not self.exam_period_start or not self.exam_period_end:
                self.exam_period_start = date.today() + timedelta(days=30)
                self.exam_period_end = self.exam_period_start + timedelta(days=14)

            self._date_range_configured = True

    def get_room_capacity_info(self, room_id: UUID) -> Dict[str, Any]:
        """Get detailed capacity information for a room"""
        room = self.rooms.get(room_id)
        if not room:
            return {}

        return {
            "id": room.id,
            "code": room.code,
            "normal_capacity": room.capacity,
            "exam_capacity": room.exam_capacity,
            "has_computers": room.has_computers,
            "overbookable": getattr(room, "overbookable", False),
        }

    def get_exam_student_info(self, exam_id: UUID) -> Dict[str, Any]:
        """Get detailed student information for an exam"""
        exam = self.exams.get(exam_id)
        if not exam:
            return {}

        return {
            "id": exam.id,
            "course_id": exam.course_id,
            "expected_students": exam.expected_students,
            "actual_students": len(exam.students) if hasattr(exam, "students") else 0,
            "duration_minutes": exam.duration_minutes,
            "is_practical": exam.is_practical,
            "course_code": getattr(exam, "course_code", "N/A"),
            "course_title": getattr(exam, "course_title", "N/A"),
        }

    def get_capacity_utilization_stats(self) -> Dict[str, Any]:
        """Get capacity utilization statistics for the problem"""
        total_room_capacity = sum(room.exam_capacity for room in self.rooms.values())
        total_student_exams = sum(
            len(exam.students)
            for exam in self.exams.values()
            if hasattr(exam, "students")
        )

        if total_room_capacity == 0:
            utilization = 0
        else:
            utilization = (total_student_exams / total_room_capacity) * 100

        return {
            "total_room_capacity": total_room_capacity,
            "total_student_exams": total_student_exams,
            "utilization_percentage": utilization,
            "rooms_count": len(self.rooms),
            "exams_count": len(self.exams),
        }

    def configure_exam_days(self, days_count: int) -> None:
        """Configure the number of exam days and regenerate day structure"""
        if days_count <= 0:
            raise ValueError(f"days_count must be positive, got {days_count}")

        logger.info(f"Configuring exam schedule for {days_count} days")

        # Ensure date range is configured
        self._generate_days_based_on_period()

        self.exam_days_count = days_count
        self.day_timeslot_map.clear()
        self.days = self._generate_days_with_timeslots()

        # CRITICAL FIX: If no days were generated, create default days
        if not self.days:
            logger.warning(
                f"No days generated with normal method. Creating {days_count} default days."
            )
            self.days = self._create_default_days(days_count)

        logger.info(
            f"Generated {len(self.days)} days with {len(self.timeslots)} total timeslots"
        )

        # Clear cache to force recomputation
        self.timeslots_cache = None
        self.timeslot_to_day = None

    def _create_default_days(self, days_count: int) -> Dict[UUID, Day]:
        """Create default days as fallback when normal generation fails"""
        days = {}
        start_date = self.exam_period_start or date.today()

        for i in range(days_count):
            day_date = start_date + timedelta(days=i)
            day = Day(id=uuid4(), date=day_date)
            days[day.id] = day
            self.day_timeslot_map[day.id] = {slot.id for slot in day.timeslots}

        logger.info(f"Created {len(days)} default days as fallback")
        return days

    def _ensure_uuid(self, value: Any) -> UUID:
        """Ensure a value is a UUID object, converting from string if necessary"""
        if isinstance(value, UUID):
            return value
        elif isinstance(value, str):
            try:
                return UUID(value)
            except ValueError:
                # Generate a deterministic UUID from the string for invalid UUIDs
                from hashlib import md5

                return UUID(md5(value.encode()).hexdigest()[:32])
        else:
            # For other types, try to convert to string first
            try:
                return self._ensure_uuid(str(value))
            except:
                # Final fallback: generate a random UUID
                from uuid import uuid4

                return uuid4()

    def _apply_exam_student_data(self, exam_data_list: List[Dict[str, Any]]) -> None:
        """Apply student data directly from exam objects in dataset"""
        logger.info("Applying exam student data from dataset...")

        for exam_data in exam_data_list:
            try:
                exam_id = UUID(str(exam_data["id"]))

                if exam_id in self.exams:
                    exam_obj = self.exams[exam_id]

                    # Get students from exam data
                    students_in_data = exam_data.get("students", set())
                    actual_student_count = exam_data.get("actual_student_count", 0)

                    if students_in_data:
                        # Convert string UUIDs to UUID objects and add to exam
                        student_uuids = set()
                        for student_id_str in students_in_data:
                            try:
                                student_uuid = UUID(str(student_id_str))
                                student_uuids.add(student_uuid)
                                exam_obj.add_student(student_uuid)
                            except Exception as e:
                                logger.error(
                                    f"Error converting student ID {student_id_str}: {e}"
                                )

                        logger.debug(
                            f"Added {len(student_uuids)} students to exam {exam_id}"
                        )

                    # Update expected students if we have actual count
                    if actual_student_count > exam_obj.expected_students:
                        exam_obj.expected_students = actual_student_count
                        logger.debug(
                            f"Updated expected students for exam {exam_id} to {actual_student_count}"
                        )

            except Exception as e:
                logger.error(
                    f"Error applying student data for exam {exam_data.get('id', 'unknown')}: {e}"
                )

    def _populate_exam_students_from_mappings(
        self, student_exam_mappings: Dict[str, Set[str]]
    ) -> None:
        """Populate exam students using pre-computed mappings"""
        logger.info("Populating exam students from mappings...")

        for student_id_str, exam_id_set in student_exam_mappings.items():
            try:
                student_id = UUID(student_id_str)

                for exam_id_str in exam_id_set:
                    try:
                        exam_id = UUID(exam_id_str)

                        if exam_id in self.exams:
                            self.exams[exam_id].add_student(student_id)

                    except Exception as e:
                        logger.error(
                            f"Error mapping student {student_id_str} to exam {exam_id_str}: {e}"
                        )
                        continue

            except Exception as e:
                logger.error(f"Error processing student mapping {student_id_str}: {e}")
                continue

        # Update expected students based on actual registrations
        for exam in self.exams.values():
            if hasattr(exam, "_students") and exam._students:
                exam.expected_students = len(exam._students)

        total_mappings = sum(len(exam._students) for exam in self.exams.values())
        logger.info(f"Populated {total_mappings} student-exam mappings from dataset")

    def add_exam(self, exam: Exam) -> None:
        self.exams[exam.id] = exam

    def add_room(self, room: Room) -> None:
        self.rooms[room.id] = room

    def add_student(self, student: Student) -> None:
        self.students[student.id] = student

    def add_invigilator(self, invigilator: Invigilator) -> None:
        """Add an invigilator to the problem"""
        self.invigilators[invigilator.id] = invigilator

    def add_instructor(self, instructor: Instructor) -> None:
        """Add an Instructor to the problem"""
        self.instructors[instructor.id] = instructor

    def register_student_course(self, student_id: UUID, course_id: UUID) -> None:
        """Register student-course relationship with UUIDs"""
        self._student_courses[student_id].add(course_id)
        self.course_students[course_id].add(student_id)

    def populate_exam_students(self):
        """Populate exam students using pre-mapped data from dataset - FIXED VERSION"""
        logger.info("Populating exam students using pre-mapped data...")

        students_added = 0
        exams_with_students = 0

        # FIXED: Handle case where no exams exist
        if not self.exams:
            logger.warning("No exams available to populate students")
            return False

        for exam in self.exams.values():
            # Check if exam has pre-populated students from dataset
            if hasattr(exam, "_students") and exam._students:
                # Students are already populated from dataset
                student_count = len(exam._students)
                if student_count > 0:
                    exams_with_students += 1
                    students_added += student_count
                    logger.debug(f"Exam {exam.id} already has {student_count} students")
                continue

            # Fallback: Try to find students via course registrations
            course_id = exam.course_id
            if course_id in self.course_students:
                student_ids = self.course_students[course_id]
                exam.set_students(student_ids)
                student_count = len(student_ids)
                if student_count > 0:
                    exams_with_students += 1
                    students_added += student_count
                    logger.info(
                        f"Exam {exam.id} (course {course_id}) has {student_count} students"
                    )
                else:
                    logger.warning(
                        f"Exam {exam.id} (course {course_id}) has no students via course registrations"
                    )
            else:
                logger.warning(
                    f"Exam {exam.id} (course {course_id}) not found in course registrations"
                )

        logger.info(
            f"Student population complete: {exams_with_students}/{len(self.exams)} exams have students, {students_added} total assignments"
        )

        # FIXED: Don't fail completely if some exams have no students
        if exams_with_students == 0 and len(self.exams) > 0:
            logger.error("CRITICAL: No exams have students assigned!")
            return False
        elif exams_with_students < len(self.exams):
            logger.warning(
                f"{len(self.exams) - exams_with_students} exams have no students"
            )

        return True

    def get_students_for_course(self, course_id: UUID) -> Set[UUID]:
        """Get all students registered for a specific course"""
        return self.course_students.get(course_id, set())

    def get_courses_for_student(self, student_id: UUID) -> Set[UUID]:
        """Get all courses a student is registered for"""
        return self._student_courses.get(student_id, set())

    def get_students_for_exam(self, exam_id: UUID) -> Set[UUID]:
        """Get students registered for the course of this exam"""
        exam = self.exams[exam_id]
        return self.course_students.get(exam.course_id, set())

    def validate_problem_data(self) -> Dict[str, Any]:
        """Comprehensive problem data validation"""
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

        # Student-course mapping validation
        total_registrations = sum(
            len(courses) for courses in self._student_courses.values()
        )
        if total_registrations == 0 and len(self.students) > 0:
            validation["warnings"].append("No student-course registrations found")
        validation["stats"]["student_registrations"] = total_registrations

        # Invigilator validation
        inv_validation = self.validate_invigilator_data()
        validation["valid"] = validation["valid"] and inv_validation["valid"]
        validation["errors"].extend(inv_validation["errors"])
        validation["warnings"].extend(inv_validation["warnings"])
        validation["stats"]["invigilators"] = inv_validation["stats"]

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
