# scheduling_engine/core/solution.py

"""
Solution representation for exam timetabling.
Handles complete and partial solutions, validation, and quality metrics.
Integrated with backend data retrieval services.
"""

from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum

try:
    # Import backend services for data validation
    from app.services.data_retrieval import (
        SchedulingData,
        AcademicData,
        InfrastructureData,
        ConflictAnalysis,
    )

    BACKEND_AVAILABLE = True
except ImportError:
    BACKEND_AVAILABLE = False

from ..config import get_logger
from .problem_model import ExamSchedulingProblem
from scheduling_engine.core.constraint_types import ConstraintSeverity

logger = get_logger("core.solution")


class SolutionStatus(Enum):
    """Status of a timetable solution"""

    INCOMPLETE = "incomplete"
    FEASIBLE = "feasible"
    OPTIMAL = "optimal"
    INFEASIBLE = "infeasible"
    INVALID = "invalid"


class AssignmentStatus(Enum):
    """Status of individual exam assignments"""

    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"
    CONFLICT = "conflict"
    INVALID = "invalid"


@dataclass
class ExamAssignment:
    """Represents the assignment of an exam to time slot and rooms"""

    exam_id: UUID
    time_slot_id: Optional[UUID] = None
    room_ids: List[UUID] = field(default_factory=list)
    assigned_date: Optional[date] = None

    # Assignment metadata
    status: AssignmentStatus = AssignmentStatus.UNASSIGNED
    assignment_priority: float = 0.0
    conflicts: List[str] = field(default_factory=list)

    # Capacity allocation per room
    room_allocations: Dict[UUID, int] = field(default_factory=dict)

    # Backend integration - store assignment data compatible with backend models
    backend_data: Dict[str, Any] = field(default_factory=dict)

    def is_complete(self) -> bool:
        """Check if assignment is complete (has time slot and at least one room)"""
        return (
            self.time_slot_id is not None
            and len(self.room_ids) > 0
            and self.assigned_date is not None
        )

    def get_total_capacity(self) -> int:
        """Get total allocated capacity across all rooms"""
        return sum(self.room_allocations.values())

    def add_room_allocation(self, room_id: UUID, capacity: int) -> None:
        """Add room allocation to the assignment"""
        if room_id not in self.room_ids:
            self.room_ids.append(room_id)
        self.room_allocations[room_id] = capacity

    def to_backend_format(self) -> Dict[str, Any]:
        """Convert assignment to format compatible with backend services"""
        return {
            "exam_id": str(self.exam_id),
            "time_slot_id": str(self.time_slot_id) if self.time_slot_id else None,
            "exam_date": self.assigned_date.isoformat() if self.assigned_date else None,
            "room_assignments": [
                {
                    "room_id": str(room_id),
                    "allocated_capacity": self.room_allocations.get(room_id, 0),
                    "is_primary": i == 0,  # First room is primary
                }
                for i, room_id in enumerate(self.room_ids)
            ],
            "status": "scheduled" if self.is_complete() else "pending",
        }


@dataclass
class ConflictReport:
    """Represents a conflict in the timetable"""

    conflict_id: UUID
    conflict_type: str
    severity: ConstraintSeverity  # "high", "medium", "low"
    affected_exams: List[UUID]
    affected_students: List[UUID] = field(default_factory=list)
    affected_resources: List[UUID] = field(default_factory=list)
    description: str = ""
    resolution_suggestions: List[str] = field(default_factory=list)

    # Backend integration
    constraint_violation_type: Optional[str] = None
    backend_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SolutionStatistics:
    """Statistics about the solution quality"""

    total_exams: int = 0
    assigned_exams: int = 0
    unassigned_exams: int = 0

    # Conflict statistics
    hard_constraint_violations: int = 0
    soft_constraint_violations: int = 0
    student_conflicts: int = 0
    room_conflicts: int = 0
    time_conflicts: int = 0

    # Quality metrics
    room_utilization_percentage: float = 0.0
    time_slot_utilization_percentage: float = 0.0
    student_satisfaction_score: float = 0.0

    # Performance metrics
    solution_time_seconds: float = 0.0
    iterations_required: int = 0
    memory_usage_mb: float = 0.0

    # Backend-specific metrics
    faculty_distribution: Dict[str, int] = field(default_factory=dict)
    department_distribution: Dict[str, int] = field(default_factory=dict)
    practical_exam_allocation: Dict[str, int] = field(default_factory=dict)


class TimetableSolution:
    """
    Complete solution representation for exam timetabling.
    Integrated with backend data retrieval services.
    """

    def __init__(
        self,
        problem: ExamSchedulingProblem,
        solution_id: Optional[UUID] = None,
        session_data: Optional[Dict[str, Any]] = None,
    ):
        self.id = solution_id or uuid4()
        self.problem = problem
        self.created_at = datetime.now()
        self.last_modified = datetime.now()

        # Backend integration
        self.session_data = session_data or {}
        self.session_id = problem.session_id

        # Solution data
        self.assignments: Dict[UUID, ExamAssignment] = {}
        self.status = SolutionStatus.INCOMPLETE

        # Quality metrics
        self.objective_value: float = float("inf")
        self.fitness_score: float = 0.0
        self.constraint_violations: Dict[str, int] = {}

        # Conflict tracking
        self.conflicts: Dict[UUID, ConflictReport] = {}
        self.statistics = SolutionStatistics()

        # Solver metadata
        self.solver_phase: Optional[str] = None
        self.generation: int = 0
        self.parent_solutions: List[UUID] = []

        # Backend service integration
        self.backend_services: Dict[str, Any] = {}

        # Initialize empty assignments for all exams
        for exam_id in problem.exams.keys():
            self.assignments[exam_id] = ExamAssignment(exam_id=exam_id)

        logger.debug(
            f"Created TimetableSolution {self.id} for session {self.session_id} "
            f"with {len(self.assignments)} exam slots"
        )

    def set_backend_services(self, session) -> None:
        """Initialize backend services for data validation and retrieval"""
        if BACKEND_AVAILABLE:
            try:
                # Re-import here to ensure availability
                from app.services.data_retrieval import (
                    SchedulingData,
                    AcademicData,
                    InfrastructureData,
                    ConflictAnalysis,
                )

                self.backend_services = {
                    "scheduling_data": SchedulingData(session),
                    "academic_data": AcademicData(session),
                    "infrastructure_data": InfrastructureData(session),
                    "conflict_analysis": ConflictAnalysis(session),
                }
            except Exception as e:
                logger.warning(f"Could not initialize backend services: {e}")

    async def validate_with_backend(self) -> Dict[str, Any]:
        """Validate solution using backend data and constraints"""
        if not BACKEND_AVAILABLE or not self.backend_services:
            return {"valid": True, "warnings": ["Backend validation not available"]}

        validation_result: Dict[str, Any] = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "room_conflicts": [],
            "student_conflicts": [],
        }

        try:
            # Get current scheduling data for validation
            scheduling_data = await self.backend_services[
                "scheduling_data"
            ].get_scheduling_data_for_session(self.session_id)

            # Validate room assignments
            room_validation = await self._validate_room_assignments(scheduling_data)
            validation_result.update(room_validation)

            # Validate student conflicts using backend conflict analysis
            student_conflicts = await self.backend_services[
                "conflict_analysis"
            ].get_student_conflicts(str(self.session_id))

            if student_conflicts:
                validation_result["student_conflicts"] = list(student_conflicts.keys())
                validation_result["warnings"].append(
                    f"Found {len(student_conflicts)} students with potential conflicts"
                )

        except Exception as e:
            logger.error(f"Backend validation failed: {e}")
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation error: {str(e)}")

        return validation_result

    async def _validate_room_assignments(
        self, scheduling_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate room assignments against backend room data"""
        validation: Dict[str, List[str]] = {"errors": [], "warnings": []}

        rooms_data = {r["id"]: r for r in scheduling_data.get("rooms", [])}

        for assignment in self.assignments.values():
            if not assignment.is_complete():
                continue

            exam = self.problem.exams[assignment.exam_id]

            for room_id in assignment.room_ids:
                room_str_id = str(room_id)
                if room_str_id not in rooms_data:
                    validation["errors"].append(
                        f"Room {room_id} not found in backend data"
                    )
                    continue

                room_data = rooms_data[room_str_id]
                room_capacity = room_data.get(
                    "exam_capacity", room_data.get("capacity", 0)
                )
                allocated_capacity = assignment.room_allocations.get(room_id, 0)

                # Check capacity constraints
                if allocated_capacity > room_capacity:
                    validation["errors"].append(
                        f"Room {room_data.get('code', room_id)} capacity exceeded: "
                        f"{allocated_capacity} > {room_capacity}"
                    )

                # Check practical exam requirements
                if exam.is_practical and not room_data.get("has_computers", False):
                    validation["errors"].append(
                        f"Practical exam {exam.course_code} assigned to room {room_data.get('code', room_id)} "
                        f"without computers"
                    )

                # Check morning-only constraint
                if exam.morning_only and assignment.time_slot_id:
                    time_slot = self.problem.time_slots.get(assignment.time_slot_id)
                    if time_slot and time_slot.start_time.hour >= 12:
                        validation["warnings"].append(
                            f"Morning-only exam {exam.course_code} scheduled after noon"
                        )

        return validation

    def assign_exam(
        self,
        exam_id: UUID,
        time_slot_id: UUID,
        room_ids: List[UUID],
        assigned_date: date,
        room_allocations: Optional[Dict[UUID, int]] = None,
    ) -> bool:
        """
        Assign an exam to specific time slot and rooms.
        Returns True if assignment was successful.
        """
        try:
            if exam_id not in self.assignments:
                logger.error(f"Exam {exam_id} not found in solution")
                return False

            # Create assignment
            assignment = ExamAssignment(
                exam_id=exam_id,
                time_slot_id=time_slot_id,
                room_ids=room_ids.copy(),
                assigned_date=assigned_date,
                status=AssignmentStatus.ASSIGNED,
            )

            # Set room allocations
            if room_allocations:
                assignment.room_allocations = room_allocations.copy()
            else:
                # Default equal allocation
                exam = self.problem.exams[exam_id]
                capacity_per_room = exam.expected_students // len(room_ids)
                remainder = exam.expected_students % len(room_ids)

                for i, room_id in enumerate(room_ids):
                    allocation = capacity_per_room + (1 if i < remainder else 0)
                    assignment.room_allocations[room_id] = allocation

            # Store backend-compatible data
            assignment.backend_data = assignment.to_backend_format()

            self.assignments[exam_id] = assignment
            self.last_modified = datetime.now()

            # Validate assignment
            self._validate_assignment(assignment)

            logger.debug(f"Assigned exam {exam_id} to time slot {time_slot_id}")
            return True

        except Exception as e:
            logger.error(f"Error assigning exam {exam_id}: {e}")
            return False

    def unassign_exam(self, exam_id: UUID) -> bool:
        """Remove assignment for an exam"""
        try:
            if exam_id in self.assignments:
                self.assignments[exam_id] = ExamAssignment(exam_id=exam_id)
                self.last_modified = datetime.now()
                logger.debug(f"Unassigned exam {exam_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error unassigning exam {exam_id}: {e}")
            return False

    def _validate_assignment(self, assignment: ExamAssignment) -> None:
        """Validate a specific assignment and update conflicts"""
        exam = self.problem.exams[assignment.exam_id]
        conflicts = []

        # Check room capacity
        total_allocated = assignment.get_total_capacity()
        if total_allocated < exam.expected_students:
            conflicts.append(
                f"Insufficient capacity: {total_allocated} < {exam.expected_students}"
            )

        # Check room features for practical exams
        if exam.is_practical:
            for room_id in assignment.room_ids:
                room = self.problem.rooms.get(room_id)
                if room and not room.has_computers:
                    conflicts.append(
                        f"Practical exam requires computers in room {room.code}"
                    )

        # Check morning-only constraint
        if exam.morning_only and assignment.time_slot_id:
            time_slot = self.problem.time_slots.get(assignment.time_slot_id)
            if time_slot and time_slot.start_time.hour >= 12:
                conflicts.append("Morning-only exam scheduled in afternoon")

        # Check resource requirement (gi from research paper)
        resource_requirement = exam.get_resource_requirement()
        if total_allocated < resource_requirement:
            conflicts.append(
                f"Resource requirement not met: {total_allocated} < {resource_requirement}"
            )

        # Update assignment status
        if conflicts:
            assignment.status = AssignmentStatus.CONFLICT
            assignment.conflicts = conflicts
        else:
            assignment.status = AssignmentStatus.ASSIGNED

    def detect_conflicts(self) -> List[ConflictReport]:
        """Detect all conflicts in the current solution"""
        conflicts = []

        # Student conflicts (same student, overlapping exams)
        student_conflicts = self._detect_student_conflicts()
        conflicts.extend(student_conflicts)

        # Room conflicts (same room, overlapping times)
        room_conflicts = self._detect_room_conflicts()
        conflicts.extend(room_conflicts)

        # Time slot conflicts
        time_conflicts = self._detect_time_conflicts()
        conflicts.extend(time_conflicts)

        # Faculty-specific conflicts
        faculty_conflicts = self._detect_faculty_conflicts()
        conflicts.extend(faculty_conflicts)

        # Update conflicts dictionary
        self.conflicts = {conflict.conflict_id: conflict for conflict in conflicts}

        return conflicts

    def _detect_student_conflicts(self) -> List[ConflictReport]:
        """Detect student scheduling conflicts using problem model data"""
        conflicts = []

        # Group assignments by time slot and date
        time_assignments: Dict[Tuple[date, UUID], List[ExamAssignment]] = {}

        for assignment in self.assignments.values():
            if (
                assignment.is_complete()
                and assignment.assigned_date
                and assignment.time_slot_id
            ):
                key = (assignment.assigned_date, assignment.time_slot_id)
                if key not in time_assignments:
                    time_assignments[key] = []
                time_assignments[key].append(assignment)

        # Check for student conflicts within each time slot
        for (exam_date, time_slot_id), assignments_in_slot in time_assignments.items():
            if len(assignments_in_slot) <= 1:
                continue

            # Find students registered for multiple exams in this slot
            for i, assignment1 in enumerate(assignments_in_slot):
                for assignment2 in assignments_in_slot[i + 1 :]:
                    students1 = self.problem.get_students_for_exam(assignment1.exam_id)
                    students2 = self.problem.get_students_for_exam(assignment2.exam_id)

                    conflicted_students = students1.intersection(students2)

                    if conflicted_students:
                        exam1 = self.problem.exams[assignment1.exam_id]
                        exam2 = self.problem.exams[assignment2.exam_id]

                        conflict = ConflictReport(
                            conflict_id=uuid4(),
                            conflict_type="student_conflict",
                            severity=ConstraintSeverity.HIGH,
                            affected_exams=[assignment1.exam_id, assignment2.exam_id],
                            affected_students=list(conflicted_students),
                            description=f"{len(conflicted_students)} students have conflicting exams "
                            f"({exam1.course_code and exam2.course_code})",
                            resolution_suggestions=[
                                "Move one exam to a different time slot",
                                "Split exam into multiple sessions",
                            ],
                            constraint_violation_type="student_overlap",
                        )
                        conflicts.append(conflict)

        return conflicts

    def _detect_room_conflicts(self) -> List[ConflictReport]:
        """Detect room double-booking conflicts"""
        conflicts = []

        # Group assignments by room and time
        room_assignments: Dict[Tuple[UUID, date, UUID], List[ExamAssignment]] = {}

        for assignment in self.assignments.values():
            if (
                assignment.is_complete()
                and assignment.assigned_date
                and assignment.time_slot_id
            ):
                for room_id in assignment.room_ids:
                    key = (room_id, assignment.assigned_date, assignment.time_slot_id)
                    if key not in room_assignments:
                        room_assignments[key] = []
                    room_assignments[key].append(assignment)

        # Check for double bookings
        for (room_id, exam_date, time_slot_id), assignments in room_assignments.items():
            if len(assignments) > 1:
                room = self.problem.rooms.get(room_id)
                room_code = room.code if room else str(room_id)

                conflict = ConflictReport(
                    conflict_id=uuid4(),
                    conflict_type="room_conflict",
                    severity=ConstraintSeverity.HIGH,
                    affected_exams=[a.exam_id for a in assignments],
                    affected_resources=[room_id],
                    description=f"Room {room_code} double-booked for {len(assignments)} exams",
                    resolution_suggestions=[
                        "Assign conflicting exams to different rooms",
                        "Move one exam to a different time slot",
                    ],
                    constraint_violation_type="room_overlap",
                )
                conflicts.append(conflict)

        return conflicts

    def _detect_time_conflicts(self) -> List[ConflictReport]:
        """Detect time-related conflicts including precedence violations"""
        conflicts = []

        # Check precedence constraints
        for assignment in self.assignments.values():
            if (
                not assignment.is_complete()
                or not assignment.assigned_date
                or not assignment.time_slot_id
            ):
                continue

            exam = self.problem.exams[assignment.exam_id]

            # Check if any prerequisite exams are scheduled after this exam
            for prereq_exam_id in exam.prerequisite_exams:
                if prereq_exam_id in self.assignments:
                    prereq_assignment = self.assignments[prereq_exam_id]
                    if (
                        prereq_assignment.is_complete()
                        and prereq_assignment.assigned_date
                        and prereq_assignment.time_slot_id
                    ):
                        # Compare scheduling times
                        exam_time_slot = self.problem.time_slots.get(
                            assignment.time_slot_id
                        )
                        prereq_time_slot = self.problem.time_slots.get(
                            prereq_assignment.time_slot_id
                        )

                        if exam_time_slot and prereq_time_slot:
                            exam_datetime = datetime.combine(
                                assignment.assigned_date,
                                exam_time_slot.start_time,
                            )
                            prereq_datetime = datetime.combine(
                                prereq_assignment.assigned_date,
                                prereq_time_slot.start_time,
                            )

                            if prereq_datetime >= exam_datetime:
                                prereq_exam = self.problem.exams[prereq_exam_id]
                                conflict = ConflictReport(
                                    conflict_id=uuid4(),
                                    conflict_type="precedence_conflict",
                                    severity=ConstraintSeverity.HIGH,
                                    affected_exams=[assignment.exam_id, prereq_exam_id],
                                    description=f"Prerequisite exam {prereq_exam.course_code} "
                                    f"scheduled after {exam.course_code}",
                                    resolution_suggestions=[
                                        "Reschedule prerequisite exam earlier",
                                        "Move dependent exam to later time",
                                    ],
                                    constraint_violation_type="precedence_violation",
                                )
                                conflicts.append(conflict)

        return conflicts

    def _detect_faculty_conflicts(self) -> List[ConflictReport]:
        """Detect faculty-specific conflicts"""
        conflicts = []

        # Group exams by faculty
        faculty_assignments: Dict[UUID, List[ExamAssignment]] = {}

        for assignment in self.assignments.values():
            if assignment.is_complete():
                exam = self.problem.exams[assignment.exam_id]
                if exam.faculty_id:
                    if exam.faculty_id not in faculty_assignments:
                        faculty_assignments[exam.faculty_id] = []
                    faculty_assignments[exam.faculty_id].append(assignment)

        # Check for faculty-level constraint violations
        for faculty_id, assignments in faculty_assignments.items():
            faculty = self.problem.faculties.get(faculty_id)
            if not faculty:
                continue

            # Check concurrent exam limits
            time_groups: Dict[Tuple[date, UUID], List[ExamAssignment]] = {}
            for assignment in assignments:
                if assignment.assigned_date and assignment.time_slot_id:
                    key = (assignment.assigned_date, assignment.time_slot_id)
                    if key not in time_groups:
                        time_groups[key] = []
                    time_groups[key].append(assignment)

            for (
                exam_date,
                time_slot_id,
            ), concurrent_assignments in time_groups.items():
                if len(concurrent_assignments) > faculty.max_concurrent_exams:
                    conflict = ConflictReport(
                        conflict_id=uuid4(),
                        conflict_type="faculty_overload",
                        severity=ConstraintSeverity.MEDIUM,
                        affected_exams=[a.exam_id for a in concurrent_assignments],
                        description=f"Faculty {faculty.name} has {len(concurrent_assignments)} "
                        f"concurrent exams (limit: {faculty.max_concurrent_exams})",
                        resolution_suggestions=[
                            "Reschedule some exams to different time slots",
                            "Distribute exams across multiple sessions",
                        ],
                        constraint_violation_type="faculty_capacity_exceeded",
                    )
                    conflicts.append(conflict)

        return conflicts

    def calculate_objective_value(self) -> float:
        """
        Calculate objective value based on Total Weighted Tardiness (TWT).
        Enhanced with backend data integration.
        """
        total_twt = 0.0

        for assignment in self.assignments.values():
            if not assignment.is_complete():
                # Unassigned exams get penalty
                exam = self.problem.exams[assignment.exam_id]
                total_twt += exam.weight * 1000  # High penalty for unassigned
                continue

            exam = self.problem.exams[assignment.exam_id]

            # Calculate tardiness if due date is specified
            if exam.due_date and assignment.assigned_date and assignment.time_slot_id:
                time_slot = self.problem.time_slots.get(assignment.time_slot_id)
                if time_slot:
                    exam_datetime = datetime.combine(
                        assignment.assigned_date,
                        time_slot.start_time,
                    )

                    if exam_datetime > exam.due_date:
                        tardiness = (
                            exam_datetime - exam.due_date
                        ).total_seconds() / 3600  # Hours
                        total_twt += exam.weight * tardiness

            # Add workload penalty (from research paper)
            workload_penalty = exam.get_workload() * 0.1
            total_twt += workload_penalty

        self.objective_value = total_twt
        return total_twt

    def calculate_fitness_score(self) -> float:
        """
        Calculate fitness score for genetic algorithm.
        Enhanced with multi-objective considerations.
        """
        if self.objective_value == float("inf"):
            self.fitness_score = 0.0
        else:
            # Base fitness from objective value
            base_fitness = 1.0 / (1.0 + self.objective_value)

            # Bonus for completion rate
            completion_bonus = self.get_completion_percentage() / 100.0

            # Penalty for conflicts
            conflicts = self.detect_conflicts()
            conflict_penalty = len(conflicts) * 0.01

            # Final fitness score
            self.fitness_score = max(
                0.0, base_fitness + completion_bonus - conflict_penalty
            )

        return self.fitness_score

    def update_statistics(self) -> None:
        """Update solution statistics with backend data integration"""
        self.statistics.total_exams = len(self.assignments)
        self.statistics.assigned_exams = sum(
            1 for a in self.assignments.values() if a.is_complete()
        )
        self.statistics.unassigned_exams = (
            self.statistics.total_exams - self.statistics.assigned_exams
        )

        # Count conflicts
        conflicts = self.detect_conflicts()
        self.statistics.student_conflicts = len(
            [c for c in conflicts if c.conflict_type == "student_conflict"]
        )
        self.statistics.room_conflicts = len(
            [c for c in conflicts if c.conflict_type == "room_conflict"]
        )
        self.statistics.time_conflicts = len(
            [c for c in conflicts if c.conflict_type == "precedence_conflict"]
        )

        # Calculate utilization metrics
        self._calculate_utilization_metrics()

        # Calculate backend-specific metrics
        self._calculate_backend_metrics()

    def _calculate_utilization_metrics(self) -> None:
        """Calculate room and time slot utilization"""
        if not self.problem.rooms or not self.problem.time_slots:
            return

        # Room utilization
        used_rooms = set()
        for assignment in self.assignments.values():
            if assignment.is_complete():
                used_rooms.update(assignment.room_ids)

        self.statistics.room_utilization_percentage = (
            len(used_rooms) / len(self.problem.rooms) * 100
        )

        # Time slot utilization
        used_time_slots = set()
        for assignment in self.assignments.values():
            if assignment.is_complete() and assignment.time_slot_id:
                used_time_slots.add(assignment.time_slot_id)

        self.statistics.time_slot_utilization_percentage = (
            len(used_time_slots) / len(self.problem.time_slots) * 100
        )

    def _calculate_backend_metrics(self) -> None:
        """Calculate backend-specific distribution metrics"""
        # Faculty distribution
        faculty_counts: Dict[str, int] = {}
        department_counts: Dict[str, int] = {}
        practical_counts: Dict[str, int] = {}

        for assignment in self.assignments.values():
            if assignment.is_complete():
                exam = self.problem.exams[assignment.exam_id]

                # Faculty distribution
                if exam.faculty_id:
                    faculty = self.problem.faculties.get(exam.faculty_id)
                    if faculty:
                        faculty_name = faculty.name
                        faculty_counts[faculty_name] = (
                            faculty_counts.get(faculty_name, 0) + 1
                        )

                # Department distribution
                if exam.department_id:
                    department = self.problem.departments.get(exam.department_id)
                    if department:
                        dept_name = department.name
                        department_counts[dept_name] = (
                            department_counts.get(dept_name, 0) + 1
                        )

                # Practical exam allocation
                if exam.is_practical:
                    for room_id in assignment.room_ids:
                        room = self.problem.rooms.get(room_id)
                        if room:
                            room_type = (
                                "computer_lab" if room.has_computers else "regular"
                            )
                            practical_counts[room_type] = (
                                practical_counts.get(room_type, 0) + 1
                            )

        self.statistics.faculty_distribution = faculty_counts
        self.statistics.department_distribution = department_counts
        self.statistics.practical_exam_allocation = practical_counts

    def export_to_backend_format(self) -> Dict[str, Any]:
        """Export solution in format compatible with backend services"""
        backend_assignments = []

        for assignment in self.assignments.values():
            if assignment.is_complete():
                backend_assignments.append(assignment.to_backend_format())

        return {
            "solution_id": str(self.id),
            "session_id": str(self.session_id),
            "status": self.status.value,
            "objective_value": self.objective_value,
            "fitness_score": self.fitness_score,
            "assignments": backend_assignments,
            "statistics": {
                "total_exams": self.statistics.total_exams,
                "assigned_exams": self.statistics.assigned_exams,
                "completion_percentage": self.get_completion_percentage(),
                "conflict_count": len(self.conflicts),
                "room_utilization": self.statistics.room_utilization_percentage,
                "time_utilization": self.statistics.time_slot_utilization_percentage,
                "faculty_distribution": self.statistics.faculty_distribution,
                "department_distribution": self.statistics.department_distribution,
            },
            "conflicts": [
                {
                    "conflict_id": str(conflict.conflict_id),
                    "type": conflict.conflict_type,
                    "severity": conflict.severity,
                    "description": conflict.description,
                    "affected_exams": [str(eid) for eid in conflict.affected_exams],
                    "affected_students": [
                        str(sid) for sid in conflict.affected_students
                    ],
                    "affected_resources": [
                        str(rid) for rid in conflict.affected_resources
                    ],
                }
                for conflict in self.conflicts.values()
            ],
            "created_at": self.created_at.isoformat(),
            "last_modified": self.last_modified.isoformat(),
        }

    def is_feasible(self) -> bool:
        """Check if solution is feasible (no hard constraint violations)"""
        conflicts = self.detect_conflicts()
        hard_conflicts = [c for c in conflicts if c.severity == "high"]
        return len(hard_conflicts) == 0

    def is_complete(self) -> bool:
        """Check if all exams are assigned"""
        return all(assignment.is_complete() for assignment in self.assignments.values())

    def get_completion_percentage(self) -> float:
        """Get percentage of exams that are assigned"""
        if not self.assignments:
            return 0.0

        assigned_count = sum(1 for a in self.assignments.values() if a.is_complete())
        return (assigned_count / len(self.assignments)) * 100

    def copy(self) -> "TimetableSolution":
        """Create a deep copy of the solution"""
        new_solution = TimetableSolution(
            self.problem, solution_id=uuid4(), session_data=self.session_data.copy()
        )

        # Copy assignments
        for exam_id, assignment in self.assignments.items():
            new_assignment = ExamAssignment(
                exam_id=assignment.exam_id,
                time_slot_id=assignment.time_slot_id,
                room_ids=assignment.room_ids.copy(),
                assigned_date=assignment.assigned_date,
                status=assignment.status,
                assignment_priority=assignment.assignment_priority,
                conflicts=assignment.conflicts.copy(),
                room_allocations=assignment.room_allocations.copy(),
                backend_data=assignment.backend_data.copy(),
            )
            new_solution.assignments[exam_id] = new_assignment

        # Copy metadata
        new_solution.status = self.status
        new_solution.objective_value = self.objective_value
        new_solution.fitness_score = self.fitness_score
        new_solution.solver_phase = self.solver_phase
        new_solution.generation = self.generation
        new_solution.parent_solutions = self.parent_solutions.copy()
        new_solution.backend_services = self.backend_services

        return new_solution

    def to_dict(self) -> Dict[str, Any]:
        """Convert solution to dictionary for serialization"""
        return {
            "id": str(self.id),
            "problem_id": str(self.problem.id),
            "session_id": str(self.session_id),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_modified": self.last_modified.isoformat(),
            "objective_value": self.objective_value,
            "fitness_score": self.fitness_score,
            "completion_percentage": self.get_completion_percentage(),
            "is_feasible": self.is_feasible(),
            "assignments": {
                str(exam_id): {
                    "exam_id": str(assignment.exam_id),
                    "time_slot_id": (
                        str(assignment.time_slot_id)
                        if assignment.time_slot_id
                        else None
                    ),
                    "room_ids": [str(rid) for rid in assignment.room_ids],
                    "assigned_date": (
                        assignment.assigned_date.isoformat()
                        if assignment.assigned_date
                        else None
                    ),
                    "status": assignment.status.value,
                    "total_capacity": assignment.get_total_capacity(),
                    "conflicts": assignment.conflicts,
                    "room_allocations": {
                        str(room_id): capacity
                        for room_id, capacity in assignment.room_allocations.items()
                    },
                }
                for exam_id, assignment in self.assignments.items()
            },
            "statistics": {
                "total_exams": self.statistics.total_exams,
                "assigned_exams": self.statistics.assigned_exams,
                "unassigned_exams": self.statistics.unassigned_exams,
                "student_conflicts": self.statistics.student_conflicts,
                "room_conflicts": self.statistics.room_conflicts,
                "time_conflicts": self.statistics.time_conflicts,
                "room_utilization_percentage": self.statistics.room_utilization_percentage,
                "time_slot_utilization_percentage": self.statistics.time_slot_utilization_percentage,
                "faculty_distribution": self.statistics.faculty_distribution,
                "department_distribution": self.statistics.department_distribution,
                "practical_exam_allocation": self.statistics.practical_exam_allocation,
            },
            "conflicts": {
                str(conflict_id): {
                    "conflict_id": str(conflict.conflict_id),
                    "conflict_type": conflict.conflict_type,
                    "severity": conflict.severity,
                    "affected_exams": [str(eid) for eid in conflict.affected_exams],
                    "affected_students": [
                        str(sid) for sid in conflict.affected_students
                    ],
                    "affected_resources": [
                        str(rid) for rid in conflict.affected_resources
                    ],
                    "description": conflict.description,
                    "resolution_suggestions": conflict.resolution_suggestions,
                    "constraint_violation_type": conflict.constraint_violation_type,
                }
                for conflict_id, conflict in self.conflicts.items()
            },
            "solver_metadata": {
                "solver_phase": self.solver_phase,
                "generation": self.generation,
                "parent_solutions": [str(pid) for pid in self.parent_solutions],
            },
        }
