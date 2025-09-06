# scheduling_engine/constraints/soft_constraints/invigilator_balance.py

"""
Invigilator Balance Soft Constraint

This constraint optimizes the distribution of invigilation duties among staff
to ensure fair workload distribution and adequate coverage while respecting
staff preferences and availability.
"""

from typing import Dict, List, Set, Any, Optional, Tuple
from uuid import UUID
import logging
from collections import defaultdict
from dataclasses import dataclass
import math

from ..enhanced_base_constraint import EnhancedBaseConstraint
from ...core.constraint_registry import (
    ConstraintDefinition,
    ConstraintType,
    ConstraintCategory,
    ConstraintViolation,
    ConstraintSeverity,
)
from ...core.problem_model import ExamSchedulingProblem
from ...core.solution import TimetableSolution

logger = logging.getLogger(__name__)


@dataclass
class InvigilatorBalanceViolation:
    """Represents an invigilator workload imbalance"""

    violation_type: str  # 'overload', 'underutilization', 'unfair_distribution', 'preference_violation'
    staff_id: UUID
    time_slot_ids: List[UUID]
    exam_ids: List[UUID]
    current_load: int
    expected_load: int
    load_deviation: float
    department_id: Optional[UUID]
    severity: float = 1.0


class InvigilatorBalanceConstraint(EnhancedBaseConstraint):
    """
    Soft constraint optimizing invigilator workload balance.

    This constraint ensures fair distribution of invigilation duties among
    available staff while respecting individual limits and preferences.
    It promotes equitable workload sharing and staff satisfaction.

    Supports database configuration for:
    - Balance methods (variance minimization, even split, department-based)
    - Daily and weekly limit enforcement
    - Department preference weighting
    - Workload variance penalty settings
    """

    def __init__(self, **kwargs):
        super().__init__(
            constraint_id="INVIGILATOR_BALANCE",
            name="Invigilator Workload Balance",
            constraint_type=ConstraintType.SOFT,
            category=ConstraintCategory.RESOURCE_CONSTRAINTS,
            weight=0.5,
            parameters={
                "balance_method": "variance_minimization",
                "respect_daily_limits": True,
                "respect_weekly_limits": True,
                "department_preference_weight": 0.3,
                "workload_variance_penalty": 500,
                "overload_penalty_multiplier": 2.0,
                "underutilization_threshold": 0.5,
                "fair_distribution_target": 0.15,
            },
            **kwargs,
        )

        self.staff_capacities: Dict[UUID, Dict[str, int]] = {}
        self.staff_departments: Dict[UUID, UUID] = {}
        self.qualified_staff: Set[UUID] = set()
        self._is_initialized: bool = False

    def get_definition(self) -> ConstraintDefinition:
        """Get constraint definition for registration"""
        return ConstraintDefinition(
            constraint_id=self.constraint_id,
            name=self.name,
            description="Ensures fair distribution of invigilation duties among staff",
            constraint_type=self.constraint_type,
            category=self.category,
            parameters=self.parameters,
            validation_rules=[
                "Distribute invigilation duties fairly among qualified staff",
                "Respect individual staff capacity limits",
                "Minimize workload variance across staff",
                "Consider department-based preferences",
                "Avoid severe staff overload or underutilization",
            ],
            constraint_class=type(self),
            is_configurable=True,
        )

    def _initialize_implementation(
        self,
        problem: "ExamSchedulingProblem",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize constraint with staff capacity and qualification data"""
        try:
            self.staff_capacities.clear()
            self.staff_departments.clear()
            self.qualified_staff.clear()

            # Extract staff information
            staff_list = getattr(problem, "staff", {})
            for staff in staff_list.values():
                staff_id = staff.id

                # Check if staff can invigilate
                can_invigilate = getattr(staff, "can_invigilate", False)
                if can_invigilate:
                    self.qualified_staff.add(staff_id)

                    # Extract capacity limits
                    daily_limit = getattr(staff, "max_daily_sessions", 2)
                    weekly_limit = getattr(staff, "max_weekly_sessions", 10)

                    self.staff_capacities[staff_id] = {
                        "daily": max(1, daily_limit),
                        "weekly": max(1, weekly_limit),
                        "total": max(1, weekly_limit * 4),  # Approximate monthly limit
                    }

                    # Department association
                    department_id = getattr(staff, "department_id", None)
                    if department_id:
                        self.staff_departments[staff_id] = department_id

            self._is_initialized = True
            logger.info(
                f"Initialized invigilator balance constraint: "
                f"{len(self.qualified_staff)} qualified staff, "
                f"{len(self.staff_departments)} with department assignments"
            )

        except Exception as e:
            self._is_initialized = False
            logger.error(f"Error initializing invigilator balance constraint: {e}")
            raise

    def _evaluate_implementation(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> List[ConstraintViolation]:
        """Evaluate constraint against solution"""
        violations: List[ConstraintViolation] = []

        try:
            # Component 1: Workload distribution violations
            dist_violations = self._evaluate_distribution_balance(problem, solution)
            violations.extend(dist_violations)

            # Component 2: Capacity limit violations
            capacity_violations = self._evaluate_capacity_violations(problem, solution)
            violations.extend(capacity_violations)

            # Component 3: Department preference violations
            pref_violations = self._evaluate_preference_violations(problem, solution)
            violations.extend(pref_violations)

        except Exception as e:
            logger.error(f"Error evaluating invigilator balance constraint: {e}")

        return violations

    def _evaluate_distribution_balance(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> List[ConstraintViolation]:
        """Evaluate workload distribution balance"""
        violations: List[ConstraintViolation] = []

        try:
            # Count assignments per staff member
            staff_workloads: Dict[UUID, int] = defaultdict(
                int
            )  # staff_id -> number of assignments
            staff_assignments: Dict[UUID, List[Tuple[UUID, Optional[UUID]]]] = (
                defaultdict(list)
            )  # staff_id -> list of (exam_id, time_slot_id)

            # Extract invigilator assignments from solution
            # Note: This assumes invigilator assignments are available
            invigilator_assignments = getattr(solution, "invigilator_assignments", {})

            for exam_id, assignment in solution.assignments.items():
                if exam_id in invigilator_assignments:
                    exam_invigilators = invigilator_assignments[exam_id]
                    for staff_id in exam_invigilators:
                        if staff_id in self.qualified_staff:
                            staff_workloads[staff_id] += 1
                            if assignment.time_slot_id is not None:
                                staff_assignments[staff_id].append(
                                    (exam_id, assignment.time_slot_id)
                                )

            # Include staff with zero assignments
            for staff_id in self.qualified_staff:
                if staff_id not in staff_workloads:
                    staff_workloads[staff_id] = 0

            if not staff_workloads:
                return violations

            # Calculate distribution statistics
            workloads = list(staff_workloads.values())
            total_assignments = sum(workloads)
            avg_workload = total_assignments / len(workloads)

            if avg_workload == 0:
                return violations

            # Calculate variance-based penalty
            variance = sum((load - avg_workload) ** 2 for load in workloads) / len(
                workloads
            )
            variance_penalty = variance * self.get_parameter(
                "workload_variance_penalty", 500
            )

            # Identify specific violations
            for staff_id, workload in staff_workloads.items():
                deviation = abs(workload - avg_workload)

                if workload > avg_workload * 1.5:  # Significantly overloaded
                    penalty = variance_penalty * self.get_parameter(
                        "overload_penalty_multiplier", 2.0
                    )

                    violation = ConstraintViolation(
                        constraint_id=self.id,
                        violation_id=UUID(),
                        severity=ConstraintSeverity.MEDIUM,
                        affected_exams=[
                            exam_id for exam_id, _ in staff_assignments[staff_id]
                        ],
                        affected_resources=[staff_id],
                        description=f"Staff {staff_id} overloaded: {workload} assignments "
                        f"(average: {avg_workload:.1f})",
                        penalty=penalty,
                    )
                    violations.append(violation)

                elif (
                    workload < avg_workload * 0.5 and avg_workload > 1
                ):  # Significantly underutilized
                    penalty = variance_penalty * 0.5

                    violation = ConstraintViolation(
                        constraint_id=self.id,
                        violation_id=UUID(),
                        severity=ConstraintSeverity.LOW,
                        affected_exams=[],
                        affected_resources=[staff_id],
                        description=f"Staff {staff_id} underutilized: {workload} assignments "
                        f"(average: {avg_workload:.1f})",
                        penalty=penalty,
                    )
                    violations.append(violation)

        except Exception as e:
            logger.error(f"Error evaluating distribution balance: {e}")

        return violations

    def _evaluate_capacity_violations(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> List[ConstraintViolation]:
        """Evaluate capacity limit violations"""
        violations: List[ConstraintViolation] = []

        try:
            if not self.get_parameter("respect_daily_limits", True):
                return violations

            # Group assignments by staff and time period
            staff_daily_assignments: Dict[UUID, Dict[str, int]] = defaultdict(
                lambda: defaultdict(int)
            )  # staff_id -> date -> count
            staff_weekly_assignments: Dict[UUID, int] = defaultdict(
                int
            )  # staff_id -> total weekly count

            invigilator_assignments = getattr(solution, "invigilator_assignments", {})

            # Extract time slot date information
            time_slot_dates = {}
            for time_slot in problem.time_slots.values():
                slot_date = getattr(time_slot, "date", None)
                if slot_date:
                    time_slot_dates[time_slot.id] = str(slot_date)
                else:
                    time_slot_dates[time_slot.id] = "unknown"

            # Count assignments per staff per day/week
            for exam_id, assignment in solution.assignments.items():
                if exam_id in invigilator_assignments and assignment.time_slot_id:
                    exam_invigilators = invigilator_assignments[exam_id]
                    time_slot_id = assignment.time_slot_id
                    slot_date = time_slot_dates.get(time_slot_id, "unknown")

                    for staff_id in exam_invigilators:
                        if staff_id in self.qualified_staff:
                            staff_daily_assignments[staff_id][slot_date] += 1
                            staff_weekly_assignments[staff_id] += 1

            # Check capacity violations
            for staff_id in self.qualified_staff:
                capacities = self.staff_capacities.get(
                    staff_id, {"daily": 2, "weekly": 10}
                )

                # Check daily limits
                daily_assignments = staff_daily_assignments[staff_id]
                for date, count in daily_assignments.items():
                    if count > capacities["daily"]:
                        excess = count - capacities["daily"]
                        penalty = (
                            excess * 1000
                        )  # High penalty for daily limit violation

                        violation = ConstraintViolation(
                            constraint_id=self.id,
                            violation_id=UUID(),
                            severity=ConstraintSeverity.HIGH,
                            affected_exams=[],
                            affected_resources=[staff_id],
                            description=f"Staff {staff_id} exceeds daily limit on {date}: "
                            f"{count} assignments (limit: {capacities['daily']})",
                            penalty=penalty,
                        )
                        violations.append(violation)

                # Check weekly limits
                if self.get_parameter("respect_weekly_limits", True):
                    weekly_count = staff_weekly_assignments[staff_id]
                    if weekly_count > capacities["weekly"]:
                        excess = weekly_count - capacities["weekly"]
                        penalty = (
                            excess * 500
                        )  # Moderate penalty for weekly limit violation

                        violation = ConstraintViolation(
                            constraint_id=self.id,
                            violation_id=UUID(),
                            severity=ConstraintSeverity.MEDIUM,
                            affected_exams=[],
                            affected_resources=[staff_id],
                            description=f"Staff {staff_id} exceeds weekly limit: "
                            f"{weekly_count} assignments (limit: {capacities['weekly']})",
                            penalty=penalty,
                        )
                        violations.append(violation)

        except Exception as e:
            logger.error(f"Error evaluating capacity violations: {e}")

        return violations

    def _evaluate_preference_violations(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> List[ConstraintViolation]:
        """Evaluate department preference violations"""
        violations: List[ConstraintViolation] = []

        try:
            # Count cross-department assignments
            cross_dept_assignments = 0
            total_assignments = 0

            invigilator_assignments = getattr(solution, "invigilator_assignments", {})

            for exam_id, assignment in solution.assignments.items():
                if exam_id not in invigilator_assignments:
                    continue

                # Get exam's department
                exam = problem.exams.get(exam_id)
                if not exam:
                    continue

                exam_dept_id = getattr(exam, "department_id", None)
                if not exam_dept_id:
                    continue

                exam_invigilators = invigilator_assignments[exam_id]
                for staff_id in exam_invigilators:
                    total_assignments += 1
                    staff_dept_id = self.staff_departments.get(staff_id)

                    if staff_dept_id and exam_dept_id and staff_dept_id != exam_dept_id:
                        cross_dept_assignments += 1

            # Penalty for cross-department assignments (mild preference violation)
            if total_assignments > 0:
                cross_dept_ratio = cross_dept_assignments / total_assignments

                if cross_dept_ratio > 0.3:  # More than 30% cross-department
                    penalty = cross_dept_ratio * 300

                    violation = ConstraintViolation(
                        constraint_id=self.id,
                        violation_id=UUID(),
                        severity=ConstraintSeverity.LOW,
                        affected_exams=[],
                        affected_resources=[],
                        description=f"High cross-department assignment rate: {cross_dept_ratio:.1%} "
                        f"({cross_dept_assignments}/{total_assignments})",
                        penalty=penalty,
                    )
                    violations.append(violation)

        except Exception as e:
            logger.error(f"Error evaluating preference violations: {e}")

        return violations

    def validate_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """Validate constraint parameters"""
        errors = super().validate_parameters(parameters)

        balance_method = parameters.get("balance_method", "variance_minimization")
        if balance_method not in [
            "variance_minimization",
            "even_split",
            "department_based",
        ]:
            errors.append("Invalid balance_method")

        dept_weight = parameters.get("department_preference_weight", 0.3)
        if not (0 <= dept_weight <= 1):
            errors.append("department_preference_weight must be between 0 and 1")

        variance_penalty = parameters.get("workload_variance_penalty", 500)
        if variance_penalty < 0:
            errors.append("workload_variance_penalty cannot be negative")

        overload_multiplier = parameters.get("overload_penalty_multiplier", 2.0)
        if overload_multiplier < 1:
            errors.append("overload_penalty_multiplier must be at least 1")

        return errors

    def get_balance_statistics(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> Dict[str, Any]:
        """Get detailed statistics about invigilator workload balance"""
        if not self._is_initialized:
            self.initialize(problem)

        # Count assignments per staff
        staff_workloads: Dict[UUID, int] = defaultdict(int)
        invigilator_assignments = getattr(solution, "invigilator_assignments", {})

        for exam_id, assignment in solution.assignments.items():
            if exam_id in invigilator_assignments:
                exam_invigilators = invigilator_assignments[exam_id]
                for staff_id in exam_invigilators:
                    if staff_id in self.qualified_staff:
                        staff_workloads[staff_id] += 1

        # Include staff with zero assignments
        for staff_id in self.qualified_staff:
            if staff_id not in staff_workloads:
                staff_workloads[staff_id] = 0

        workloads = list(staff_workloads.values())

        if workloads:
            avg_workload = sum(workloads) / len(workloads)
            max_workload = max(workloads)
            min_workload = min(workloads)

            # Calculate fairness metrics
            variance = sum((w - avg_workload) ** 2 for w in workloads) / len(workloads)
            std_dev = math.sqrt(variance)
            coefficient_of_variation = std_dev / avg_workload if avg_workload > 0 else 0
        else:
            avg_workload = max_workload = min_workload = 0
            variance = std_dev = coefficient_of_variation = 0

        return {
            "qualified_staff_count": len(self.qualified_staff),
            "staff_with_assignments": len([w for w in workloads if w > 0]),
            "workload_distribution": {
                "average": avg_workload,
                "minimum": min_workload,
                "maximum": max_workload,
                "variance": variance,
                "standard_deviation": std_dev,
                "coefficient_of_variation": coefficient_of_variation,
            },
            "balance_quality": {
                "is_fair": coefficient_of_variation
                < self.get_parameter("fair_distribution_target", 0.15),
                "fairness_score": max(0, 1 - coefficient_of_variation),
                "overloaded_staff": len(
                    [w for w in workloads if w > avg_workload * 1.5]
                ),
                "underutilized_staff": len(
                    [w for w in workloads if w < avg_workload * 0.5]
                ),
            },
            "constraint_parameters": self.parameters,
        }

    def clone(
        self,
        new_weight: Optional[float] = None,
        new_parameters: Optional[Dict[str, Any]] = None,
    ) -> "InvigilatorBalanceConstraint":
        """Create a copy of this constraint with optional modifications"""
        kwargs = {
            "parameters": self.parameters.copy(),
            "database_config": self.database_config.copy(),
        }

        if new_parameters:
            kwargs["parameters"].update(new_parameters)

        clone = InvigilatorBalanceConstraint(**kwargs)

        if new_weight is not None:
            clone.weight = new_weight

        return clone
