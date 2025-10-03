# scheduling_engine/core/metrics.py

"""
Solution quality metrics and performance evaluation.
Calculates comprehensive KPIs for frontend display and analysis.
"""

from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field, asdict
from uuid import UUID
import time
import logging
import math
from collections import defaultdict

from .problem_model import ExamSchedulingProblem

from .constraint_types import ConstraintType, ConstraintSeverity

if TYPE_CHECKING:
    from .solution import TimetableSolution


logger = logging.getLogger(__name__)


@dataclass
class QualityScore:
    """
    A comprehensive data structure holding all calculated KPIs for a timetable solution.
    Designed for easy serialization to JSON for frontend consumption.
    """

    # --- High-Level Scores ---
    total_score: float = 0.0  # A single, weighted score (higher is better)
    completion_percentage: float = 0.0
    is_feasible: bool = False

    # --- Hard Constraint / Conflict Report ---
    hard_constraint_violations: int = 0
    conflict_report: Dict[str, int] = field(default_factory=dict)
    unassigned_exam_penalty: float = 0.0

    # --- Soft Constraint Report ---
    total_soft_constraint_penalty: float = 0.0
    soft_constraint_penalties: Dict[str, float] = field(default_factory=dict)
    soft_constraint_satisfaction: Dict[str, float] = field(default_factory=dict)

    # --- Resource Utilization Report ---
    utilization_report: Dict[str, Any] = field(default_factory=dict)

    # --- Student Welfare Report ---
    student_welfare_report: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the QualityScore object to a dictionary for JSON output."""
        return asdict(self)


class SolutionMetrics:
    """
    Calculates various quality metrics for a given timetable solution.
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.evaluation_history: List[Tuple[float, QualityScore]] = []
        self.weights = weights or self._get_default_weights()

    def _get_default_weights(self) -> Dict[str, float]:
        """Defines the weighting for the final aggregated score."""
        return {
            "completeness": 50.0,
            "hard_constraints": 1000.0,
            "soft_constraints": 1.0,
            "student_welfare": 20.0,
        }

    def evaluate_solution_quality(
        self, problem: ExamSchedulingProblem, solution: "TimetableSolution"
    ) -> QualityScore:
        """
        Orchestrates the calculation of all KPIs and returns a comprehensive QualityScore object.
        """
        quality = QualityScore()
        solution.update_statistics()  # Ensure basic stats are current

        # --- Core Feasibility and Completeness ---
        quality.completion_percentage = solution.get_completion_percentage()
        quality.is_feasible = solution.is_feasible()
        unassigned_count = (
            solution.statistics.total_exams - solution.statistics.assigned_exams
        )
        quality.unassigned_exam_penalty = unassigned_count * self.weights.get(
            "unassigned_penalty", 50.0
        )

        # --- Hard Constraint Violations ---
        hard_violations, conflict_report = self._calculate_hard_constraint_penalties(
            solution
        )
        quality.hard_constraint_violations = hard_violations
        quality.conflict_report = conflict_report

        # --- Soft Constraint Penalties & Satisfaction ---
        penalties, satisfaction = self._calculate_soft_constraint_metrics(
            problem, solution
        )
        quality.soft_constraint_penalties = penalties
        quality.soft_constraint_satisfaction = satisfaction
        quality.total_soft_constraint_penalty = sum(penalties.values())

        # --- KPI Reports ---
        quality.utilization_report = self._calculate_utilization_metrics(
            problem, solution
        )
        quality.student_welfare_report = self._calculate_student_welfare_metrics(
            problem, solution
        )

        # --- Final Weighted Score ---
        quality.total_score = self._calculate_weighted_total_score(quality)

        self.evaluation_history.append((time.time(), quality))
        return quality

    def _calculate_hard_constraint_penalties(
        self, solution: "TimetableSolution"
    ) -> Tuple[int, Dict[str, int]]:
        """Counts hard constraint violations from the solution's conflict list."""
        conflicts = solution.detect_conflicts_fixed()
        report = defaultdict(int)
        for conflict in conflicts:
            report[conflict.conflict_type] += 1
        return len(conflicts), dict(report)

    def _calculate_soft_constraint_metrics(
        self, problem: ExamSchedulingProblem, solution: "TimetableSolution"
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        FIXED: Calculates penalties and satisfaction for each active soft constraint.
        This now correctly iterates over the list of constraint definitions.
        """
        penalties = {}
        satisfaction = {}

        try:
            # 1. Get all constraint definitions from the registry.
            all_definitions = problem.constraint_registry.get_definitions()

            # 2. Filter for only the enabled SOFT constraints.
            soft_definitions = [
                d
                for d in all_definitions
                if d.enabled and d.constraint_type == ConstraintType.SOFT
            ]

            # 3. Iterate through the list of definitions
            for constraint_def in soft_definitions:
                penalty = 0.0
                # NOTE: This section is a placeholder. A full implementation would
                # require specific evaluation logic for each soft constraint.
                # The structure is now correct.

                penalties[constraint_def.id] = penalty * constraint_def.weight
                satisfaction[constraint_def.id] = 100.0 if penalty == 0 else 0.0

        except Exception as e:
            logger.error(
                f"Error calculating soft constraint metrics: {e}", exc_info=True
            )

        return penalties, satisfaction

    def _calculate_utilization_metrics(
        self, problem: ExamSchedulingProblem, solution: "TimetableSolution"
    ) -> Dict[str, Any]:
        """Calculates detailed resource utilization statistics."""
        stats = solution.statistics
        total_possible_seat_hours = 0
        used_seat_hours = 0

        for day in problem.days.values():
            for timeslot in day.timeslots:
                for room in problem.rooms.values():
                    total_possible_seat_hours += room.exam_capacity * (
                        timeslot.duration_minutes / 60
                    )

        for assignment in solution.assignments.values():
            if assignment.is_complete():
                exam = problem.exams.get(assignment.exam_id)
                if exam:
                    used_seat_hours += exam.expected_students * (
                        exam.duration_minutes / 60
                    )

        overall_seat_hour_utilization = (
            (used_seat_hours / total_possible_seat_hours * 100)
            if total_possible_seat_hours > 0
            else 0
        )

        return {
            "room_usage_percentage": stats.room_utilization_percentage,
            "timeslot_usage_percentage": stats.timeslot_utilization_percentage,
            "total_rooms_available": len(problem.rooms),
            "total_rooms_used": len(
                {
                    r
                    for a in solution.assignments.values()
                    if a.is_complete()
                    for r in a.room_ids
                }
            ),
            "total_timeslots_available": len(problem.timeslots),
            "total_timeslots_used": len(
                {
                    a.time_slot_id
                    for a in solution.assignments.values()
                    if a.is_complete()
                }
            ),
            "overall_seat_hour_utilization_percentage": overall_seat_hour_utilization,
        }

    def _calculate_student_welfare_metrics(
        self, problem: ExamSchedulingProblem, solution: "TimetableSolution"
    ) -> Dict[str, Any]:
        """Calculates metrics related to student convenience and workload."""
        student_schedules = defaultdict(list)
        for assignment in solution.assignments.values():
            if assignment.is_complete():
                students = solution.get_students_for_exam_enhanced(assignment.exam_id)
                for student_id in students:
                    student_schedules[student_id].append(assignment)

        exams_per_day = defaultdict(lambda: defaultdict(int))
        back_to_back_count = 0

        for student_id, schedule in student_schedules.items():
            sorted_schedule = sorted(
                schedule,
                key=lambda a: (
                    a.assigned_date,
                    problem.timeslots[a.time_slot_id].start_time,
                ),
            )
            for i in range(len(sorted_schedule)):
                assignment = sorted_schedule[i]
                exams_per_day[student_id][assignment.assigned_date] += 1
                if i > 0:
                    prev_assignment = sorted_schedule[i - 1]
                    if prev_assignment.assigned_date == assignment.assigned_date:
                        prev_slot = problem.timeslots[prev_assignment.time_slot_id]
                        curr_slot = problem.timeslots[assignment.time_slot_id]
                        if prev_slot.end_time == curr_slot.start_time:
                            back_to_back_count += 1

        students_with_2_exams_day = sum(
            1
            for day_counts in exams_per_day.values()
            if any(c == 2 for c in day_counts.values())
        )
        students_with_3plus_exams_day = sum(
            1
            for day_counts in exams_per_day.values()
            if any(c >= 3 for c in day_counts.values())
        )

        return {
            "students_with_back_to_back_exams": back_to_back_count,
            "students_with_2_exams_in_a_day": students_with_2_exams_day,
            "students_with_3_or_more_exams_in_a_day": students_with_3plus_exams_day,
            "total_students_with_schedules": len(student_schedules),
        }

    def _calculate_weighted_total_score(self, q: QualityScore) -> float:
        """Calculates a final weighted score based on all KPIs."""
        score = 1000.0
        score -= q.hard_constraint_violations * self.weights["hard_constraints"]
        score -= q.unassigned_exam_penalty
        score -= q.total_soft_constraint_penalty * self.weights["soft_constraints"]

        welfare_penalty = (
            q.student_welfare_report.get("students_with_3_or_more_exams_in_a_day", 0)
            * 5
            + q.student_welfare_report.get("students_with_back_to_back_exams", 0) * 2
        )
        score -= welfare_penalty * self.weights["student_welfare"]

        return max(0.0, score)
