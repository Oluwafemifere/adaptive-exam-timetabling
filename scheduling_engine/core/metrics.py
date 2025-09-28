# scheduling_engine/core/metrics.py

"""
Solution quality metrics and performance evaluation.
Implements fitness evaluation schemes from the research paper.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from uuid import UUID
import time
import logging
import math

from .problem_model import ExamSchedulingProblem
from .solution import TimetableSolution
from .constraint_types import ConstraintSeverity

logger = logging.getLogger(__name__)


@dataclass
class QualityScore:
    total_score: float = 0.0
    feasibility_score: float = 0.0
    objective_value_score: float = 0.0
    constraint_satisfaction_score: float = 0.0
    resource_utilization_score: float = 0.0
    student_satisfaction_score: float = 0.0
    hard_constraint_penalty: float = 0.0
    soft_constraint_penalty: float = 0.0
    unassigned_exam_penalty: float = 0.0
    completion_percentage: float = 0.0
    conflict_count: int = 0
    weights: Dict[str, float] = field(default_factory=dict)
    soft_constraint_penalties: Dict[str, float] = field(default_factory=dict)
    total_soft_constraint_penalty: float = 0.0
    soft_constraint_satisfaction: Dict[str, float] = field(default_factory=dict)

    def calculate_from_solution(self, solution, problem):
        """Calculate metrics from solution and problem."""
        self.completion_percentage = solution.get_completion_percentage()
        conflicts = solution.detect_conflicts_fixed()
        self.conflict_count = len(conflicts)

        # Calculate scores
        self.feasibility_score = (
            100.0 if len(conflicts) == 0 else max(0, 100 - len(conflicts) * 10)
        )
        self.total_score = (self.completion_percentage * 0.7) + (
            self.feasibility_score * 0.3
        )

        return self


@dataclass
class PerformanceMetrics:
    total_runtime_seconds: float = 0.0
    cp_sat_runtime_seconds: float = 0.0
    ga_runtime_seconds: float = 0.0
    coordination_overhead_seconds: float = 0.0
    total_iterations: int = 0
    cp_sat_iterations: int = 0
    ga_generations: int = 0
    peak_memory_mb: float = 0.0
    average_memory_mb: float = 0.0
    generations_to_best: int = 0
    improvement_rate: float = 0.0
    convergence_stability: float = 0.0
    initial_solution_quality: float = 0.0
    final_solution_quality: float = 0.0
    quality_improvement: float = 0.0


class SolutionMetrics:
    def __init__(self):
        self.evaluation_history: List[Tuple[float, QualityScore]] = []
        self.performance_metrics = PerformanceMetrics()
        self.soft_constraint_weights = self._get_soft_constraint_weights()

    def _get_default_weights(self) -> Dict[str, float]:
        return {
            "feasibility": 1.0,
            "objective_value": 0.8,
            "constraint_satisfaction": 0.7,
            "resource_utilization": 0.6,
            "student_satisfaction": 0.5,
            "hard_constraint_penalty": -10.0,
            "soft_constraint_penalty": -2.0,
            "unassigned_penalty": -5.0,
        }

    def _get_soft_constraint_weights(self) -> Dict[str, float]:
        """Get weights for soft constraints"""
        return {
            "OverbookingPenaltyConstraint": 1000,
            "PreferenceSlotsConstraint": 500,
            "StudentGapPenaltyConstraint": 2000,
            "InvigilatorLoadBalanceConstraint": 300,
            "RoomContinuityConstraint": 800,
            "InvigilatorAvailabilityConstraint": 1500,
            "DailyWorkloadBalanceConstraint": 200,
            "UnusedSeatsConstraint": 50,
        }

    def evaluate_solution_quality(
        self,
        problem: ExamSchedulingProblem,
        solution: TimetableSolution,
        weights: Optional[Dict[str, float]] = None,
    ) -> QualityScore:
        if weights is None:
            weights = self._get_default_weights()
        quality = QualityScore(weights=weights)
        quality.feasibility_score = self._calculate_feasibility_score(problem, solution)
        quality.objective_value_score = self._calculate_objective_score(solution)
        quality.constraint_satisfaction_score = self._calculate_constraint_satisfaction(
            problem, solution
        )
        quality.resource_utilization_score = self._calculate_utilization_score(
            problem, solution
        )
        quality.student_satisfaction_score = self._calculate_student_satisfaction(
            problem, solution
        )
        quality.hard_constraint_penalty = self._calculate_hard_constraint_penalty(
            problem, solution
        )
        quality.soft_constraint_penalties = self._calculate_soft_constraint_penalties(
            problem, solution
        )
        quality.total_soft_constraint_penalty = sum(
            quality.soft_constraint_penalties.values()
        )
        quality.soft_constraint_satisfaction = (
            self._calculate_soft_constraint_satisfaction(
                quality.soft_constraint_penalties
            )
        )

        quality.total_score = self._calculate_weighted_total_score(quality, weights)
        self.evaluation_history.append((time.time(), quality))
        return quality

    def _calculate_soft_constraint_penalties(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> Dict[str, float]:
        """Calculate penalties for each soft constraint"""
        penalties = {}

        # Get all active soft constraints
        active_constraints = problem.constraint_registry.get_active_constraint_classes()
        soft_constraints = {
            k: v
            for k, v in active_constraints.items()
            if v.get("category") == "SOFT_CONSTRAINTS"
        }

        # Calculate penalty for each soft constraint
        for constraint_id, constraint_info in soft_constraints.items():
            try:
                constraint_class = constraint_info["class"]
                constraint_instance = constraint_class(problem)
                penalty = constraint_instance.evaluate_penalty(solution)
                penalties[constraint_id] = penalty
            except Exception as e:
                logger.error(f"Error evaluating soft constraint {constraint_id}: {e}")
                penalties[constraint_id] = 0

        return penalties

    def _calculate_soft_constraint_satisfaction(
        self, penalties: Dict[str, float]
    ) -> Dict[str, float]:
        """Calculate satisfaction percentage for each soft constraint"""
        satisfaction = {}
        max_penalties = self._estimate_max_penalties()

        for constraint_id, penalty in penalties.items():
            max_penalty = max_penalties.get(constraint_id, 1000)
            # Convert penalty to satisfaction percentage (0-100)
            # Lower penalty = higher satisfaction
            if max_penalty == 0:
                satisfaction_pct = 100.0
            else:
                satisfaction_pct = max(0.0, 100.0 - (penalty / max_penalty * 100.0))
            satisfaction[constraint_id] = satisfaction_pct

        return satisfaction

    def _estimate_max_penalties(self) -> Dict[str, float]:
        """Estimate maximum possible penalties for normalization"""
        # These are rough estimates - you might want to refine them
        return {
            "OverbookingPenaltyConstraint": 5000,
            "PreferenceSlotsConstraint": 2000,
            "StudentGapPenaltyConstraint": 10000,
            "InvigilatorLoadBalanceConstraint": 1500,
            "RoomContinuityConstraint": 4000,
            "InvigilatorAvailabilityConstraint": 7500,
            "DailyWorkloadBalanceConstraint": 1000,
            "UnusedSeatsConstraint": 2500,
        }

    def _calculate_feasibility_score(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> float:
        completion = solution.get_completion_percentage()
        return (completion / 100.0) if solution.is_feasible() else 0.0

    def _calculate_objective_score(self, solution: TimetableSolution) -> float:
        ov = solution.calculate_objective_value()
        if ov == float("inf") or ov < 0:
            return 0.0
        if ov == 0:
            return 1.0
        # Safely calculate score with division protection
        denominator = 1.0 + ov / 100.0
        if abs(denominator) < 1e-10:
            return 0.0
        return 1.0 / denominator

    def _calculate_student_satisfaction(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> float:
        total = len(problem.students)
        if total == 0:
            return 1.0

        score = 0.0
        for sid, student in problem.students.items():
            sat = 1.0
            exams = [
                eid
                for eid, ex in problem.exams.items()
                if ex.course_id in student.registered_courses
            ]
            prefs = getattr(student, "preferred_times", [])
            conflicts = []
            for i in range(len(exams)):
                for j in range(i + 1, len(exams)):
                    a1 = solution.assignments.get(exams[i])
                    a2 = solution.assignments.get(exams[j])
                    if (
                        a1
                        and a2
                        and a1.is_complete()
                        and a2.is_complete()
                        and a1.time_slot_id == a2.time_slot_id
                    ):
                        conflicts.append((exams[i], exams[j]))
            sat -= 0.5 * len(conflicts)
            if prefs and exams:
                pref_count = sum(
                    1
                    for eid in exams
                    if solution.assignments[eid].time_slot_id in prefs
                )
                sat = sat * 0.8 + (pref_count / len(exams)) * 0.2
            score += max(0.0, sat)
        return score / total

    def _calculate_constraint_satisfaction(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> float:
        conflicts = solution.detect_conflicts()
        if not conflicts:
            return 1.0
        total_penalty = sum(
            (
                10.0
                if c.severity == ConstraintSeverity.HIGH
                else 5.0 if c.severity == ConstraintSeverity.MEDIUM else 1.0
            )
            for c in conflicts
        )
        max_penalty = len(solution.assignments) * 10
        if max_penalty == 0:
            return 1.0
        return max(0.0, 1.0 - total_penalty / max_penalty)

    def _calculate_utilization_score(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> float:
        solution.update_statistics()
        room_util = solution.statistics.room_utilization_percentage / 100.0
        time_util = solution.statistics.timeslot_utilization_percentage / 100.0
        target = 0.8
        return (1.0 - abs(room_util - target) + 1.0 - abs(time_util - target)) / 2.0

    def _calculate_hard_constraint_penalty(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> float:
        return sum(
            100.0
            for c in solution.detect_conflicts()
            if c.severity == ConstraintSeverity.HIGH
        )

    def _calculate_soft_constraint_penalty(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> float:
        return sum(
            10.0 if c.severity == ConstraintSeverity.MEDIUM else 1.0
            for c in solution.detect_conflicts()
            if c.severity in (ConstraintSeverity.MEDIUM, ConstraintSeverity.LOW)
        )

    def _calculate_unassigned_penalty(self, solution: TimetableSolution) -> float:
        return 50.0 * len(
            [a for a in solution.assignments.values() if not a.is_complete()]
        )

    def _calculate_weighted_total_score(
        self, q: QualityScore, w: Dict[str, float]
    ) -> float:
        total = (
            q.feasibility_score * w["feasibility"]
            + q.objective_value_score * w["objective_value"]
            + q.constraint_satisfaction_score * w["constraint_satisfaction"]
            + q.resource_utilization_score * w["resource_utilization"]
            + q.student_satisfaction_score * w["student_satisfaction"]
            + q.hard_constraint_penalty * w["hard_constraint_penalty"]
            + q.soft_constraint_penalty * w["soft_constraint_penalty"]
            + q.unassigned_exam_penalty * w["unassigned_penalty"]
        )
        return total

    def calculate_fitness_for_ga(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> float:
        quality = self.evaluate_solution_quality(problem, solution)
        return max(0.0, quality.total_score + 100.0)

    def calculate_diversity_metrics(
        self, solutions: List[TimetableSolution]
    ) -> Dict[str, float]:
        n = len(solutions)
        if n < 2:
            return {"diversity": 0.0, "uniqueness": 0.0}
        total_div, count = 0.0, 0
        for i in range(n):
            for j in range(i + 1, n):
                diff = 0
                num_assignments = len(solutions[i].assignments)
                if num_assignments == 0:
                    continue
                for eid in solutions[i].assignments:
                    a1, a2 = (
                        solutions[i].assignments[eid],
                        solutions[j].assignments[eid],
                    )
                    if a1.time_slot_id != a2.time_slot_id:
                        diff += 1
                    elif set(a1.room_ids) != set(a2.room_ids):
                        diff += 0.5
                total_div += diff / num_assignments
                count += 1
        avg_div = total_div / count if count > 0 else 0.0
        unique = len(
            {
                tuple(
                    (
                        sol.assignments[e].time_slot_id,
                        tuple(sol.assignments[e].room_ids),
                    )
                    for e in sol.assignments
                )
                for sol in solutions
            }
        )
        return {"diversity": avg_div, "uniqueness": unique / n if n > 0 else 0.0}
