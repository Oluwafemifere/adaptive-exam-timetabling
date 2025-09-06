# scheduling_engine/constraints/hard_constraints/room_capacity.py

"""
Room Capacity Hard Constraint

This constraint ensures that the number of students assigned to any exam room
does not exceed the room's capacity.
"""

from typing import (
    Dict,
    List,
    Set,
    Any,
    Optional,
    Tuple,
    DefaultDict,
    TYPE_CHECKING,
    cast,
)
from uuid import UUID, uuid4
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
from ...core import ExamSchedulingProblem, TimetableSolution

if TYPE_CHECKING:
    # Avoid runtime import cycles. Used for type checking only.
    from ...core import ExamAssignment

logger = logging.getLogger(__name__)


@dataclass
class RoomCapacityViolation:
    """Represents a room capacity violation"""

    room_id: UUID
    time_slot_id: UUID
    exam_ids: List[UUID]
    assigned_students: int
    room_capacity: int
    overflow: int
    severity: float = 1.0


class RoomCapacityConstraint(EnhancedBaseConstraint):
    """
    Hard constraint ensuring room capacity limits are respected.
    """

    def __init__(self, **kwargs):
        super().__init__(
            constraint_id="ROOM_CAPACITY",
            name="Room Capacity Limits",
            constraint_type=ConstraintType.HARD,
            category=ConstraintCategory.RESOURCE_CONSTRAINTS,
            weight=1.0,
            parameters={
                "use_exam_capacity": True,
                "capacity_buffer_percent": 0,
                "special_needs_extra_space": True,
                "multi_room_support": True,
                "room_type_matching": True,
                "overflow_penalty_multiplier": 1000,
            },
            **kwargs,
        )

        self.room_capacity_cache: Dict[UUID, int] = {}
        self.exam_capacity_cache: Dict[UUID, int] = {}

    def get_definition(self) -> ConstraintDefinition:
        """Get constraint definition for registration"""
        return ConstraintDefinition(
            constraint_id=self.constraint_id,
            name=self.name,
            description="Ensures room occupancy does not exceed capacity limits",
            constraint_type=self.constraint_type,
            category=self.category,
            parameters=self.parameters,
            validation_rules=[
                "Total students per room <= room capacity",
                "Exam-specific capacity limits respected",
                "Special accommodation space reserved",
                "Room type compatibility maintained",
            ],
            constraint_class=type(self),
            is_configurable=True,
        )

    def _initialize_implementation(
        self,
        problem: "ExamSchedulingProblem",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize constraint with room and exam capacity data"""
        try:
            self.room_capacity_cache.clear()
            self.exam_capacity_cache.clear()

            # Get parameters
            use_exam_capacity = self.get_parameter("use_exam_capacity", True)
            capacity_buffer_percent = self.get_parameter("capacity_buffer_percent", 0)

            # Cache room capacities
            for room in problem.rooms.values():
                base_capacity = getattr(room, "capacity", 0)
                exam_capacity = getattr(room, "exam_capacity", base_capacity)

                # Apply capacity buffer
                if capacity_buffer_percent > 0:
                    buffer_reduction = int(
                        base_capacity * capacity_buffer_percent / 100
                    )
                    base_capacity = max(1, base_capacity - buffer_reduction)
                    exam_capacity = max(1, exam_capacity - buffer_reduction)

                # Use exam capacity if specified and available
                effective_capacity = (
                    exam_capacity
                    if (use_exam_capacity and exam_capacity > 0)
                    else base_capacity
                )

                self.room_capacity_cache[room.id] = max(1, effective_capacity)

                logger.debug(
                    f"Room {room.id}: capacity={base_capacity}, "
                    f"exam_capacity={exam_capacity}, effective={effective_capacity}"
                )

            # Cache exam student counts
            for exam in problem.exams.values():
                expected_students = getattr(exam, "expected_students", 0)
                if expected_students <= 0:
                    # Calculate from registrations if not provided
                    student_count = sum(
                        1
                        for reg in problem.course_registrations.values()
                        if reg.course_id == exam.course_id
                    )
                    expected_students = student_count

                self.exam_capacity_cache[exam.id] = max(1, expected_students)

            logger.info(
                f"Initialized room capacity constraint: {len(self.room_capacity_cache)} rooms, "
                f"{len(self.exam_capacity_cache)} exams"
            )

        except Exception as e:
            logger.error(f"Error initializing room capacity constraint: {e}")
            raise

    def _evaluate_implementation(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> List[ConstraintViolation]:
        """Evaluate constraint against solution"""
        violations: List[ConstraintViolation] = []

        try:
            # Typed nested default dict:
            room_slot_usage: DefaultDict[UUID, DefaultDict[UUID, List[UUID]]] = (
                defaultdict(lambda: defaultdict(list))
            )  # room_id -> slot_id -> [exam_ids]

            for exam_id, outer_assignment in solution.assignments.items():
                if not outer_assignment.room_ids or not outer_assignment.time_slot_id:
                    continue

                time_slot_id = outer_assignment.time_slot_id

                # Handle multi-room assignments
                for room_id in outer_assignment.room_ids:
                    room_slot_usage[room_id][time_slot_id].append(exam_id)

            # Check capacity for each room-slot combination
            for room_id, slot_usage in room_slot_usage.items():
                room_capacity = self.room_capacity_cache.get(room_id, 0)

                for time_slot_id, exam_ids in slot_usage.items():
                    if not exam_ids:
                        continue

                    # Calculate total students in this room at this time
                    total_students = 0

                    for exam_id in exam_ids:
                        exam_assignment: Optional["ExamAssignment"] = (
                            solution.assignments.get(exam_id)
                        )
                        if (
                            exam_assignment is not None
                            and room_id in exam_assignment.room_ids
                        ):
                            # Get allocated capacity for this room
                            allocated_capacity = exam_assignment.room_allocations.get(
                                room_id, self.exam_capacity_cache.get(exam_id, 0)
                            )
                            total_students += allocated_capacity

                    # Check for capacity violation
                    if total_students > room_capacity:
                        overflow = total_students - room_capacity

                        # Calculate severity based on overflow percentage
                        overflow_percentage = overflow / max(room_capacity, 1)
                        severity = min(1.0, overflow_percentage)

                        violation = ConstraintViolation(
                            constraint_id=cast(UUID, self.constraint_id),
                            violation_id=uuid4(),
                            severity=ConstraintSeverity.CRITICAL,
                            affected_exams=exam_ids,
                            affected_resources=[room_id],
                            description=(
                                f"Room {room_id} capacity exceeded: {total_students} students "
                                f"assigned, capacity {room_capacity}"
                            ),
                            penalty=self._calculate_capacity_penalty(
                                overflow, room_capacity
                            ),
                        )
                        violations.append(violation)

        except Exception as e:
            logger.error(f"Error evaluating room capacity constraint: {e}")

        return violations

    def _calculate_capacity_penalty(self, overflow: int, room_capacity: int) -> float:
        """Calculate penalty for capacity overflow"""
        base_penalty = self.get_parameter("overflow_penalty_multiplier", 1000)

        # Linear penalty for each extra student
        overflow_penalty = overflow * base_penalty

        # Additional quadratic penalty for severe overcrowding
        overflow_ratio = overflow / max(room_capacity, 1)
        severity_penalty = (overflow_ratio**2) * base_penalty * 10

        return overflow_penalty + severity_penalty

    def validate_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """Validate constraint parameters"""
        errors = super().validate_parameters(parameters)

        buffer_percent = parameters.get("capacity_buffer_percent", 0)
        if buffer_percent < 0 or buffer_percent > 50:
            errors.append("capacity_buffer_percent must be between 0 and 50")

        penalty_multiplier = parameters.get("overflow_penalty_multiplier", 1000)
        if penalty_multiplier <= 0:
            errors.append("overflow_penalty_multiplier must be positive")

        return errors

    def get_capacity_statistics(
        self, problem: "ExamSchedulingProblem"
    ) -> Dict[str, Any]:
        """Get statistics about capacity utilization and constraints"""
        # Use safe attribute access in case base class stores a different name
        if not getattr(self, "_is_initialized", False):
            # call initialize defined in base class
            self.initialize(problem)

        total_room_capacity = sum(self.room_capacity_cache.values())
        total_exam_students = sum(self.exam_capacity_cache.values())

        # Calculate capacity pressure
        num_slots = len(problem.time_slots)
        effective_capacity = total_room_capacity * num_slots
        capacity_utilization = total_exam_students / max(effective_capacity, 1)

        # Room size distribution
        room_sizes = list(self.room_capacity_cache.values())
        avg_room_size = sum(room_sizes) / max(len(room_sizes), 1)

        # Exam size distribution
        exam_sizes = list(self.exam_capacity_cache.values())
        avg_exam_size = sum(exam_sizes) / max(len(exam_sizes), 1)

        return {
            "total_rooms": len(self.room_capacity_cache),
            "total_room_capacity": total_room_capacity,
            "total_exam_students": total_exam_students,
            "capacity_utilization": capacity_utilization,
            "effective_total_capacity": effective_capacity,
            "average_room_size": avg_room_size,
            "average_exam_size": avg_exam_size,
            "largest_room_capacity": max(room_sizes) if room_sizes else 0,
            "largest_exam_size": max(exam_sizes) if exam_sizes else 0,
            "capacity_pressure": (
                "high"
                if capacity_utilization > 0.8
                else "medium" if capacity_utilization > 0.6 else "low"
            ),
        }

    def get_room_compatibility_check(
        self, exam_id: UUID, room_id: UUID, problem: "ExamSchedulingProblem"
    ) -> Tuple[bool, List[str]]:
        """Check if a room is compatible with an exam's requirements"""
        issues: List[str] = []

        try:
            exam = problem.exams.get(exam_id)
            room = problem.rooms.get(room_id)

            if not exam or not room:
                issues.append("Exam or room not found")
                return False, issues

            # Check capacity compatibility
            exam_students = self.exam_capacity_cache.get(exam_id, 0)
            room_capacity = self.room_capacity_cache.get(room_id, 0)

            if exam_students > room_capacity:
                issues.append(
                    f"Exam requires {exam_students} students, room capacity is {room_capacity}"
                )

            # Check for practical/computer requirements
            if getattr(exam, "is_practical", False) and not getattr(
                room, "has_computers", False
            ):
                issues.append("Exam requires computers but room has none")

            # Check for special equipment requirements
            if getattr(exam, "requires_projector", False) and not getattr(
                room, "has_projector", False
            ):
                issues.append("Exam requires projector but room has none")

            # Check accessibility requirements
            exam_special_needs = getattr(exam, "requires_special_arrangements", False)
            room_accessible = getattr(room, "is_accessible", True)

            if exam_special_needs and not room_accessible:
                issues.append(
                    "Exam requires special arrangements but room is not accessible"
                )

        except Exception as e:
            logger.error(f"Error checking room compatibility: {e}")
            issues.append(f"Error checking compatibility: {e}")

        is_compatible = len(issues) == 0
        return is_compatible, issues

    def suggest_capacity_improvements(
        self, problem: "ExamSchedulingProblem"
    ) -> List[Dict[str, Any]]:
        """Suggest improvements to address capacity constraints"""
        suggestions: List[Dict[str, Any]] = []

        try:
            stats = self.get_capacity_statistics(problem)

            if stats["capacity_utilization"] > 0.9:
                suggestions.append(
                    {
                        "type": "critical",
                        "issue": "Very high capacity utilization",
                        "suggestion": "Consider adding more exam slots or larger rooms",
                        "impact": "High",
                    }
                )

            # Check for capacity bottlenecks
            large_exams = [
                {"exam_id": exam_id, "students": students}
                for exam_id, students in self.exam_capacity_cache.items()
                if students > stats["average_exam_size"] * 2
            ]

            if large_exams:
                suggestions.append(
                    {
                        "type": "optimization",
                        "issue": f"{len(large_exams)} very large exams detected",
                        "suggestion": "Consider splitting large exams across multiple rooms",
                        "impact": "Medium",
                        "details": large_exams[:5],  # first 5 as structured dicts
                    }
                )

            # Check room utilization efficiency
            small_rooms = [
                room_id
                for room_id, capacity in self.room_capacity_cache.items()
                if capacity < stats["average_room_size"] * 0.5
            ]

            if len(small_rooms) > len(self.room_capacity_cache) * 0.3:
                suggestions.append(
                    {
                        "type": "efficiency",
                        "issue": "Many small rooms may lead to inefficient allocation",
                        "suggestion": "Consider consolidating small exams or using larger rooms",
                        "impact": "Low",
                    }
                )

        except Exception as e:
            logger.error(f"Error generating capacity improvement suggestions: {e}")

        return suggestions

    def clone(
        self,
        new_weight: Optional[float] = None,
        new_parameters: Optional[Dict[str, Any]] = None,
    ) -> "RoomCapacityConstraint":
        """Create a copy of this constraint with optional modifications"""
        kwargs = {
            "parameters": self.parameters.copy(),
            "database_config": getattr(self, "database_config", {}).copy(),
        }

        if new_parameters:
            kwargs["parameters"].update(new_parameters)

        clone = RoomCapacityConstraint(**kwargs)

        if new_weight is not None:
            clone.weight = new_weight

        return clone
