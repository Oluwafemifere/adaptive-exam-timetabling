# scheduling_engine/constraints/soft_constraints/room_utilization.py

"""
Room Utilization Soft Constraint

This constraint optimizes room usage efficiency by promoting high utilization
rates while avoiding overcrowding. It balances room capacity usage and
minimizes the number of rooms needed.
"""

from typing import Dict, List, Any, Optional
from uuid import UUID
import logging
from collections import defaultdict
from dataclasses import dataclass

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
class RoomUtilizationViolation:
    """Represents a room utilization inefficiency"""

    violation_type: (
        str  # 'underutilization', 'overutilization', 'fragmentation', 'waste'
    )
    room_id: UUID
    time_slot_id: UUID
    exam_ids: List[UUID]
    capacity_used: int
    room_capacity: int
    utilization_rate: float
    efficiency_loss: float
    severity: float = 1.0


class RoomUtilizationConstraint(EnhancedBaseConstraint):
    """
    Soft constraint optimizing room utilization efficiency.

    This constraint promotes efficient use of room resources by encouraging
    high utilization rates while maintaining student comfort and avoiding
    overcrowding.

    Supports database configuration for:
    - Target utilization rates and acceptable ranges
    - Underutilization and overutilization penalty weights
    - Fragmentation penalty settings
    - Room type efficiency preferences
    """

    def __init__(self, **kwargs):
        super().__init__(
            constraint_id="ROOM_UTILIZATION",
            name="Room Utilization Optimization",
            constraint_type=ConstraintType.SOFT,
            category=ConstraintCategory.RESOURCE_CONSTRAINTS,
            weight=0.6,
            parameters={
                "target_utilization_rate": 0.85,
                "min_acceptable_utilization": 0.60,
                "max_acceptable_utilization": 0.95,
                "underutilization_penalty_weight": 0.4,
                "overutilization_penalty_weight": 0.3,
                "fragmentation_penalty_weight": 0.3,
                "prefer_larger_rooms": True,
                "room_type_efficiency": True,
                "utilization_calculation_method": "capacity_based",
            },
            **kwargs,
        )

        self.room_capacities: Dict[UUID, int] = {}
        self._is_initialized = False

    def get_definition(self) -> ConstraintDefinition:
        """Get constraint definition for registration"""
        return ConstraintDefinition(
            constraint_id=self.constraint_id,
            name=self.name,
            description="Optimizes room usage efficiency and capacity utilization",
            constraint_type=self.constraint_type,
            category=self.category,
            parameters=self.parameters,
            validation_rules=[
                "Promote high room capacity utilization",
                "Avoid severe underutilization of rooms",
                "Prevent overcrowding beyond safe limits",
                "Minimize room fragmentation",
                "Balance utilization across available rooms",
            ],
            constraint_class=type(self),
            is_configurable=True,
        )

    def _initialize_implementation(
        self,
        problem: "ExamSchedulingProblem",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize constraint with room capacity data"""
        try:
            self.room_capacities.clear()

            # Cache room capacities
            for room in problem.rooms.values():
                # Use exam capacity if available, otherwise use general capacity
                capacity = getattr(room, "exam_capacity", None) or getattr(
                    room, "capacity", 0
                )
                self.room_capacities[room.id] = max(1, int(capacity or 0))

            self._is_initialized = True
            logger.info(
                f"Initialized room utilization constraint: {len(self.room_capacities)} rooms, "
                f"target utilization: {self.get_parameter('target_utilization_rate', 0.85):.1%}"
            )

        except Exception as e:
            logger.error(f"Error initializing room utilization constraint: {e}")
            raise

    def _evaluate_implementation(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> List[ConstraintViolation]:
        """Evaluate constraint against solution"""
        violations = []

        try:
            # Component 1: Room utilization efficiency violations
            util_violations = self._evaluate_utilization_efficiency(problem, solution)
            violations.extend(util_violations)

            # Component 2: Room fragmentation violations
            frag_violations = self._evaluate_fragmentation(problem, solution)
            violations.extend(frag_violations)

        except Exception as e:
            logger.error(f"Error evaluating room utilization constraint: {e}")

        return violations

    def _evaluate_utilization_efficiency(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> List[ConstraintViolation]:
        """Evaluate room utilization efficiency"""
        violations = []

        try:
            # Analyze utilization for each room-time slot combination
            room_slot_usage: Dict[UUID, Dict[UUID, int]] = defaultdict(
                lambda: defaultdict(int)
            )  # room_id -> slot_id -> students
            room_slot_exams: Dict[UUID, Dict[UUID, List[UUID]]] = defaultdict(
                lambda: defaultdict(list)
            )  # room_id -> slot_id -> exam_ids

            # Collect room usage data
            for exam_id, assignment in solution.assignments.items():
                if not assignment.room_ids or not assignment.time_slot_id:
                    continue

                time_slot_id = assignment.time_slot_id

                for room_id in assignment.room_ids:
                    allocated_capacity = assignment.room_allocations.get(
                        room_id,
                        getattr(problem.exams.get(exam_id), "expected_students", 0),
                    )

                    room_slot_usage[room_id][time_slot_id] += allocated_capacity
                    room_slot_exams[room_id][time_slot_id].append(exam_id)

            # Calculate penalties for each used room-slot combination
            min_util = self.get_parameter("min_acceptable_utilization", 0.60)
            max_util = self.get_parameter("max_acceptable_utilization", 0.95)
            target_util = self.get_parameter("target_utilization_rate", 0.85)

            for room_id, slot_usage in room_slot_usage.items():
                room_capacity = self.room_capacities.get(room_id, 1)

                for time_slot_id, students_used in slot_usage.items():
                    utilization_rate = students_used / room_capacity
                    exam_ids = room_slot_exams[room_id][time_slot_id]

                    # Penalty for underutilization
                    if utilization_rate < min_util:
                        penalty = (min_util - utilization_rate) * 1000

                        violation = ConstraintViolation(
                            constraint_id=self.id,
                            violation_id=UUID(),
                            severity=ConstraintSeverity.MEDIUM,
                            affected_exams=exam_ids,
                            affected_resources=[room_id],
                            description=f"Room {room_id} underutilized: {utilization_rate:.1%} "
                            f"({students_used}/{room_capacity} students)",
                            penalty=penalty,
                        )
                        violations.append(violation)

                    # Penalty for overutilization (safety concern)
                    elif utilization_rate > max_util:
                        penalty = (utilization_rate - max_util) * 5000

                        violation = ConstraintViolation(
                            constraint_id=self.id,
                            violation_id=UUID(),
                            severity=ConstraintSeverity.HIGH,
                            affected_exams=exam_ids,
                            affected_resources=[room_id],
                            description=f"Room {room_id} overcrowded: {utilization_rate:.1%} "
                            f"({students_used}/{room_capacity} students)",
                            penalty=penalty,
                        )
                        violations.append(violation)

                    # Penalty for deviation from target utilization
                    elif abs(utilization_rate - target_util) > 0.10:
                        deviation = abs(utilization_rate - target_util)
                        penalty = deviation * 200

                        violation = ConstraintViolation(
                            constraint_id=self.id,
                            violation_id=UUID(),
                            severity=ConstraintSeverity.LOW,
                            affected_exams=exam_ids,
                            affected_resources=[room_id],
                            description=f"Room {room_id} utilization suboptimal: {utilization_rate:.1%} "
                            f"(target: {target_util:.1%})",
                            penalty=penalty,
                        )
                        violations.append(violation)

        except Exception as e:
            logger.error(f"Error evaluating utilization efficiency: {e}")

        return violations

    def _evaluate_fragmentation(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> List[ConstraintViolation]:
        """Evaluate room fragmentation (many small allocations)"""
        violations = []

        try:
            # Count room usage patterns
            room_usage_frequency: Dict[UUID, int] = defaultdict(
                int
            )  # room_id -> number of time slots used

            for assignment in solution.assignments.values():
                if assignment.room_ids and assignment.time_slot_id:
                    for room_id in assignment.room_ids:
                        room_usage_frequency[room_id] += 1

            # Analyze fragmentation
            capacities = list(self.room_capacities.values())
            avg_capacity = sum(capacities) / max(len(capacities), 1)

            large_rooms = [
                room_id
                for room_id, capacity in self.room_capacities.items()
                if capacity > avg_capacity * 1.5
            ]

            small_rooms = [
                room_id
                for room_id, capacity in self.room_capacities.items()
                if capacity < avg_capacity * 0.5
            ]

            # Penalty for underutilizing large rooms
            for room_id in large_rooms:
                usage_count = room_usage_frequency.get(room_id, 0)

                if usage_count == 0:
                    continue

                # Large rooms should be used more efficiently
                expected_usage = max(
                    2, len(problem.time_slots) * 0.3
                )  # Expect 30% usage

                if usage_count < expected_usage * 0.5:
                    penalty = (expected_usage - usage_count) * 100

                    violation = ConstraintViolation(
                        constraint_id=self.id,
                        violation_id=UUID(),
                        severity=ConstraintSeverity.LOW,
                        affected_exams=[],
                        affected_resources=[room_id],
                        description=f"Large room {room_id} underutilized: "
                        f"used {usage_count} times (expected {expected_usage:.0f})",
                        penalty=penalty,
                    )
                    violations.append(violation)

            # Penalty for overusing small rooms when large rooms available
            total_large_room_usage = sum(
                room_usage_frequency.get(room_id, 0) for room_id in large_rooms
            )
            total_small_room_usage = sum(
                room_usage_frequency.get(room_id, 0) for room_id in small_rooms
            )

            if (
                total_small_room_usage > 0
                and total_large_room_usage < total_small_room_usage
                and len(large_rooms) > 0
            ):

                fragmentation_ratio = total_small_room_usage / max(
                    total_large_room_usage, 1
                )
                penalty = fragmentation_ratio * 300

                violation = ConstraintViolation(
                    constraint_id=self.id,
                    violation_id=UUID(),
                    severity=ConstraintSeverity.MEDIUM,
                    affected_exams=[],
                    affected_resources=small_rooms[:5],  # Show first 5
                    description="Room fragmentation detected: small rooms overused "
                    "while large rooms available",
                    penalty=penalty,
                )
                violations.append(violation)

        except Exception as e:
            logger.error(f"Error evaluating fragmentation: {e}")

        return violations

    def validate_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """Validate constraint parameters"""
        errors = super().validate_parameters(parameters)

        target_util = parameters.get("target_utilization_rate", 0.85)
        min_util = parameters.get("min_acceptable_utilization", 0.60)
        max_util = parameters.get("max_acceptable_utilization", 0.95)

        if not (0 < target_util < 1):
            errors.append("target_utilization_rate must be between 0 and 1")

        if not (0 <= min_util <= 1):
            errors.append("min_acceptable_utilization must be between 0 and 1")

        if not (0 <= max_util <= 1):
            errors.append("max_acceptable_utilization must be between 0 and 1")

        if min_util >= max_util:
            errors.append(
                "min_acceptable_utilization must be less than max_acceptable_utilization"
            )

        if not (min_util <= target_util <= max_util):
            errors.append(
                "target_utilization_rate must be between min and max acceptable values"
            )

        # Validate penalty weights
        penalty_weights = [
            parameters.get("underutilization_penalty_weight", 0.4),
            parameters.get("overutilization_penalty_weight", 0.3),
            parameters.get("fragmentation_penalty_weight", 0.3),
        ]

        if any(w < 0 for w in penalty_weights):
            errors.append("All penalty weights must be non-negative")

        return errors

    def get_utilization_statistics(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> Dict[str, Any]:
        """Get detailed utilization statistics"""
        if not self._is_initialized:
            self.initialize(problem)

        # Calculate overall utilization
        total_capacity = sum(self.room_capacities.values())
        used_capacity = 0
        room_usage_count = 0

        room_utilizations = []

        for room_id, capacity in self.room_capacities.items():
            room_used = 0
            room_sessions = 0

            for assignment in solution.assignments.values():
                if room_id in assignment.room_ids and assignment.time_slot_id:
                    allocated = assignment.room_allocations.get(room_id, 0)
                    room_used += allocated
                    room_sessions += 1

            if room_sessions > 0:
                avg_utilization = room_used / (capacity * room_sessions)
                room_utilizations.append(avg_utilization)
                used_capacity += room_used
                room_usage_count += 1

        overall_utilization = (
            used_capacity / max(total_capacity, 1) if total_capacity > 0 else 0
        )
        avg_room_utilization = sum(room_utilizations) / max(len(room_utilizations), 1)

        return {
            "overall_utilization": overall_utilization,
            "average_room_utilization": avg_room_utilization,
            "rooms_used": room_usage_count,
            "total_rooms": len(self.room_capacities),
            "room_usage_rate": room_usage_count / max(len(self.room_capacities), 1),
            "utilization_distribution": {
                "min": min(room_utilizations) if room_utilizations else 0,
                "max": max(room_utilizations) if room_utilizations else 0,
                "std_dev": (
                    (
                        sum((u - avg_room_utilization) ** 2 for u in room_utilizations)
                        / max(len(room_utilizations), 1)
                    )
                    ** 0.5
                    if room_utilizations
                    else 0
                ),
            },
            "target_utilization": self.get_parameter("target_utilization_rate", 0.85),
            "constraint_parameters": self.parameters,
        }

    def get_room_efficiency_recommendations(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> List[Dict[str, Any]]:
        """Get recommendations for improving room efficiency"""
        recommendations = []

        try:
            stats = self.get_utilization_statistics(problem, solution)

            if stats["overall_utilization"] < 0.6:
                recommendations.append(
                    {
                        "type": "efficiency_improvement",
                        "priority": "high",
                        "issue": f"Low overall room utilization ({stats['overall_utilization']:.1%})",
                        "suggestion": "Consider consolidating exams into fewer, larger rooms",
                    }
                )

            if stats["room_usage_rate"] < 0.5:
                recommendations.append(
                    {
                        "type": "resource_optimization",
                        "priority": "medium",
                        "issue": f"Many rooms unused ({stats['room_usage_rate']:.1%} usage rate)",
                        "suggestion": "Review room allocation strategy or reduce available room set",
                    }
                )

            if stats["utilization_distribution"]["std_dev"] > 0.3:
                recommendations.append(
                    {
                        "type": "balance_improvement",
                        "priority": "medium",
                        "issue": "High variation in room utilization rates",
                        "suggestion": "Balance load more evenly across rooms",
                    }
                )

        except Exception as e:
            logger.error(f"Error generating room efficiency recommendations: {e}")

        return recommendations

    def clone(
        self,
        new_weight: Optional[float] = None,
        new_parameters: Optional[Dict[str, Any]] = None,
    ) -> "RoomUtilizationConstraint":
        """Create a copy of this constraint with optional modifications"""
        kwargs = {
            "parameters": self.parameters.copy(),
            "database_config": self.database_config.copy(),
        }

        if new_parameters:
            kwargs["parameters"].update(new_parameters)

        clone = RoomUtilizationConstraint(**kwargs)

        if new_weight is not None:
            clone.weight = new_weight

        return clone
