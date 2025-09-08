# scheduling_engine/core/metrics.py

"""
Solution quality metrics and performance evaluation.
Implements fitness evaluation schemes from the research paper.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from uuid import UUID
import time

from ..config import get_logger
from .problem_model import ExamSchedulingProblem
from .solution import TimetableSolution

logger = get_logger("core.metrics")


@dataclass
class QualityScore:
    """Quality score breakdown for a solution"""

    total_score: float = 0.0

    # Individual components
    feasibility_score: float = 0.0
    objective_value_score: float = 0.0
    constraint_satisfaction_score: float = 0.0
    resource_utilization_score: float = 0.0
    student_satisfaction_score: float = 0.0

    # Penalty components
    hard_constraint_penalty: float = 0.0
    soft_constraint_penalty: float = 0.0
    unassigned_exam_penalty: float = 0.0

    # Weights used in calculation
    weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics for solver execution"""

    # Runtime metrics
    total_runtime_seconds: float = 0.0
    cp_sat_runtime_seconds: float = 0.0
    ga_runtime_seconds: float = 0.0
    coordination_overhead_seconds: float = 0.0

    # Iteration metrics
    total_iterations: int = 0
    cp_sat_iterations: int = 0
    ga_generations: int = 0

    # Memory metrics
    peak_memory_mb: float = 0.0
    average_memory_mb: float = 0.0

    # Convergence metrics
    generations_to_best: int = 0
    improvement_rate: float = 0.0
    convergence_stability: float = 0.0

    # Solution progression
    initial_solution_quality: float = 0.0
    final_solution_quality: float = 0.0
    quality_improvement: float = 0.0


class SolutionMetrics:
    """
    Comprehensive solution evaluation and metrics calculation.
    Implements fitness evaluation from the research paper.
    """

    def __init__(self):
        self.evaluation_history: List[Tuple[float, QualityScore]] = []
        self.performance_metrics = PerformanceMetrics()

    def evaluate_solution_quality(
        self,
        problem: ExamSchedulingProblem,
        solution: TimetableSolution,
        weights: Optional[Dict[str, float]] = None,
    ) -> QualityScore:
        """
        Evaluate comprehensive solution quality.
        Based on fitness evaluation from research paper equation (6).
        """
        if weights is None:
            weights = self._get_default_weights()

        quality = QualityScore(weights=weights)

        # 1. Feasibility score (hard constraints)
        quality.feasibility_score = self._calculate_feasibility_score(problem, solution)

        # 2. Objective value score (TWT from research paper)
        quality.objective_value_score = self._calculate_objective_score(solution)

        # 3. Constraint satisfaction score
        quality.constraint_satisfaction_score = self._calculate_constraint_satisfaction(
            problem, solution
        )

        # 4. Resource utilization score
        quality.resource_utilization_score = self._calculate_utilization_score(
            problem, solution
        )

        # 5. Student satisfaction score
        quality.student_satisfaction_score = self._calculate_student_satisfaction(
            problem, solution
        )

        # Calculate penalties
        quality.hard_constraint_penalty = self._calculate_hard_constraint_penalty(
            problem, solution
        )
        quality.soft_constraint_penalty = self._calculate_soft_constraint_penalty(
            problem, solution
        )
        quality.unassigned_exam_penalty = self._calculate_unassigned_penalty(solution)

        # Combine into total score
        quality.total_score = self._calculate_weighted_total_score(quality, weights)

        # Store in history
        self.evaluation_history.append((time.time(), quality))

        return quality

    def _get_default_weights(self) -> Dict[str, float]:
        """Get default weights for quality components"""
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

    def _calculate_feasibility_score(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> float:
        """Calculate feasibility score (0.0 to 1.0)"""
        if not solution.is_feasible():
            return 0.0

        # Check completion rate
        completion_rate = solution.get_completion_percentage() / 100.0
        return completion_rate

    def _calculate_objective_score(self, solution: TimetableSolution) -> float:
        """
        Calculate objective value score.
        Lower TWT (Total Weighted Tardiness) = higher score.
        """
        objective_value = solution.calculate_objective_value()

        if objective_value == float("inf"):
            return 0.0

        # Normalize objective value to 0-1 range
        # Using inverse relationship: lower objective = higher score
        if objective_value == 0:
            return 1.0
        else:
            # Sigmoid normalization to bound between 0 and 1
            return 1.0 / (1.0 + objective_value / 100.0)

    def _calculate_constraint_satisfaction(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> float:
        """Calculate constraint satisfaction rate"""
        # This would integrate with constraint registry
        # For now, use basic conflict detection
        conflicts = solution.detect_conflicts()

        if not conflicts:
            return 1.0

        # Weight by conflict severity
        total_penalty = 0.0
        max_penalty = len(solution.assignments) * 10  # Theoretical maximum

        for conflict in conflicts:
            if conflict.severity == "high":
                total_penalty += 10.0
            elif conflict.severity == "medium":
                total_penalty += 5.0
            else:
                total_penalty += 1.0

        # Normalize to 0-1 range
        satisfaction = max(0.0, 1.0 - (total_penalty / max_penalty))
        return satisfaction

    def _calculate_utilization_score(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> float:
        """Calculate resource utilization efficiency"""
        solution.update_statistics()

        # Combine room and time slot utilization
        room_util = solution.statistics.room_utilization_percentage / 100.0
        time_util = solution.statistics.time_slot_utilization_percentage / 100.0

        # Penalize both over and under utilization
        target_utilization = 0.8  # 80% target

        room_efficiency = 1.0 - abs(room_util - target_utilization)
        time_efficiency = 1.0 - abs(time_util - target_utilization)

        return (room_efficiency + time_efficiency) / 2.0

    def _calculate_student_satisfaction(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> float:
        """Calculate student satisfaction score"""
        satisfaction_score = 0.0
        total_students = len(problem.students)

        if total_students == 0:
            return 1.0

        for student_id, student in problem.students.items():
            student_score = self._calculate_individual_student_satisfaction(
                student_id, problem, solution
            )
            satisfaction_score += student_score

        return satisfaction_score / total_students

    def _calculate_individual_student_satisfaction(
        self,
        student_id: UUID,
        problem: ExamSchedulingProblem,
        solution: TimetableSolution,
    ) -> float:
        """Calculate satisfaction for individual student"""
        student = problem.students[student_id]
        satisfaction = 1.0

        # Check for conflicts
        # Replace get_student_conflicts with direct conflict detection
        conflicts = []
        student_courses = student.registered_courses
        student_exams = [
            exam_id
            for exam_id, exam in problem.exams.items()
            if exam.course_id in student_courses
        ]

        # Check for conflicts in the solution
        for i, exam1_id in enumerate(student_exams):
            for exam2_id in student_exams[i + 1 :]:
                assignment1 = solution.assignments.get(exam1_id)
                assignment2 = solution.assignments.get(exam2_id)

                if (
                    assignment1
                    and assignment1.is_complete()
                    and assignment2
                    and assignment2.is_complete()
                    and assignment1.time_slot_id == assignment2.time_slot_id
                ):
                    conflicts.append((exam1_id, exam2_id))

        # Apply penalty for conflicts
        satisfaction -= len(conflicts) * 0.5

        # Check for preferred times (if student has preferences)
        if student.preferred_times:
            preference_satisfaction = 0.0
            registered_exams = [
                exam
                for exam in problem.exams.values()
                if exam.course_id in student.registered_courses
            ]

            for exam in registered_exams:
                assignment = solution.assignments.get(exam.id)
                if assignment and assignment.is_complete():
                    if assignment.time_slot_id in student.preferred_times:
                        preference_satisfaction += 1.0

            if registered_exams:
                preference_satisfaction /= len(registered_exams)
                satisfaction = satisfaction * 0.8 + preference_satisfaction * 0.2

        return max(0.0, satisfaction)

    def _calculate_hard_constraint_penalty(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> float:
        """Calculate penalty for hard constraint violations"""
        # This would integrate with constraint registry
        conflicts = solution.detect_conflicts()

        penalty = 0.0
        for conflict in conflicts:
            if conflict.severity == "high":  # Treating "high" as hard constraint
                penalty += 100.0  # High penalty for hard constraint violations

        return penalty

    def _calculate_soft_constraint_penalty(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> float:
        """Calculate penalty for soft constraint violations"""
        conflicts = solution.detect_conflicts()

        penalty = 0.0
        for conflict in conflicts:
            if conflict.severity in ["medium", "low"]:
                penalty += 10.0 if conflict.severity == "medium" else 1.0

        return penalty

    def _calculate_unassigned_penalty(self, solution: TimetableSolution) -> float:
        """Calculate penalty for unassigned exams"""
        unassigned_count = len(
            [a for a in solution.assignments.values() if not a.is_complete()]
        )
        return float(unassigned_count) * 50.0  # High penalty per unassigned exam

    def _calculate_weighted_total_score(
        self, quality: QualityScore, weights: Dict[str, float]
    ) -> float:
        """Calculate weighted total score"""
        total = 0.0

        # Positive components
        total += quality.feasibility_score * weights.get("feasibility", 1.0)
        total += quality.objective_value_score * weights.get("objective_value", 0.8)
        total += quality.constraint_satisfaction_score * weights.get(
            "constraint_satisfaction", 0.7
        )
        total += quality.resource_utilization_score * weights.get(
            "resource_utilization", 0.6
        )
        total += quality.student_satisfaction_score * weights.get(
            "student_satisfaction", 0.5
        )

        # Penalty components (negative weights)
        total += quality.hard_constraint_penalty * weights.get(
            "hard_constraint_penalty", -10.0
        )
        total += quality.soft_constraint_penalty * weights.get(
            "soft_constraint_penalty", -2.0
        )
        total += quality.unassigned_exam_penalty * weights.get(
            "unassigned_penalty", -5.0
        )

        return total

    def calculate_fitness_for_ga(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> float:
        """
        Calculate fitness score for genetic algorithm.
        Based on research paper's fitness function (equation 6).
        """
        quality = self.evaluate_solution_quality(problem, solution)

        # Convert quality score to fitness (higher is better for GA)
        # Ensure fitness is always positive
        fitness = max(
            0.0, quality.total_score + 100.0
        )  # Shift to ensure positive values

        return fitness

    def calculate_diversity_metrics(
        self, solutions: List[TimetableSolution]
    ) -> Dict[str, float]:
        """Calculate diversity metrics for a population of solutions"""
        if len(solutions) < 2:
            return {"diversity": 0.0, "uniqueness": 0.0}

        # Calculate pairwise diversity
        total_diversity = 0.0
        comparisons = 0

        for i in range(len(solutions)):
            for j in range(i + 1, len(solutions)):
                diversity = self._calculate_solution_diversity(
                    solutions[i], solutions[j]
                )
                total_diversity += diversity
                comparisons += 1

        average_diversity = total_diversity / comparisons if comparisons > 0 else 0.0

        # Calculate uniqueness (number of unique solutions)
        unique_solutions_count = self._count_unique_solutions(solutions)
        uniqueness = unique_solutions_count / len(solutions)

        return {
            "diversity": average_diversity,
            "uniqueness": uniqueness,
            "population_size": len(solutions),
            "unique_solutions": unique_solutions_count,
        }

    def _calculate_solution_diversity(
        self, solution1: TimetableSolution, solution2: TimetableSolution
    ) -> float:
        """Calculate diversity between two solutions"""
        differences = 0.0
        total_assignments = len(solution1.assignments)

        for exam_id in solution1.assignments.keys():
            assignment1 = solution1.assignments[exam_id]
            assignment2 = solution2.assignments[exam_id]

            # Compare assignments
            if assignment1.time_slot_id != assignment2.time_slot_id:
                differences += 1
            elif set(assignment1.room_ids) != set(assignment2.room_ids):
                differences += 0.5  # Partial difference for room changes

        return differences / total_assignments if total_assignments > 0 else 0.0

    def _count_unique_solutions(self, solutions: List[TimetableSolution]) -> int:
        """Count unique solutions in a population"""
        unique_solutions: List[TimetableSolution] = []

        for solution in solutions:
            is_duplicate = False
            for unique_solution in unique_solutions:
                if self._calculate_solution_diversity(solution, unique_solution) < 0.01:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_solutions.append(solution)

        return len(unique_solutions)

    def update_performance_metrics(
        self,
        runtime: float,
        solver_phase: str,
        iterations: int = 0,
        memory_usage: float = 0.0,
    ) -> None:
        """Update performance metrics during solving"""
        self.performance_metrics.total_runtime_seconds += runtime

        if solver_phase == "cp_sat":
            self.performance_metrics.cp_sat_runtime_seconds += runtime
            self.performance_metrics.cp_sat_iterations += iterations
        elif solver_phase == "ga":
            self.performance_metrics.ga_runtime_seconds += runtime
            self.performance_metrics.ga_generations += iterations
        elif solver_phase == "coordination":
            self.performance_metrics.coordination_overhead_seconds += runtime

        self.performance_metrics.total_iterations += iterations

        # Ensure we're working with float values
        memory_usage_float = float(memory_usage)
        if memory_usage_float > self.performance_metrics.peak_memory_mb:
            self.performance_metrics.peak_memory_mb = memory_usage_float

    def calculate_convergence_metrics(
        self, fitness_history: List[float]
    ) -> Dict[str, float]:
        """Calculate convergence metrics from fitness history"""
        if len(fitness_history) < 2:
            return {
                "convergence_rate": 0.0,
                "stability": 0.0,
                "improvement_rate": 0.0,
                "generations_evaluated": len(fitness_history),
            }

        # Calculate improvement rate
        initial_fitness = fitness_history[0]
        final_fitness = fitness_history[-1]
        # Use actual initial value unless it's zero; avoid division by zero by using 1.0
        denom = initial_fitness if initial_fitness != 0.0 else 1.0
        improvement_rate = (final_fitness - initial_fitness) / denom

        # Calculate convergence rate (how quickly fitness improves)
        convergence_rate = 0.0
        if len(fitness_history) > 10:
            early_avg = sum(fitness_history[:5]) / 5
            late_avg = sum(fitness_history[-5:]) / 5
            convergence_rate = (late_avg - early_avg) / len(fitness_history)

        # Calculate stability (variance in recent generations)
        stability = 0.0
        if len(fitness_history) > 5:
            recent_fitness = fitness_history[-10:]
            mean_recent = sum(recent_fitness) / len(recent_fitness)
            variance = sum((f - mean_recent) ** 2 for f in recent_fitness) / len(
                recent_fitness
            )
            stability = 1.0 / (1.0 + variance)  # Higher stability = lower variance

        return {
            "convergence_rate": convergence_rate,
            "stability": stability,
            "improvement_rate": improvement_rate,
            "generations_evaluated": len(fitness_history),
        }

    def generate_quality_report(
        self, problem: ExamSchedulingProblem, solution: TimetableSolution
    ) -> Dict[str, Any]:
        """Generate comprehensive quality report"""
        quality = self.evaluate_solution_quality(problem, solution)
        solution.update_statistics()

        return {
            "solution_id": str(solution.id),
            "evaluation_timestamp": time.time(),
            # Overall scores
            "total_quality_score": quality.total_score,
            "fitness_score": solution.fitness_score,
            "objective_value": solution.objective_value,
            # Quality breakdown
            "quality_components": {
                "feasibility_score": quality.feasibility_score,
                "objective_value_score": quality.objective_value_score,
                "constraint_satisfaction_score": quality.constraint_satisfaction_score,
                "resource_utilization_score": quality.resource_utilization_score,
                "student_satisfaction_score": quality.student_satisfaction_score,
            },
            # Penalties
            "penalties": {
                "hard_constraint_penalty": quality.hard_constraint_penalty,
                "soft_constraint_penalty": quality.soft_constraint_penalty,
                "unassigned_exam_penalty": quality.unassigned_exam_penalty,
            },
            # Solution statistics
            "statistics": {
                "completion_percentage": solution.get_completion_percentage(),
                "is_feasible": solution.is_feasible(),
                "assigned_exams": solution.statistics.assigned_exams,
                "unassigned_exams": solution.statistics.unassigned_exams,
                "total_conflicts": len(solution.conflicts),
                "room_utilization_percentage": solution.statistics.room_utilization_percentage,
                "time_slot_utilization_percentage": solution.statistics.time_slot_utilization_percentage,
            },
            # Performance metrics
            "performance": {
                "total_runtime_seconds": self.performance_metrics.total_runtime_seconds,
                "total_iterations": self.performance_metrics.total_iterations,
                "peak_memory_mb": self.performance_metrics.peak_memory_mb,
            },
        }
