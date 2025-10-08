# scheduling_engine/core/solution.py
# FIXED Solution representation with UUID-only implementation
# MODIFIED for UUID-only usage AND proper room sharing validation
# Key Fixes:
# 1. Keep all internal processing with UUID keys
# 2. Only convert UUIDs to strings for serialization (to_dict method)
# 3. Removed string conversions in internal logic
# 4. Maintained UUID consistency throughout constraint detection
# 5. Updated all methods to work with UUID keys directly
# 6. FIXED conflict detection to allow valid room sharing
# 7. FIXED Update assignment status to CONFLICT when conflicts are detected
# 8. FIXED division by zero errors in statistics calculation
# 9. FIXED non-JSON-compliant 'Infinity' and Enum serialization

import json
import traceback
from typing import Dict, List, Optional, Any, Set, Tuple, TYPE_CHECKING
from uuid import UUID, uuid4
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from enum import Enum
import logging
from .constraint_types import ConstraintSeverity
from collections import defaultdict

# Import the new metrics class
from .metrics import SolutionMetrics, QualityScore

if TYPE_CHECKING:
    from .problem_model import ExamSchedulingProblem


logger = logging.getLogger(__name__)


class SolutionStatus(Enum):
    INCOMPLETE = "incomplete"
    FEASIBLE = "feasible"
    OPTIMAL = "optimal"
    INFEASIBLE = "infeasible"
    INVALID = "invalid"


class AssignmentStatus(Enum):
    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"
    CONFLICT = "conflict"
    INVALID = "invalid"


@dataclass
class ExamAssignment:
    exam_id: UUID
    time_slot_id: Optional[UUID] = None
    room_ids: List[UUID] = field(default_factory=list)
    assigned_date: Optional[date] = None
    status: AssignmentStatus = AssignmentStatus.UNASSIGNED
    conflicts: List[str] = field(default_factory=list)
    room_allocations: Dict[UUID, int] = field(default_factory=dict)
    invigilator_ids: List[UUID] = field(default_factory=list)

    def is_complete(self) -> bool:
        return (
            self.time_slot_id is not None
            and len(self.room_ids) > 0
            and self.assigned_date is not None
        )

    def total_capacity(self) -> int:
        return sum(self.room_allocations.values())


@dataclass
class ConflictReport:
    conflict_id: UUID
    conflict_type: str
    severity: ConstraintSeverity
    affected_exams: List[UUID]
    affected_students: List[UUID] = field(default_factory=list)
    affected_resources: List[UUID] = field(default_factory=list)
    description: str = ""
    resolution_suggestions: List[str] = field(default_factory=list)


@dataclass
class SolutionStatistics:
    total_exams: int = 0
    assigned_exams: int = 0
    unassigned_exams: int = 0
    student_conflicts: int = 0
    room_conflicts: int = 0
    time_conflicts: int = 0
    room_utilization_percentage: float = 0.0
    timeslot_utilization_percentage: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """MODIFIED: Serializes the statistics object to a dictionary."""
        return asdict(self)


class TimetableSolution:
    """FIXED - Solution class with UUID-only internal processing and proper room sharing validation"""

    def __init__(
        self, problem: "ExamSchedulingProblem", solution_id: Optional[UUID] = None
    ):
        self.id = solution_id or uuid4()
        self.problem = problem
        self.created_at = datetime.now()
        self.last_modified = datetime.now()
        self.status = SolutionStatus.INCOMPLETE
        self.objective_value = float("inf")
        self.fitness_score: float = 0.0

        self.assignments: Dict[UUID, ExamAssignment] = {
            eid: ExamAssignment(exam_id=eid) for eid in problem.exams
        }
        self.conflicts: Dict[UUID, ConflictReport] = {}
        self.statistics = SolutionStatistics()
        self.soft_constraint_penalties: Dict[str, float] = {}
        self.soft_constraint_satisfaction: Dict[str, float] = {}

    def assign(
        self,
        exam_id: UUID,
        date: date,
        slot_id: UUID,
        rooms: List[UUID],
        allocations: Dict[UUID, int],
        invigilator_ids: Optional[List[UUID]] = None,
    ) -> None:
        """Assign exam to specific date, time slot, and rooms using UUIDs"""
        asm = ExamAssignment(
            exam_id=exam_id,
            time_slot_id=slot_id,
            room_ids=rooms.copy(),
            assigned_date=date,
            status=AssignmentStatus.ASSIGNED,
            room_allocations=allocations.copy(),
            invigilator_ids=invigilator_ids.copy() if invigilator_ids else [],
        )
        self.assignments[exam_id] = asm
        self.last_modified = datetime.now()
        self.update_assignment_statuses()

    def get_completion_percentage(self) -> float:
        """Calculate percentage of exams with complete assignments"""
        if not self.assignments:
            return 0.0
        total_exams = len(self.assignments)
        if total_exams == 0:
            return 100.0
        assigned = sum(1 for a in self.assignments.values() if a.is_complete())
        return (assigned / total_exams) * 100

    def is_feasible(self) -> bool:
        """FIXED - Check if solution is feasible (complete and conflict-free)"""
        return (
            self.get_completion_percentage() >= 100
            and len(self.detect_conflicts_fixed()) == 0
        )

    def calculate_objective_value(self) -> float:
        """Calculate objective value based on conflicts and completion"""
        conflicts = self.detect_conflicts_fixed()
        completion = self.get_completion_percentage()

        conflict_penalty = len(conflicts) * 10
        completion_bonus = completion

        self.objective_value = conflict_penalty - completion_bonus
        return self.objective_value

    def get_students_for_exam_enhanced(self, exam_id: UUID) -> Set[UUID]:
        """FIXED - Enhanced student retrieval for exam using UUID keys"""
        students = set()
        exam = self.problem.exams.get(exam_id)
        if not exam:
            return students

        if hasattr(exam, "students"):
            students.update(exam.students.keys())

        students.update(self.problem.get_students_for_course(exam.course_id))

        return students

    def update_assignment_statuses(self):
        """FIXED - Update assignment statuses based on detected conflicts"""
        for assignment in self.assignments.values():
            if assignment.is_complete():
                assignment.status = AssignmentStatus.ASSIGNED
                assignment.conflicts.clear()

        conflicts = self.detect_conflicts_fixed()
        conflicted_exams = {exam_id for c in conflicts for exam_id in c.affected_exams}

        for exam_id in conflicted_exams:
            if exam_id in self.assignments:
                assignment = self.assignments[exam_id]
                if assignment.is_complete():
                    assignment.status = AssignmentStatus.CONFLICT
                    assignment.conflicts = [
                        c.description for c in conflicts if exam_id in c.affected_exams
                    ]

        logger.info(f"Updated {len(conflicted_exams)} assignments to CONFLICT status")

    def detect_conflicts_fixed(self) -> List[ConflictReport]:
        """FIXED - Enhanced conflict detection with UUID keys and proper room sharing validation"""
        conflicts: List[ConflictReport] = []
        by_slot: Dict[Tuple[date, UUID], List[ExamAssignment]] = defaultdict(list)
        for assignment in self.assignments.values():
            if assignment.is_complete():
                key = (assignment.assigned_date, assignment.time_slot_id)
                by_slot[key].append(assignment)  # type: ignore

        for (day, slot_id), slot_assignments in by_slot.items():
            if len(slot_assignments) <= 1:
                continue
            conflicts.extend(
                self._detect_student_temporal_conflicts(slot_assignments, day, slot_id)
            )
            conflicts.extend(
                self._detect_room_capacity_conflicts(slot_assignments, day, slot_id)
            )

        self.conflicts = {c.conflict_id: c for c in conflicts}
        return conflicts

    def _detect_student_temporal_conflicts(
        self, slot_assignments: List[ExamAssignment], day: date, slot_id: UUID
    ) -> List[ConflictReport]:
        """Detect students scheduled for multiple exams at the same time, differentiating by registration type."""
        conflicts = []
        student_exam_map: Dict[UUID, List[UUID]] = defaultdict(list)
        for assignment in slot_assignments:
            exam_students = self.get_students_for_exam_enhanced(assignment.exam_id)
            for student_id in exam_students:
                student_exam_map[student_id].append(assignment.exam_id)

        for student_id, exam_list in student_exam_map.items():
            if len(exam_list) <= 1:
                continue

            # --- START MODIFICATION ---
            # Check if this conflict involves only carryover registrations for this student
            is_carryover_conflict = True
            for exam_id in exam_list:
                exam = self.problem.exams.get(exam_id)
                if exam and exam.students.get(student_id) == "normal":
                    is_carryover_conflict = False
                    break

            if is_carryover_conflict:
                conflict_type = "student_carryover_conflict"
                severity = ConstraintSeverity.MEDIUM  # Less severe
                description = (
                    f"Carryover student has {len(exam_list)} exams in the same slot."
                )
            else:
                conflict_type = "student_temporal_conflict"
                severity = (
                    ConstraintSeverity.CRITICAL
                )  # This is a hard constraint violation
                description = f"Student has {len(exam_list)} exams in the same slot (involving at least one normal registration)."
            # --- END MODIFICATION ---

            conflicts.append(
                ConflictReport(
                    conflict_id=uuid4(),
                    conflict_type=conflict_type,
                    severity=severity,
                    affected_exams=exam_list,
                    affected_students=[student_id],
                    description=description,
                )
            )
        return conflicts

    def _detect_room_capacity_conflicts(
        self, slot_assignments: List[ExamAssignment], day: date, slot_id: UUID
    ) -> List[ConflictReport]:
        """FIXED - Detect room capacity violations, allowing valid room sharing"""
        conflicts = []
        room_student_count: Dict[UUID, int] = defaultdict(int)
        room_exams_map: Dict[UUID, List[UUID]] = defaultdict(list)

        for assignment in slot_assignments:
            exam = self.problem.exams.get(assignment.exam_id)
            if not exam:
                continue
            # Use room_allocations for precise student count per room if available
            if assignment.room_allocations:
                for room_id, count in assignment.room_allocations.items():
                    room_student_count[room_id] += count
                    room_exams_map[room_id].append(assignment.exam_id)
            else:  # Fallback for simpler assignments
                for room_id in assignment.room_ids:
                    room_student_count[room_id] += exam.expected_students
                    room_exams_map[room_id].append(assignment.exam_id)

        for room_id, total_students in room_student_count.items():
            room = self.problem.rooms.get(room_id)
            if room and total_students > room.exam_capacity:
                conflicts.append(
                    ConflictReport(
                        conflict_id=uuid4(),
                        conflict_type="room_capacity_conflict",
                        severity=ConstraintSeverity.HIGH,
                        affected_exams=room_exams_map[room_id],
                        affected_resources=[room_id],
                        description=f"Room {room.code} is over capacity ({total_students}/{room.exam_capacity}).",
                    )
                )
        return conflicts

    def detect_conflicts(self) -> List[ConflictReport]:
        return self.detect_conflicts_fixed()

    def update_statistics(self):
        """Update solution statistics based on current state"""
        stats = SolutionStatistics()
        stats.total_exams = len(self.assignments)
        stats.assigned_exams = sum(
            1 for a in self.assignments.values() if a.is_complete()
        )
        stats.unassigned_exams = stats.total_exams - stats.assigned_exams

        conflicts = self.detect_conflicts_fixed()
        stats.student_conflicts = sum(
            1 for c in conflicts if "student" in c.conflict_type
        )
        stats.room_conflicts = sum(1 for c in conflicts if "room" in c.conflict_type)

        used_rooms = {
            r for a in self.assignments.values() if a.is_complete() for r in a.room_ids
        }
        total_rooms = len(self.problem.rooms)
        stats.room_utilization_percentage = (
            (len(used_rooms) / total_rooms * 100) if total_rooms > 0 else 0.0
        )

        used_slots = {
            a.time_slot_id for a in self.assignments.values() if a.is_complete()
        }
        total_timeslots = len(self.problem.timeslots)
        stats.timeslot_utilization_percentage = (
            (len(used_slots) / total_timeslots * 100) if total_timeslots > 0 else 0.0
        )

        self.statistics = stats

    def to_dict(self) -> Dict[str, Any]:
        """
        MODIFIED: Creates a comprehensive dictionary representation of the solution,
        ideal for serialization to JSON for frontend display.
        Handles non-JSON-compliant float values and Enums.
        """
        self.update_statistics()
        self.update_assignment_statuses()

        metrics_calculator = SolutionMetrics()
        quality_score = metrics_calculator.evaluate_solution_quality(self.problem, self)

        objective_value = self.calculate_objective_value()
        objective_value_serializable = (
            None
            if objective_value == float("inf") or objective_value == -float("inf")
            else objective_value
        )

        # --- START OF ENUM FIX ---
        # Manually build the conflicts list to ensure Enums are converted to strings
        serializable_conflicts = []
        for c in self.conflicts.values():
            conflict_dict = asdict(c)
            conflict_dict["severity"] = (
                c.severity.value
            )  # Convert Enum member to its string value
            serializable_conflicts.append(conflict_dict)
        # --- END OF ENUM FIX ---

        return {
            "solution_id": str(self.id),
            "problem_id": str(self.problem.id),
            "created_at": self.created_at.isoformat(),
            "last_modified": self.last_modified.isoformat(),
            "status": self.status.value,
            "objective_value": objective_value_serializable,
            "statistics": self.statistics.to_dict(),
            "quality_metrics": quality_score.to_dict(),
            "assignments": {
                str(eid): {
                    "exam_id": str(a.exam_id),
                    "time_slot_id": str(a.time_slot_id) if a.time_slot_id else None,
                    "assigned_date": (
                        a.assigned_date.isoformat() if a.assigned_date else None
                    ),
                    "room_ids": [str(r) for r in a.room_ids],
                    "status": a.status.value,
                    "conflicts": a.conflicts,
                    "invigilator_ids": [str(inv_id) for inv_id in a.invigilator_ids],
                }
                for eid, a in self.assignments.items()
            },
            "conflicts": serializable_conflicts,  # Use the sanitized list
        }

    def update_soft_constraint_metrics(self, problem: "ExamSchedulingProblem"):
        """Update soft constraint metrics using SolutionMetrics"""
        metrics_calculator = SolutionMetrics()
        quality_score = metrics_calculator.evaluate_solution_quality(problem, self)
        self.soft_constraint_penalties = quality_score.soft_constraint_penalties
        self.soft_constraint_satisfaction = quality_score.soft_constraint_satisfaction
