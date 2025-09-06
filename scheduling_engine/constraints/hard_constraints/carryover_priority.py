# scheduling_engine/constraints/hard_constraints/carryover_priority.py

"""
Carryover Priority Hard Constraint

This constraint ensures that students who have failed or deferred exams from previous
sessions get priority scheduling. This is a critical academic policy constraint that
must be satisfied to maintain fairness and academic progression.
"""

from typing import Dict, List, Set, Any, Optional, DefaultDict
from uuid import UUID, uuid4
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
class CarryoverPriorityViolation:
    """Represents a carryover priority violation"""

    student_id: UUID
    exam_id: UUID
    violation_type: (
        str  # 'no_priority_slot', 'conflict_with_carryover', 'suboptimal_scheduling'
    )
    expected_priority: int  # Higher number = higher priority
    assigned_slot_priority: int
    severity: float = 1.0


class CarryoverPriorityConstraint(EnhancedBaseConstraint):
    """
    Hard constraint ensuring carryover/resit exam priority.

    This constraint manages the special scheduling requirements for students who
    are retaking exams from previous sessions. These students must be given priority
    in scheduling to ensure they can complete their academic requirements.

    Supports database configuration for:
    - Priority scheduling for carryover students
    - Conflict resolution favoring carryover students
    - Optimal time slot allocation for resit exams
    - Integration with capacity and availability constraints
    """

    def __init__(self, **kwargs):
        super().__init__(
            constraint_id="CARRYOVER_PRIORITY",
            name="Carryover Student Priority",
            constraint_type=ConstraintType.HARD,
            category=ConstraintCategory.ACADEMIC_POLICIES,
            weight=1.0,
            parameters={
                "enable_carryover_priority": True,
                "priority_levels": 3,
                "reserve_premium_slots": True,
                "carryover_conflict_resolution": "favor_carryover",
                "minimum_carryover_spacing_hours": 4,
                "preferred_carryover_times": ["morning", "early_afternoon"],
                "priority_penalty_multiplier": 50000,
            },
            **kwargs,
        )

        self.carryover_students: Set[UUID] = set()
        self.carryover_exams: Dict[UUID, int] = {}  # exam_id -> priority_level
        self.priority_time_slots: List[UUID] = []  # Ordered by preference

    def get_definition(self) -> ConstraintDefinition:
        """Get constraint definition for registration"""
        return ConstraintDefinition(
            constraint_id=self.constraint_id,
            name=self.name,
            description="Ensures priority scheduling for students retaking exams from previous sessions",
            constraint_type=self.constraint_type,
            category=self.category,
            parameters=self.parameters,
            validation_rules=[
                "Carryover students get priority in slot allocation",
                "No conflicts between carryover and regular exams",
                "Premium time slots reserved for carryover when possible",
                "Carryover exam capacity takes precedence",
            ],
            constraint_class=type(self),
            is_configurable=True,
        )

    def _initialize_implementation(
        self,
        problem: "ExamSchedulingProblem",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the constraint by identifying carryover students and exams"""
        try:
            self.carryover_students.clear()
            self.carryover_exams.clear()
            self.priority_time_slots.clear()

            # Check if carryover priority is enabled
            enable_priority = self.get_parameter("enable_carryover_priority", True)
            if not enable_priority:
                logger.info("Carryover priority disabled by parameters")
                return

            # Identify carryover students and exams
            self._identify_carryover_students(problem)
            self._identify_carryover_exams(problem)
            self._rank_priority_time_slots(problem)

            logger.info(
                f"Initialized carryover priority: {len(self.carryover_students)} students, "
                f"{len(self.carryover_exams)} priority exams"
            )

        except Exception as e:
            logger.error(f"Error initializing carryover priority constraint: {e}")
            raise

    def _evaluate_implementation(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> List[ConstraintViolation]:
        """Evaluate constraint against solution"""
        violations: List[ConstraintViolation] = []

        if not self.get_parameter("enable_carryover_priority", True):
            return violations

        try:
            # Check priority slot allocation
            violations.extend(self._check_priority_slot_allocation(problem, solution))

            # Check for carryover conflicts
            violations.extend(self._check_carryover_conflicts(problem, solution))

            # Check premium slot usage
            violations.extend(self._check_premium_slot_usage(problem, solution))

        except Exception as e:
            logger.error(f"Error evaluating carryover priority constraint: {e}")

        return violations

    def _identify_carryover_students(self, problem: "ExamSchedulingProblem") -> None:
        """Identify students who are carrying over exams from previous sessions"""
        try:
            # Check for carryover indicators in student data
            students = getattr(problem, "students", {})
            for student in students.values():
                is_carryover = (
                    getattr(student, "is_carryover", False)
                    or getattr(student, "has_failed_exams", False)
                    or getattr(student, "student_type", "") == "carryover"
                )

                if is_carryover:
                    self.carryover_students.add(student.id)

            # Alternative: Check course registrations for carryover indicators
            for registration in problem.course_registrations.values():
                registration_type = getattr(registration, "registration_type", "")
                if registration_type in ["carryover", "resit", "repeat"]:
                    self.carryover_students.add(registration.student_id)

            logger.info(f"Identified {len(self.carryover_students)} carryover students")

        except Exception as e:
            logger.error(f"Error identifying carryover students: {e}")

    def _identify_carryover_exams(self, problem: "ExamSchedulingProblem") -> None:
        """Identify exams that involve carryover students and assign priority levels"""
        try:
            for exam in problem.exams.values():
                # Count carryover students in this exam
                carryover_count = 0
                total_students = 0

                for registration in problem.course_registrations.values():
                    if registration.course_id == exam.course_id:
                        total_students += 1
                        if registration.student_id in self.carryover_students:
                            carryover_count += 1

                # Assign priority based on carryover student percentage
                if carryover_count > 0:
                    carryover_ratio = carryover_count / max(total_students, 1)

                    if carryover_ratio >= 0.5:  # Majority carryover students
                        priority_level = 1  # Highest priority
                    elif carryover_ratio >= 0.2:  # Significant carryover presence
                        priority_level = 2  # High priority
                    else:  # Some carryover students
                        priority_level = 3  # Medium priority

                    self.carryover_exams[exam.id] = priority_level

                    logger.debug(
                        f"Exam {exam.id} assigned priority {priority_level} "
                        f"({carryover_count}/{total_students} carryover students)"
                    )

        except Exception as e:
            logger.error(f"Error identifying carryover exams: {e}")

    def _rank_priority_time_slots(self, problem: "ExamSchedulingProblem") -> None:
        """Rank time slots by preference for carryover exam scheduling"""
        try:
            preferred_times = self.get_parameter(
                "preferred_carryover_times", ["morning", "early_afternoon"]
            )

            # Score and rank time slots
            slot_scores: List[tuple[UUID, int]] = []
            for time_slot in problem.time_slots.values():
                score = 0

                # Morning preference
                if "morning" in preferred_times and self._is_morning_slot(time_slot):
                    score += 10

                # Early afternoon preference
                if (
                    "early_afternoon" in preferred_times
                    and self._is_early_afternoon_slot(time_slot)
                ):
                    score += 8

                # Avoid late slots
                if self._is_late_slot(time_slot):
                    score -= 5

                # Prefer weekdays over weekends
                if not self._is_weekend_slot(time_slot):
                    score += 3

                slot_scores.append((time_slot.id, score))

            # Sort by score (descending) and store ordered list
            slot_scores.sort(key=lambda x: x[1], reverse=True)
            self.priority_time_slots = [slot_id for slot_id, _ in slot_scores]

            logger.info(
                f"Ranked {len(self.priority_time_slots)} time slots for carryover priority"
            )

        except Exception as e:
            logger.error(f"Error ranking priority time slots: {e}")

    def _check_priority_slot_allocation(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> List[ConstraintViolation]:
        """Check that carryover exams get priority slots"""
        violations: List[ConstraintViolation] = []

        try:
            if not self.priority_time_slots:
                return violations

            # Get top 30% of priority slots
            num_premium_slots = max(1, len(self.priority_time_slots) // 3)
            premium_slots = set(self.priority_time_slots[:num_premium_slots])

            # Check if carryover exams are getting good slots
            for exam_id, priority_level in self.carryover_exams.items():
                assignment = solution.assignments.get(exam_id)

                if not assignment or not assignment.time_slot_id:
                    continue

                time_slot_id = assignment.time_slot_id

                # High priority exams should get premium slots
                if priority_level <= 2 and time_slot_id not in premium_slots:
                    violation = ConstraintViolation(
                        constraint_id=getattr(self, "id", uuid4()),
                        violation_id=uuid4(),
                        severity=ConstraintSeverity.HIGH,
                        affected_exams=[exam_id],
                        affected_resources=[time_slot_id],
                        description=f"High priority carryover exam {exam_id} not in premium slot",
                        penalty=self.get_parameter("priority_penalty_multiplier", 50000)
                        * (3 - priority_level),  # Higher penalty for higher priority
                    )
                    violations.append(violation)

        except Exception as e:
            logger.error(f"Error checking priority slot allocation: {e}")

        return violations

    def _check_carryover_conflicts(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> List[ConstraintViolation]:
        """Check for conflicts involving carryover students"""
        violations: List[ConstraintViolation] = []

        try:
            # Ensure carryover students don't have conflicts
            for student_id in self.carryover_students:
                student_exams: List[UUID] = []

                # Find all exams for this carryover student
                for registration in problem.course_registrations.values():
                    if registration.student_id == student_id:
                        for exam in problem.exams.values():
                            if exam.course_id == registration.course_id:
                                student_exams.append(exam.id)

                if len(student_exams) <= 1:
                    continue

                # Check for time conflicts
                time_slot_assignments: Dict[UUID, List[UUID]] = {}
                for exam_id in student_exams:
                    assignment = solution.assignments.get(exam_id)
                    if assignment and assignment.time_slot_id:
                        slot_id = assignment.time_slot_id
                        if slot_id not in time_slot_assignments:
                            time_slot_assignments[slot_id] = []
                        time_slot_assignments[slot_id].append(exam_id)

                # Check for conflicts
                for slot_id, exam_ids in time_slot_assignments.items():
                    if len(exam_ids) > 1:
                        violation = ConstraintViolation(
                            constraint_id=getattr(self, "id", uuid4()),
                            violation_id=uuid4(),
                            severity=ConstraintSeverity.CRITICAL,
                            affected_exams=exam_ids,
                            affected_resources=[student_id],
                            description=f"Carryover student {student_id} has conflicting exams "
                            f"in slot {slot_id}",
                            penalty=self.get_parameter(
                                "priority_penalty_multiplier", 50000
                            )
                            * 2,
                        )
                        violations.append(violation)

        except Exception as e:
            logger.error(f"Error checking carryover conflicts: {e}")

        return violations

    def _check_premium_slot_usage(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> List[ConstraintViolation]:
        """Check that premium slots are being used appropriately"""
        violations: List[ConstraintViolation] = []

        try:
            if not self.get_parameter("reserve_premium_slots", True):
                return violations

            # Get top 20% of slots as premium
            num_premium_slots = max(1, len(self.priority_time_slots) // 5)
            premium_slots = set(self.priority_time_slots[:num_premium_slots])

            # Check usage of premium slots
            for slot_id in premium_slots:
                regular_exams_in_slot: List[UUID] = []
                carryover_exams_in_slot: List[UUID] = []

                # Categorize exams in this slot
                for exam_id, assignment in solution.assignments.items():
                    if assignment.time_slot_id == slot_id:
                        if exam_id in self.carryover_exams:
                            carryover_exams_in_slot.append(exam_id)
                        else:
                            regular_exams_in_slot.append(exam_id)

                # If regular exams are using premium slot while carryover exams exist
                if regular_exams_in_slot and self.carryover_exams:
                    # Check if there are unscheduled carryover exams
                    unscheduled_carryover = [
                        exam_id
                        for exam_id in self.carryover_exams.keys()
                        if not solution.assignments.get(exam_id)
                        or not solution.assignments[exam_id].time_slot_id
                    ]

                    if unscheduled_carryover:
                        violation = ConstraintViolation(
                            constraint_id=getattr(self, "id", uuid4()),
                            violation_id=uuid4(),
                            severity=ConstraintSeverity.MEDIUM,
                            affected_exams=regular_exams_in_slot,
                            affected_resources=[slot_id],
                            description=f"Premium slot {slot_id} used by regular exams "
                            f"while carryover exams remain unscheduled",
                            penalty=self.get_parameter(
                                "priority_penalty_multiplier", 50000
                            )
                            * 0.5,
                        )
                        violations.append(violation)

        except Exception as e:
            logger.error(f"Error checking premium slot usage: {e}")

        return violations

    def _is_morning_slot(self, time_slot) -> bool:
        """Check if time slot is in the morning"""
        try:
            if hasattr(time_slot, "start_time"):
                start_time = str(time_slot.start_time)
                return start_time.split(":")[0] in ["08", "09", "10", "11"]
            return False
        except Exception:
            return False

    def _is_early_afternoon_slot(self, time_slot) -> bool:
        """Check if time slot is in early afternoon"""
        try:
            if hasattr(time_slot, "start_time"):
                start_time = str(time_slot.start_time)
                return start_time.split(":")[0] in ["12", "13", "14"]
            return False
        except Exception:
            return False

    def _is_late_slot(self, time_slot) -> bool:
        """Check if time slot is late in the day"""
        try:
            if hasattr(time_slot, "start_time"):
                start_time = str(time_slot.start_time)
                return start_time.split(":")[0] in ["16", "17", "18", "19", "20"]
            return False
        except Exception:
            return False

    def _is_weekend_slot(self, time_slot) -> bool:
        """Check if time slot is on weekend"""
        try:
            if hasattr(time_slot, "day_of_week"):
                return time_slot.day_of_week in ["Saturday", "Sunday"]
            return False
        except Exception:
            return False

    def validate_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """Validate constraint parameters"""
        errors = super().validate_parameters(parameters)

        priority_levels = parameters.get("priority_levels", 3)
        if priority_levels < 1 or priority_levels > 10:
            errors.append("priority_levels must be between 1 and 10")

        spacing_hours = parameters.get("minimum_carryover_spacing_hours", 4)
        if spacing_hours < 0:
            errors.append("minimum_carryover_spacing_hours cannot be negative")

        penalty_multiplier = parameters.get("priority_penalty_multiplier", 50000)
        if penalty_multiplier <= 0:
            errors.append("priority_penalty_multiplier must be positive")

        return errors

    def get_carryover_statistics(
        self, problem: "ExamSchedulingProblem"
    ) -> Dict[str, Any]:
        """Get statistics about carryover students and exams"""
        if not getattr(self, "_is_initialized", False):
            self.initialize(problem)

        priority_distribution: DefaultDict[int, int] = defaultdict(int)
        for priority_level in self.carryover_exams.values():
            priority_distribution[priority_level] += 1

        return {
            "carryover_students": len(self.carryover_students),
            "carryover_exams": len(self.carryover_exams),
            "priority_distribution": dict(priority_distribution),
            "premium_slots_available": len(self.priority_time_slots) // 5,
            "high_priority_slots_available": len(self.priority_time_slots) // 3,
            "carryover_enabled": self.get_parameter("enable_carryover_priority", True),
        }

    def clone(
        self,
        new_weight: Optional[float] = None,
        new_parameters: Optional[Dict[str, Any]] = None,
    ) -> "CarryoverPriorityConstraint":
        """Create a copy of this constraint with optional modifications"""
        kwargs = {
            "parameters": self.parameters.copy(),
            "database_config": (
                self.database_config.copy()
                if getattr(self, "database_config", None)
                else {}
            ),
        }

        if new_parameters:
            kwargs["parameters"].update(new_parameters)

        clone = CarryoverPriorityConstraint(**kwargs)

        if new_weight is not None:
            clone.weight = new_weight

        return clone
