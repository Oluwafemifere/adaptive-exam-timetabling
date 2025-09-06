# scheduling_engine/core/problem_model.py

"""
Enhanced Problem Model with Database Integration

Problem model for exam scheduling with comprehensive database integration
for constraint loading and configuration management.
"""

from __future__ import annotations
from typing import Dict, List, Set, Optional, Any, TYPE_CHECKING, Tuple
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from datetime import datetime, time, date
from enum import Enum
import logging
from collections import defaultdict

# Type checking imports
if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.services.data_retrieval import (
        SchedulingData,
        AcademicData,
        InfrastructureData,
        ConflictAnalysis,
        ConstraintData,
    )
    from app.services.scheduling.data_preparation_service import (
        DataPreparationService,
        PreparedDataset,
    )
    from .constraint_registry import BaseConstraint, ConstraintRegistry
    from .constraint_registry import (
        ConstraintDefinition,
        ConstraintType,
        ConstraintCategory,
        ConstraintViolation,
        ConstraintSeverity,
    )


# Runtime imports with fallback
try:
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.services.data_retrieval import (
        SchedulingData,
        AcademicData,
        InfrastructureData,
        ConflictAnalysis,
        ConstraintData,
    )
    from app.services.scheduling.data_preparation_service import (
        DataPreparationService,
        PreparedDataset,
    )

    BACKEND_AVAILABLE = True
except ImportError:
    BACKEND_AVAILABLE = False


logger = logging.getLogger(__name__)


class ExamType(Enum):
    """Types of exams"""

    REGULAR = "regular"
    MAKEUP = "makeup"
    CARRYOVER = "carryover"
    SUPPLEMENTARY = "supplementary"


class ResourceType(Enum):
    """Types of resources"""

    ROOM = "room"
    INVIGILATOR = "invigilator"
    EQUIPMENT = "equipment"
    TIME_SLOT = "time_slot"


@dataclass
class TimeSlot:
    """Represents an available time slot for scheduling exams"""

    id: UUID
    name: str
    start_time: time
    end_time: time
    duration_minutes: int
    date: Optional[date] = None
    is_active: bool = True
    earliest_start: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.earliest_start is None and self.date:
            self.earliest_start = datetime.combine(self.date, self.start_time)

    @classmethod
    def from_backend_data(cls, data: Dict[str, Any]) -> TimeSlot:
        """Create TimeSlot from backend data"""
        start_time_str = data.get("start_time", "09:00")
        end_time_str = data.get("end_time", "12:00")
        start_hour, start_min = map(int, start_time_str.split(":"))
        end_hour, end_min = map(int, end_time_str.split(":"))

        return cls(
            id=UUID(data["id"]),
            name=data.get("name", ""),
            start_time=time(start_hour, start_min),
            end_time=time(end_hour, end_min),
            duration_minutes=int(data.get("duration_minutes", 180)),
            is_active=bool(data.get("is_active", True)),
        )


@dataclass
class Room:
    """Represents a physical room for conducting exams"""

    id: UUID
    code: str
    name: str
    capacity: int
    exam_capacity: int
    building_id: Optional[UUID] = None
    room_type_id: Optional[UUID] = None
    has_projector: bool = False
    has_ac: bool = False
    has_computers: bool = False
    is_accessible: bool = True
    floor_number: int = 1
    is_active: bool = True

    def get_effective_capacity(self, exam_type: ExamType = ExamType.REGULAR) -> int:
        """Get effective capacity based on exam type"""
        if exam_type == ExamType.CARRYOVER:
            return min(self.exam_capacity // 2, self.capacity // 2)
        return self.exam_capacity

    @classmethod
    def from_backend_data(cls, data: Dict[str, Any]) -> Room:
        """Create Room from backend data"""
        return cls(
            id=UUID(data["id"]),
            code=data.get("code", ""),
            name=data.get("name", ""),
            capacity=int(data.get("capacity", 0)),
            exam_capacity=int(data.get("exam_capacity", data.get("capacity", 0))),
            has_projector=bool(data.get("has_projector", False)),
            has_ac=bool(data.get("has_ac", False)),
            has_computers=bool(data.get("has_computers", False)),
            is_active=bool(data.get("is_active", True)),
        )


@dataclass
class Staff:
    """Represents staff member for invigilation"""

    id: UUID
    staff_number: str
    staff_type: str
    position: str
    department_id: Optional[UUID] = None
    can_invigilate: bool = True
    max_daily_sessions: int = 2
    max_consecutive_sessions: int = 2
    is_active: bool = True

    @classmethod
    def from_backend_data(cls, data: Dict[str, Any]) -> Staff:
        """Create Staff from backend data"""
        dept_id = None
        if data.get("department_id"):
            try:
                dept_id = UUID(data["department_id"])
            except Exception:
                dept_id = None

        return cls(
            id=UUID(data["id"]),
            staff_number=data.get("staff_number", ""),
            staff_type=data.get("staff_type", ""),
            position=data.get("position", ""),
            department_id=dept_id,
            can_invigilate=bool(data.get("can_invigilate", True)),
            max_daily_sessions=int(data.get("max_daily_sessions", 2)),
            max_consecutive_sessions=int(data.get("max_consecutive_sessions", 2)),
            is_active=bool(data.get("is_active", True)),
        )


@dataclass
class Student:
    """Represents a student with course registrations"""

    id: UUID
    matric_number: str
    programme_id: UUID
    current_level: int
    registered_courses: Set[UUID] = field(default_factory=set)
    special_needs: bool = False
    preferred_times: List[UUID] = field(default_factory=list)

    def has_conflict(self, exam1_course: UUID, exam2_course: UUID) -> bool:
        """Check if student has conflict between two course exams"""
        return (
            exam1_course in self.registered_courses
            and exam2_course in self.registered_courses
        )

    @classmethod
    def from_backend_data(cls, data: Dict[str, Any]) -> Student:
        """Create Student from backend data"""
        return cls(
            id=UUID(data["id"]),
            matric_number=data.get("matric_number", ""),
            programme_id=UUID(data["programme_id"]),
            current_level=int(data.get("current_level", 100)),
            special_needs=bool(data.get("special_needs", False)),
        )


@dataclass
class Exam:
    """Enhanced exam representation with database integration"""

    id: UUID
    course_id: UUID
    course_code: str
    course_title: str
    department_id: Optional[UUID] = None
    faculty_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    time_slot_id: Optional[UUID] = None
    exam_type: ExamType = ExamType.REGULAR
    duration_minutes: int = 180
    expected_students: int = 0
    exam_date: Optional[date] = None
    status: str = "pending"
    preferred_time_slots: List[UUID] = field(default_factory=list)
    required_room_features: Dict[str, bool] = field(default_factory=dict)
    is_practical: bool = False
    morning_only: bool = False
    requires_special_arrangements: bool = False
    weight: float = 1.0
    due_date: Optional[datetime] = None
    release_time: Optional[datetime] = None
    prerequisite_exams: Set[UUID] = field(default_factory=set)
    assigned_time_slot: Optional[UUID] = None
    assigned_rooms: List[UUID] = field(default_factory=list)
    assigned_date: Optional[date] = None

    def get_processing_time(self) -> int:
        """Get processing time"""
        return int(self.duration_minutes)

    def get_workload(self) -> float:
        """Calculate workload based on students and duration"""
        return float(self.expected_students * (self.duration_minutes / 60.0))

    def get_resource_requirement(self) -> int:
        """Get resource requirement"""
        return int(self.expected_students)

    def has_precedence(self, other_exam: Exam) -> bool:
        """Check if this exam has precedence over another"""
        return other_exam.id in self.prerequisite_exams

    @classmethod
    def from_backend_data(cls, data: Dict[str, Any]) -> Exam:
        """Create Exam from backend data"""
        # Parse dates and UUIDs safely
        exam_date = None
        if data.get("exam_date"):
            if isinstance(data["exam_date"], str):
                try:
                    exam_date = date.fromisoformat(data["exam_date"])
                except Exception:
                    exam_date = None
            elif isinstance(data["exam_date"], date):
                exam_date = data["exam_date"]

        faculty_id = None
        session_id = None
        dept_id = None
        time_slot_id = None

        for id_field, target in [
            ("faculty_id", "faculty_id"),
            ("session_id", "session_id"),
            ("department_id", "dept_id"),
            ("time_slot_id", "time_slot_id"),
        ]:
            if data.get(id_field):
                try:
                    locals()[target] = UUID(data[id_field])
                except Exception:
                    locals()[target] = None

        return cls(
            id=UUID(data["id"]),
            course_id=UUID(data["course_id"]),
            course_code=data.get("course_code", ""),
            course_title=data.get("course_title", ""),
            department_id=dept_id,
            faculty_id=faculty_id,
            session_id=session_id,
            time_slot_id=time_slot_id,
            duration_minutes=int(data.get("duration_minutes", 180)),
            expected_students=int(data.get("expected_students", 0)),
            exam_date=exam_date,
            status=data.get("status", "pending"),
            is_practical=bool(data.get("is_practical", False)),
            morning_only=bool(data.get("morning_only", False)),
            requires_special_arrangements=bool(
                data.get("requires_special_arrangements", False)
            ),
        )


@dataclass
class Faculty:
    """Represents an academic faculty"""

    id: UUID
    code: str
    name: str
    departments: List[UUID] = field(default_factory=list)
    is_active: bool = True
    max_concurrent_exams: int = 10
    preferred_time_blocks: List[UUID] = field(default_factory=list)

    @classmethod
    def from_backend_data(cls, data: Dict[str, Any]) -> Faculty:
        """Create Faculty from backend data"""
        return cls(
            id=UUID(data["id"]),
            code=data.get("code", ""),
            name=data.get("name", ""),
            is_active=bool(data.get("is_active", True)),
        )


@dataclass
class Department:
    """Represents an academic department"""

    id: UUID
    code: str
    name: str
    faculty_id: UUID
    is_active: bool = True
    avoid_time_slots: List[UUID] = field(default_factory=list)

    @classmethod
    def from_backend_data(cls, data: Dict[str, Any]) -> Department:
        """Create Department from backend data"""
        return cls(
            id=UUID(data["id"]),
            code=data.get("code", ""),
            name=data.get("name", ""),
            faculty_id=UUID(data["faculty_id"]),
            is_active=bool(data.get("is_active", True)),
        )


@dataclass
class CourseRegistration:
    """Represents a student's course registration"""

    id: UUID
    student_id: UUID
    course_id: UUID
    session_id: UUID
    registration_type: str = "regular"
    registered_at: Optional[datetime] = None

    @classmethod
    def from_backend_data(cls, data: Dict[str, Any]) -> CourseRegistration:
        """Create CourseRegistration from backend data"""
        registered_at = None
        if data.get("registered_at"):
            if isinstance(data["registered_at"], str):
                try:
                    registered_at = datetime.fromisoformat(
                        data["registered_at"].replace("Z", "+00:00")
                    )
                except Exception:
                    registered_at = None
            elif isinstance(data["registered_at"], datetime):
                registered_at = data["registered_at"]

        return cls(
            id=UUID(data["id"]),
            student_id=UUID(data["student_id"]),
            course_id=UUID(data["course_id"]),
            session_id=UUID(data["session_id"]),
            registration_type=data.get("registration_type", "regular"),
            registered_at=registered_at,
        )


class ExamSchedulingProblem:
    """
    Enhanced exam scheduling problem with database constraint integration.

    Provides comprehensive constraint management with database-driven
    configuration support for pluggable constraints.
    """

    def __init__(
        self,
        session_id: UUID,
        session_name: str = "",
        exam_period_start: Optional[date] = None,
        exam_period_end: Optional[date] = None,
        db_session: Optional[AsyncSession] = None,
        configuration_id: Optional[UUID] = None,
    ) -> None:
        self.id = uuid4()
        self.session_id = session_id
        self.session_name = session_name
        self.exam_period_start = exam_period_start
        self.exam_period_end = exam_period_end
        self.configuration_id = configuration_id

        # Database session for data retrieval
        self.db_session = db_session

        # Initialize data services if database session provided
        self.data_prep_service: Optional[DataPreparationService] = None
        self.scheduling_data: Optional[SchedulingData] = None
        self.academic_data: Optional[AcademicData] = None
        self.infrastructure_data: Optional[InfrastructureData] = None
        self.conflict_analysis: Optional[ConflictAnalysis] = None
        self.constraint_data_service: Optional[ConstraintData] = None

        if BACKEND_AVAILABLE and self.db_session is not None:
            try:
                self.data_prep_service = DataPreparationService(self.db_session)
                self.scheduling_data = SchedulingData(self.db_session)
                self.academic_data = AcademicData(self.db_session)
                self.infrastructure_data = InfrastructureData(self.db_session)
                self.conflict_analysis = ConflictAnalysis(self.db_session)
                self.constraint_data_service = ConstraintData(self.db_session)
            except Exception as e:
                logger.warning(f"Could not initialize all backend services: {e}")

        # Core entities (using dictionaries for efficient lookup)
        self.exams: Dict[UUID, Exam] = {}
        self.time_slots: Dict[UUID, TimeSlot] = {}
        self.rooms: Dict[UUID, Room] = {}
        self.students: Dict[UUID, Student] = {}
        self.faculties: Dict[UUID, Faculty] = {}
        self.departments: Dict[UUID, Department] = {}
        self.staff: Dict[UUID, Staff] = {}
        self.course_registrations: Dict[UUID, CourseRegistration] = {}

        # Enhanced constraint management with database integration
        self.constraint_registry: ConstraintRegistry = ConstraintRegistry(db_session)
        self.active_constraints: List[BaseConstraint] = []
        self.constraint_configuration: Dict[str, Any] = {}

        # Indices for efficient lookup
        self._student_course_map: Dict[UUID, Set[UUID]] = {}
        self._course_student_map: Dict[UUID, Set[UUID]] = {}
        self._faculty_exams: Dict[UUID, Set[UUID]] = {}
        self._department_exams: Dict[UUID, Set[UUID]] = {}
        self._staff_unavailability: Dict[UUID, List[Dict[str, Any]]] = defaultdict(list)

        logger.info(
            f"Created ExamSchedulingProblem for session {session_name} with constraint integration"
        )

    async def load_constraints_from_database(
        self, configuration_id: Optional[UUID] = None
    ) -> None:
        """Load constraints from database configuration"""
        if not self.constraint_data_service:
            logger.warning(
                "Cannot load constraints - constraint data service not available"
            )
            return

        try:
            target_config_id = configuration_id or self.configuration_id

            if target_config_id:
                # Load constraints for specific configuration
                await self.constraint_registry.load_from_database(target_config_id)
                constraints = await self.constraint_registry.get_active_constraints_for_configuration(
                    target_config_id
                )

                self.active_constraints = constraints

                # Validate configuration using the new method that accepts UUID
                validation = await self.constraint_registry.validate_constraint_configuration_by_id(
                    target_config_id
                )

                if not validation["valid"]:
                    logger.error(
                        f"Invalid constraint configuration: {validation['errors']}"
                    )
                    raise ValueError(
                        f"Invalid constraint configuration: {validation['errors']}"
                    )

                logger.info(
                    f"Loaded {len(self.active_constraints)} constraints from database configuration"
                )

            else:
                # Load default constraint set
                await self.constraint_registry.load_from_database()
                logger.info(
                    "Loaded constraint definitions from database without specific configuration"
                )

        except Exception as e:
            logger.error(f"Error loading constraints from database: {e}")
            raise

    def add_constraint(self, constraint: BaseConstraint) -> None:
        """Add constraint to active set"""
        if constraint not in self.active_constraints:
            self.active_constraints.append(constraint)
            logger.info(f"Added constraint: {constraint.name}")

    def remove_constraint(self, constraint_id: str) -> bool:
        """Remove constraint from active set"""
        for i, constraint in enumerate(self.active_constraints):
            if constraint.constraint_id == constraint_id:
                removed = self.active_constraints.pop(i)
                logger.info(f"Removed constraint: {removed.name}")
                return True
        return False

    def get_active_constraints_by_type(
        self, constraint_type: ConstraintType
    ) -> List[BaseConstraint]:
        """Get active constraints by type"""
        return [
            c
            for c in self.active_constraints
            if c.constraint_type == constraint_type and c.is_active
        ]

    def get_hard_constraints(self) -> List[BaseConstraint]:
        """Get active hard constraints"""
        return self.get_active_constraints_by_type(ConstraintType.HARD)

    def get_soft_constraints(self) -> List[BaseConstraint]:
        """Get active soft constraints"""
        return self.get_active_constraints_by_type(ConstraintType.SOFT)

    async def initialize_constraints(self) -> None:
        """Initialize all active constraints with problem data"""
        for constraint in self.active_constraints:
            try:
                if not getattr(constraint, "_initialized", False):
                    constraint.initialize(self)
                    logger.debug(f"Initialized constraint: {constraint.name}")
            except Exception as e:
                logger.error(f"Error initializing constraint {constraint.name}: {e}")
                raise

    async def load_from_backend(self) -> None:
        """Load complete problem data including constraints from backend"""
        if not self.data_prep_service:
            raise ValueError("Database session required for backend data loading")

        try:
            logger.info(f"Loading problem data for session {self.session_id}")

            # Load core scheduling data
            dataset = await self.data_prep_service.build_dataset(self.session_id)
            await self._load_from_dataset(dataset)

            # Load constraints from database
            await self.load_constraints_from_database()

            # Initialize constraints with loaded data
            await self.initialize_constraints()

            # Build indices
            self._build_indices()

            logger.info(
                f"Successfully loaded problem with {len(self.exams)} exams, "
                f"{len(self.students)} students, {len(self.rooms)} rooms, "
                f"{len(self.active_constraints)} active constraints"
            )

        except Exception as e:
            logger.error(f"Failed to load problem data from backend: {e}")
            raise

    async def _load_from_dataset(self, dataset: PreparedDataset) -> None:
        """Load data from PreparedDataset into problem model objects"""
        if not dataset:
            return

        # Load all entity types
        for exam_data in getattr(dataset, "exams", []):
            exam = Exam.from_backend_data(exam_data)
            self.add_exam(exam)

        for slot_data in getattr(dataset, "time_slots", []):
            time_slot = TimeSlot.from_backend_data(slot_data)
            self.time_slots[time_slot.id] = time_slot

        for room_data in getattr(dataset, "rooms", []):
            room = Room.from_backend_data(room_data)
            self.rooms[room.id] = room

        for staff_data in getattr(dataset, "staff", []):
            staff = Staff.from_backend_data(staff_data)
            self.staff[staff.id] = staff

        for reg_data in getattr(dataset, "course_registrations", []):
            registration = CourseRegistration.from_backend_data(reg_data)
            self.course_registrations[registration.id] = registration
            self.add_student_registration(
                registration.student_id, registration.course_id
            )

    def add_exam(self, exam: Exam) -> None:
        """Add exam to problem with indexing"""
        self.exams[exam.id] = exam

        # Update faculty and department indices
        if exam.faculty_id:
            if exam.faculty_id not in self._faculty_exams:
                self._faculty_exams[exam.faculty_id] = set()
            self._faculty_exams[exam.faculty_id].add(exam.id)

        if exam.department_id:
            if exam.department_id not in self._department_exams:
                self._department_exams[exam.department_id] = set()
            self._department_exams[exam.department_id].add(exam.id)

    def add_student_registration(self, student_id: UUID, course_id: UUID) -> None:
        """Add student-course registration with indexing"""
        # Update student-course mapping
        if student_id not in self._student_course_map:
            self._student_course_map[student_id] = set()
        self._student_course_map[student_id].add(course_id)

        # Update course-student mapping
        if course_id not in self._course_student_map:
            self._course_student_map[course_id] = set()
        self._course_student_map[course_id].add(student_id)

    def get_students_for_exam(self, exam_id: UUID) -> Set[UUID]:
        """Get set of student IDs registered for an exam"""
        exam = self.exams.get(exam_id)
        if not exam:
            return set()
        return self._course_student_map.get(exam.course_id, set())

    def get_exam_conflicts(self) -> List[Tuple[UUID, UUID]]:
        """Get list of conflicting exam pairs (students registered for both)"""
        conflicts = []
        exam_list = list(self.exams.keys())

        for i, exam1_id in enumerate(exam_list):
            for exam2_id in exam_list[i + 1 :]:
                exam1 = self.exams[exam1_id]
                exam2 = self.exams[exam2_id]

                students1 = self._course_student_map.get(exam1.course_id, set())
                students2 = self._course_student_map.get(exam2.course_id, set())

                # Check for student overlap
                if students1.intersection(students2):
                    conflicts.append((exam1_id, exam2_id))

        return conflicts

    def get_capacity_utilization_ratio(self) -> float:
        """Calculate capacity utilization ratio"""
        total_room_capacity = sum(room.exam_capacity for room in self.rooms.values())
        total_students = sum(exam.expected_students for exam in self.exams.values())

        if total_room_capacity == 0:
            return 0.0

        # Account for multiple time slots
        num_slots = len(self.time_slots)
        effective_capacity = total_room_capacity * num_slots

        return min(total_students / effective_capacity, 1.0)

    def get_problem_complexity_score(self) -> float:
        """Calculate problem complexity score"""
        # Base complexity from number of entities
        entity_complexity = (
            len(self.exams) * 0.1
            + len(self.students) * 0.01
            + len(self.rooms) * 0.05
            + len(self.time_slots) * 0.02
        )

        # Conflict complexity
        conflicts = self.get_exam_conflicts()
        conflict_complexity = len(conflicts) * 0.001

        # Constraint complexity (including database constraints)
        constraint_complexity = len(self.active_constraints) * 0.05

        # Capacity pressure
        capacity_ratio = self.get_capacity_utilization_ratio()
        capacity_complexity = min(capacity_ratio, 2.0) * 0.2

        return float(
            entity_complexity
            + conflict_complexity
            + constraint_complexity
            + capacity_complexity
        )

    def _build_indices(self) -> None:
        """Build lookup indices for efficient access"""
        # Clear existing indices
        self._student_course_map.clear()
        self._course_student_map.clear()
        self._faculty_exams.clear()
        self._department_exams.clear()

        # Rebuild from registrations
        for registration in self.course_registrations.values():
            self.add_student_registration(
                registration.student_id, registration.course_id
            )

        # Rebuild exam indices
        for exam in self.exams.values():
            if exam.faculty_id:
                if exam.faculty_id not in self._faculty_exams:
                    self._faculty_exams[exam.faculty_id] = set()
                self._faculty_exams[exam.faculty_id].add(exam.id)

            if exam.department_id:
                if exam.department_id not in self._department_exams:
                    self._department_exams[exam.department_id] = set()
                self._department_exams[exam.department_id].add(exam.id)

    async def refresh_from_backend(self) -> None:
        """Refresh problem data including constraints from backend"""
        if not self.data_prep_service:
            raise ValueError("Database session required for backend refresh")

        logger.info(f"Refreshing problem data for session {self.session_id}")

        # Clear existing data
        self.exams.clear()
        self.time_slots.clear()
        self.rooms.clear()
        self.students.clear()
        self.staff.clear()
        self.course_registrations.clear()
        self.active_constraints.clear()

        # Clear indices
        self._student_course_map.clear()
        self._course_student_map.clear()
        self._faculty_exams.clear()
        self._department_exams.clear()
        self._staff_unavailability.clear()

        # Refresh constraint registry
        await self.constraint_registry.refresh_database_constraints()

        # Reload from backend
        await self.load_from_backend()

    def get_constraint_summary(self) -> Dict[str, Any]:
        """Get summary of constraint configuration"""
        hard_constraints = self.get_hard_constraints()
        soft_constraints = self.get_soft_constraints()

        return {
            "total_constraints": len(self.active_constraints),
            "hard_constraints": len(hard_constraints),
            "soft_constraints": len(soft_constraints),
            "database_driven": bool(self.constraint_data_service),
            "configuration_id": (
                str(self.configuration_id) if self.configuration_id else None
            ),
            "constraint_codes": [c.constraint_id for c in self.active_constraints],
            "constraint_weights": {
                c.constraint_id: c.weight for c in self.active_constraints
            },
            "registry_statistics": self.constraint_registry.get_constraint_statistics(),
        }

    async def apply_constraint_configuration(
        self, configuration_id: UUID, validate: bool = True
    ) -> Dict[str, Any]:
        """Apply a specific constraint configuration"""
        self.configuration_id = configuration_id

        try:
            # Load and validate configuration using the new method
            if validate:
                validation = await self.constraint_registry.validate_constraint_configuration_by_id(
                    configuration_id
                )
                if not validation["valid"]:
                    raise ValueError(f"Invalid configuration: {validation['errors']}")

            # Load constraints for configuration
            constraints = (
                await self.constraint_registry.get_active_constraints_for_configuration(
                    configuration_id
                )
            )

            # Replace active constraints
            self.active_constraints = constraints

            # Initialize constraints if problem data is loaded
            if self.exams:
                await self.initialize_constraints()

            result = {
                "success": True,
                "constraints_loaded": len(constraints),
                "configuration_id": str(configuration_id),
                "constraint_summary": self.get_constraint_summary(),
            }

            logger.info(f"Applied constraint configuration {configuration_id}")
            return result

        except Exception as e:
            logger.error(f"Error applying constraint configuration: {e}")
            raise

    def export_for_solver(self) -> Dict[str, Any]:
        """Export problem data with constraint information for solvers"""
        base_export = {
            "problem_id": str(self.id),
            "session_id": str(self.session_id),
            "configuration_id": (
                str(self.configuration_id) if self.configuration_id else None
            ),
            "exams": [
                {
                    "id": str(exam.id),
                    "course_id": str(exam.course_id),
                    "course_code": exam.course_code,
                    "duration_minutes": exam.duration_minutes,
                    "expected_students": exam.expected_students,
                    "is_practical": exam.is_practical,
                    "morning_only": exam.morning_only,
                    "gp_terminals": self.extract_gp_terminals(exam.id),
                }
                for exam in self.exams.values()
            ],
            "time_slots": [
                {
                    "id": str(slot.id),
                    "name": slot.name,
                    "start_time": slot.start_time.isoformat(),
                    "end_time": slot.end_time.isoformat(),
                    "duration_minutes": slot.duration_minutes,
                }
                for slot in self.time_slots.values()
            ],
            "rooms": [
                {
                    "id": str(room.id),
                    "code": room.code,
                    "capacity": room.capacity,
                    "exam_capacity": room.exam_capacity,
                    "has_computers": room.has_computers,
                    "has_projector": room.has_projector,
                }
                for room in self.rooms.values()
            ],
            "conflicts": [
                {"exam1": str(e1), "exam2": str(e2)}
                for e1, e2 in self.get_exam_conflicts()
            ],
            "constraints": [
                {
                    "id": constraint.constraint_id,
                    "name": constraint.name,
                    "type": constraint.constraint_type.value,
                    "weight": constraint.weight,
                    "is_active": constraint.is_active,
                    "parameters": constraint.parameters,
                    "database_driven": bool(getattr(constraint, "database_config", {})),
                }
                for constraint in self.active_constraints
            ],
            "metrics": {
                "complexity_score": self.get_problem_complexity_score(),
                "capacity_utilization": self.get_capacity_utilization_ratio(),
                "total_conflicts": len(self.get_exam_conflicts()),
                "constraint_summary": self.get_constraint_summary(),
            },
        }

        return base_export

    def extract_gp_terminals(self, exam_id: UUID) -> Dict[str, Any]:
        """Extract GP terminals for an exam (from research paper)"""
        exam = self.exams.get(exam_id)
        if not exam:
            return {}

        return {
            "processing_time": exam.get_processing_time(),  # PT
            "weight": exam.weight,  # W
            "resource_requirement": exam.get_resource_requirement(),  # gi
            "due_date": exam.due_date.isoformat() if exam.due_date else None,  # DD
            "earliest_start": (
                exam.release_time.isoformat() if exam.release_time else None
            ),  # ES
            "workload": exam.get_workload(),
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        db_session: Optional[AsyncSession] = None,
        configuration_id: Optional[UUID] = None,
    ) -> ExamSchedulingProblem:
        """Create problem instance from dictionary data with constraint support"""
        problem = cls(
            session_id=UUID(data["session_id"]),
            session_name=data.get("session_name", ""),
            db_session=db_session,
            configuration_id=configuration_id,
        )

        # Load data from dictionary
        for exam_data in data.get("exams", []):
            exam = Exam.from_backend_data(exam_data)
            problem.add_exam(exam)

        for slot_data in data.get("time_slots", []):
            time_slot = TimeSlot.from_backend_data(slot_data)
            problem.time_slots[time_slot.id] = time_slot

        for room_data in data.get("rooms", []):
            room = Room.from_backend_data(room_data)
            problem.rooms[room.id] = room

        for reg_data in data.get("course_registrations", []):
            registration = CourseRegistration.from_backend_data(reg_data)
            problem.course_registrations[registration.id] = registration
            problem.add_student_registration(
                registration.student_id, registration.course_id
            )

        problem._build_indices()
        return problem


@dataclass
class ProblemComplexity:
    """Represents the complexity analysis of a scheduling problem"""

    exams: int
    rooms: int
    time_slots: int
    constraints: int
    registrations: int
    complexity_score: float
    level: str  # "low", "medium", "high", "extreme"
    faculty_balance: float = 0.5
    resource_contention: float = 0.5
