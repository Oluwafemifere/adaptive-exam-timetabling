# scheduling_engine/constraints/soft_constraints/exam_distribution.py

"""
Exam Distribution Soft Constraint

This constraint optimizes the temporal distribution of exams by promoting even
distribution across time periods and ensuring adequate preparation gaps between
student exams.
"""

from typing import Dict, List, Any, Optional, DefaultDict
from uuid import UUID
import logging
from collections import defaultdict
from dataclasses import dataclass
import math

from ..enhanced_base_constraint import EnhancedBaseConstraint
from ...core.constraint_types import (
    ConstraintType,
    ConstraintCategory,
    ConstraintViolation,
    ConstraintSeverity,
    ConstraintDefinition,
)
from ...core.problem_model import ExamSchedulingProblem
from ...core.solution import TimetableSolution

logger = logging.getLogger(__name__)


@dataclass
class ExamDistributionViolation:
    """Represents an exam distribution quality issue"""

    violation_type: str  # 'uneven_distribution', 'insufficient_gap', 'clustering'
    time_slot_ids: List[UUID]
    exam_ids: List[UUID]
    student_ids: List[UUID]
    gap_hours: Optional[float]
    expected_gap_hours: Optional[float]
    severity: float = 1.0


class ExamDistributionConstraint(EnhancedBaseConstraint):
    """
    Soft constraint optimizing exam temporal distribution.

    This constraint promotes better exam scheduling by encouraging even
    distribution of exams across time periods and maintaining adequate
    gaps between student exams for preparation time.

    Supports database configuration for:
    - Minimum and preferred gap hours between student exams
    - Distribution balance methods (variance minimization, even split)
    - Clustering penalty weights
    - Department-specific distribution rules
    """

    def __init__(self, **kwargs):
        super().__init__(
            constraint_id="EXAM_DISTRIBUTION",
            name="Exam Distribution",
            constraint_type=ConstraintType.SOFT,
            category=ConstraintCategory.TEMPORAL_CONSTRAINTS,
            weight=0.7,
            parameters={
                "minimum_gap_hours": 24,
                "preferred_gap_hours": 48,
                "distribution_balance_weight": 0.4,
                "consecutive_penalty_weight": 0.3,
                "clustering_penalty_weight": 0.3,
                "peak_period_penalty": True,
                "related_exam_separation": True,
                "workload_balance_method": "variance_minimization",
                "cluster_threshold": 3,
                "overload_threshold_multiplier": 1.5,
            },
            **kwargs,
        )

        self.student_exam_mapping: DefaultDict[UUID, List[UUID]] = defaultdict(list)
        self.time_slot_ordering: Dict[UUID, int] = {}
        self._is_initialized: bool = False

    def get_definition(self) -> ConstraintDefinition:
        """Get constraint definition for registration"""
        return ConstraintDefinition(
            constraint_id=self.constraint_id,
            name=self.name,
            description="Promotes even distribution of exams and adequate preparation gaps",
            constraint_type=self.constraint_type,
            category=self.category,
            parameters=self.parameters,
            validation_rules=[
                "Promote even distribution across available time slots",
                "Maintain minimum gaps between student exams",
                "Avoid clustering of related exams",
                "Balance workload across exam periods",
                "Minimize consecutive exam assignments",
            ],
            constraint_class=type(self),
            is_configurable=True,
        )

    def _initialize_implementation(
        self,
        problem: "ExamSchedulingProblem",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize constraint with exam and student data"""
        try:
            self.student_exam_mapping.clear()
            self.time_slot_ordering.clear()

            # Build student-exam mapping
            for registration in problem.course_registrations.values():
                student_id = registration.student_id
                course_id = registration.course_id

                # Find exams for this course
                course_exams = [
                    exam
                    for exam in problem.exams.values()
                    if exam.course_id == course_id
                ]

                for exam in course_exams:
                    self.student_exam_mapping[student_id].append(exam.id)

            # Create chronological ordering of time slots
            sorted_slots = sorted(
                problem.time_slots.values(),
                key=lambda s: (
                    getattr(s, "date", "9999-12-31"),
                    getattr(s, "start_time", "23:59"),
                ),
            )

            for i, slot in enumerate(sorted_slots):
                self.time_slot_ordering[slot.id] = i

            self._is_initialized = True

            logger.info(
                f"Initialized exam distribution constraint: "
                f"{len(self.student_exam_mapping)} students, "
                f"{len(self.time_slot_ordering)} time slots"
            )

        except Exception as e:
            logger.error(f"Error initializing exam distribution constraint: {e}")
            raise

    def _evaluate_implementation(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> List[ConstraintViolation]:
        """Evaluate constraint against solution"""
        violations: List[ConstraintViolation] = []

        try:
            # Get weights from parameters
            distribution_weight = self.get_parameter("distribution_balance_weight", 0.4)
            gap_weight = self.get_parameter("consecutive_penalty_weight", 0.3)
            clustering_weight = self.get_parameter("clustering_penalty_weight", 0.3)

            # Component 1: Distribution balance violations
            dist_violations = self._evaluate_distribution_balance(
                problem, solution, distribution_weight
            )
            violations.extend(dist_violations)

            # Component 2: Student exam gap violations
            gap_violations = self._evaluate_gap_violations(
                problem, solution, gap_weight
            )
            violations.extend(gap_violations)

            # Component 3: Exam clustering violations
            if self.get_parameter("related_exam_separation", True):
                cluster_violations = self._evaluate_clustering_violations(
                    problem, solution, clustering_weight
                )
                violations.extend(cluster_violations)

        except Exception as e:
            logger.error(f"Error evaluating exam distribution constraint: {e}")

        return violations

    def _evaluate_distribution_balance(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
        weight: float,
    ) -> List[ConstraintViolation]:
        """Evaluate distribution balance across time slots"""
        violations: List[ConstraintViolation] = []
        slot_exam_counts: DefaultDict[UUID, int] = defaultdict(int)
        slot_student_counts: DefaultDict[UUID, int] = defaultdict(int)

        try:
            # Count exams per time slot
            for exam_id, assignment in solution.assignments.items():
                if assignment.time_slot_id:
                    slot_exam_counts[assignment.time_slot_id] += 1

                    # Count students in this exam
                    exam_students = self._get_exam_student_count(exam_id, problem)
                    slot_student_counts[assignment.time_slot_id] += exam_students

            if not slot_exam_counts:
                return violations

            # Calculate distribution metrics
            workload_balance_method = self.get_parameter(
                "workload_balance_method", "variance_minimization"
            )

            exam_counts = list(slot_exam_counts.values())
            student_counts = list(slot_student_counts.values())

            if workload_balance_method == "variance_minimization":
                # Variance-based penalty for uneven distribution
                avg_exams = sum(exam_counts) / len(exam_counts)
                avg_students = sum(student_counts) / len(student_counts)

                exam_variance = sum(
                    (count - avg_exams) ** 2 for count in exam_counts
                ) / len(exam_counts)
                student_variance = sum(
                    (count - avg_students) ** 2 for count in student_counts
                ) / len(student_counts)

                penalty = (
                    math.sqrt(exam_variance) * 100 + math.sqrt(student_variance) * 50
                ) * weight
            else:
                # Simple even split penalty
                max_diff = max(exam_counts) - min(exam_counts)
                penalty = max_diff * 50 * weight

            # Identify problematic slots
            avg_exams = sum(exam_counts) / len(exam_counts)
            threshold_multiplier = self.get_parameter(
                "overload_threshold_multiplier", 1.5
            )
            threshold = avg_exams * threshold_multiplier

            for slot_id, count in slot_exam_counts.items():
                if count > threshold:
                    violation = ConstraintViolation(
                        constraint_id=self.id,
                        violation_id=UUID(),
                        severity=ConstraintSeverity.MEDIUM,
                        affected_exams=[],
                        affected_resources=[slot_id],
                        description=f"Time slot {slot_id} overloaded with {count} exams "
                        f"(average: {avg_exams:.1f})",
                        penalty=penalty * min(1.0, (count - threshold) / threshold),
                    )
                    violations.append(violation)

        except Exception as e:
            logger.error(f"Error evaluating distribution balance: {e}")

        return violations

    def _evaluate_gap_violations(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
        weight: float,
    ) -> List[ConstraintViolation]:
        """Evaluate gaps between student exams"""
        violations: List[ConstraintViolation] = []

        try:
            minimum_gap_hours = self.get_parameter("minimum_gap_hours", 24)
            preferred_gap_hours = self.get_parameter("preferred_gap_hours", 48)

            for student_id, exam_ids in self.student_exam_mapping.items():
                if len(exam_ids) <= 1:
                    continue

                # Get this student's exam schedule
                student_schedule = []
                for exam_id in exam_ids:
                    assignment = solution.assignments.get(exam_id)
                    if assignment and assignment.time_slot_id:
                        slot_order = self.time_slot_ordering.get(
                            assignment.time_slot_id, 0
                        )
                        student_schedule.append(
                            (exam_id, assignment.time_slot_id, slot_order)
                        )

                if len(student_schedule) <= 1:
                    continue

                # Sort by time slot order
                student_schedule.sort(key=lambda x: x[2])

                # Check gaps between consecutive exams
                for i in range(len(student_schedule) - 1):
                    exam1_id, slot1_id, order1 = student_schedule[i]
                    exam2_id, slot2_id, order2 = student_schedule[i + 1]

                    gap_slots = order2 - order1
                    gap_hours = gap_slots * 3  # Assume 3-hour average slot duration

                    if gap_hours < minimum_gap_hours:
                        # High penalty for violating minimum gap
                        penalty = (minimum_gap_hours - gap_hours) * 500 * weight

                        violation = ConstraintViolation(
                            constraint_id=self.id,
                            violation_id=UUID(),
                            severity=ConstraintSeverity.HIGH,
                            affected_exams=[exam1_id, exam2_id],
                            affected_resources=[student_id],
                            description=f"Student {student_id} has {gap_hours}h gap between exams "
                            f"(minimum: {minimum_gap_hours}h)",
                            penalty=penalty,
                        )
                        violations.append(violation)

                    elif gap_hours < preferred_gap_hours:
                        # Lower penalty for sub-optimal gaps
                        penalty = (preferred_gap_hours - gap_hours) * 50 * weight

                        violation = ConstraintViolation(
                            constraint_id=self.id,
                            violation_id=UUID(),
                            severity=ConstraintSeverity.LOW,
                            affected_exams=[exam1_id, exam2_id],
                            affected_resources=[student_id],
                            description=f"Student {student_id} has {gap_hours}h gap between exams "
                            f"(preferred: {preferred_gap_hours}h)",
                            penalty=penalty,
                        )
                        violations.append(violation)

        except Exception as e:
            logger.error(f"Error evaluating gap violations: {e}")

        return violations

    def _evaluate_clustering_violations(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
        weight: float,
    ) -> List[ConstraintViolation]:
        """Evaluate clustering of related exams"""
        violations: List[ConstraintViolation] = []

        try:
            # Group exams by department/faculty for clustering analysis
            dept_exams = defaultdict(list)
            for exam in problem.exams.values():
                dept_id = getattr(exam, "department_id", "unknown") or "unknown"
                dept_exams[dept_id].append(exam.id)

            cluster_threshold = self.get_parameter("cluster_threshold", 3)

            # Check for clustering within departments
            for dept_id, exam_ids in dept_exams.items():
                if len(exam_ids) <= 1:
                    continue

                # Get time slot assignments for department exams
                dept_schedule = []
                for exam_id in exam_ids:
                    assignment = solution.assignments.get(exam_id)
                    if assignment and assignment.time_slot_id:
                        slot_order = self.time_slot_ordering.get(
                            assignment.time_slot_id, 0
                        )
                        dept_schedule.append(
                            (exam_id, assignment.time_slot_id, slot_order)
                        )

                if len(dept_schedule) <= 1:
                    continue

                # Sort by time
                dept_schedule.sort(key=lambda x: x[2])

                # Look for consecutive clustering
                cluster_size = 1
                current_cluster_exams = [dept_schedule[0][0]]

                for i in range(1, len(dept_schedule)):
                    prev_order = dept_schedule[i - 1][2]
                    curr_order = dept_schedule[i][2]

                    if curr_order - prev_order <= 1:  # Consecutive or same slot
                        cluster_size += 1
                        current_cluster_exams.append(dept_schedule[i][0])
                    else:
                        # End of cluster - check if too large
                        if cluster_size >= cluster_threshold:
                            penalty = (
                                (cluster_size - (cluster_threshold - 1)) * 200 * weight
                            )

                            violation = ConstraintViolation(
                                constraint_id=self.id,
                                violation_id=UUID(),
                                severity=ConstraintSeverity.MEDIUM,
                                affected_exams=current_cluster_exams,
                                affected_resources=[],
                                description=f"Department {dept_id} has {cluster_size} "
                                f"consecutive exams clustered together",
                                penalty=penalty,
                            )
                            violations.append(violation)

                        # Start new cluster
                        cluster_size = 1
                        current_cluster_exams = [dept_schedule[i][0]]

                # Check final cluster
                if cluster_size >= cluster_threshold:
                    penalty = (cluster_size - (cluster_threshold - 1)) * 200 * weight

                    violation = ConstraintViolation(
                        constraint_id=self.id,
                        violation_id=UUID(),
                        severity=ConstraintSeverity.MEDIUM,
                        affected_exams=current_cluster_exams,
                        affected_resources=[],
                        description=f"Department {dept_id} has {cluster_size} "
                        f"consecutive exams clustered together",
                        penalty=penalty,
                    )
                    violations.append(violation)

        except Exception as e:
            logger.error(f"Error evaluating clustering violations: {e}")

        return violations

    def _get_exam_student_count(
        self, exam_id: UUID, problem: "ExamSchedulingProblem"
    ) -> int:
        """Get the number of students registered for an exam"""
        try:
            exam = problem.exams.get(exam_id)
            if not exam:
                return 0

            # Count registrations for this exam's course
            count = sum(
                1
                for reg in problem.course_registrations.values()
                if reg.course_id == exam.course_id
            )
            return count

        except Exception as e:
            logger.error(f"Error getting exam student count: {e}")
            return 0

    def validate_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """Validate constraint parameters"""
        errors = super().validate_parameters(parameters)

        min_gap = parameters.get("minimum_gap_hours", 24)
        pref_gap = parameters.get("preferred_gap_hours", 48)

        if min_gap < 0:
            errors.append("minimum_gap_hours cannot be negative")

        if pref_gap < min_gap:
            errors.append("preferred_gap_hours must be >= minimum_gap_hours")

        cluster_threshold = parameters.get("cluster_threshold", 3)
        if cluster_threshold < 2:
            errors.append("cluster_threshold must be at least 2")

        # Validate weight distribution
        weights = [
            parameters.get("distribution_balance_weight", 0.4),
            parameters.get("consecutive_penalty_weight", 0.3),
            parameters.get("clustering_penalty_weight", 0.3),
        ]

        if any(w < 0 for w in weights):
            errors.append("All weight parameters must be non-negative")

        if sum(weights) == 0:
            errors.append("At least one weight parameter must be positive")

        return errors

    def get_distribution_statistics(
        self, problem: "ExamSchedulingProblem", solution: "TimetableSolution"
    ) -> Dict[str, Any]:
        """Get detailed distribution statistics"""
        if not self._is_initialized:
            self.initialize(problem)

        # Slot utilization
        slot_usage: DefaultDict[UUID, int] = defaultdict(int)
        for assignment in solution.assignments.values():
            if assignment.time_slot_id:
                slot_usage[assignment.time_slot_id] += 1

        usage_values = list(slot_usage.values())
        avg_usage = sum(usage_values) / max(len(usage_values), 1)

        # Student exam distribution
        student_exam_counts = [
            len(exams) for exams in self.student_exam_mapping.values()
        ]

        return {
            "slot_utilization": {
                "total_slots": len(self.time_slot_ordering),
                "used_slots": len(slot_usage),
                "average_exams_per_slot": avg_usage,
                "max_exams_per_slot": max(usage_values) if usage_values else 0,
                "min_exams_per_slot": min(usage_values) if usage_values else 0,
            },
            "student_distribution": {
                "students_with_multiple_exams": sum(
                    1 for count in student_exam_counts if count > 1
                ),
                "average_exams_per_student": sum(student_exam_counts)
                / max(len(student_exam_counts), 1),
                "max_exams_per_student": (
                    max(student_exam_counts) if student_exam_counts else 0
                ),
            },
            "constraint_parameters": self.parameters,
        }

    def clone(
        self,
        new_weight: Optional[float] = None,
        new_parameters: Optional[Dict[str, Any]] = None,
    ) -> "ExamDistributionConstraint":
        """Create a copy of this constraint with optional modifications"""
        kwargs = {
            "parameters": self.parameters.copy(),
            "database_config": self.database_config.copy(),
        }

        if new_parameters:
            kwargs["parameters"].update(new_parameters)

        clone = ExamDistributionConstraint(**kwargs)

        if new_weight is not None:
            clone.weight = new_weight

        return clone
