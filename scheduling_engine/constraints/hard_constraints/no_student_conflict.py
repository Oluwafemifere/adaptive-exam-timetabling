# scheduling_engine/constraints/hard_constraints/no_student_conflict.py

"""
No Student Conflict Hard Constraint

This constraint ensures that no student has multiple exams scheduled at the same time.
This is the most critical constraint in exam scheduling as it directly affects student ability
to take their exams.
"""

from typing import Dict, List, Any, Optional, DefaultDict
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
class StudentConflictViolation:
    """Represents a student scheduling conflict"""

    student_id: UUID
    conflicting_exam_ids: List[UUID]
    time_slot_id: UUID
    course_codes: List[str]
    severity: float = 1.0


class NoStudentConflictConstraint(EnhancedBaseConstraint):
    """
    Hard constraint preventing student exam conflicts.

    This constraint ensures that no student is scheduled for multiple exams
    in the same time slot. It supports database configuration for:
    - Cross-registration conflict checking
    - Elective course inclusion/exclusion
    - Carryover exam handling
    - Conflict detection methods
    """

    # Change the __init__ method to avoid parameter conflicts
    def __init__(self, **kwargs):
        # Extract parameters with defaults
        constraint_id = kwargs.pop("constraint_id", "NO_STUDENT_CONFLICT")
        name = kwargs.pop("name", "No Student Conflicts")
        constraint_type = kwargs.pop("constraint_type", ConstraintType.HARD)
        category = kwargs.pop("category", ConstraintCategory.STUDENT_CONSTRAINTS)
        weight = kwargs.pop("weight", 1.0)

        # Handle parameters separately
        default_params = {
            "check_cross_registration": True,
            "include_electives": True,
            "include_carryover": True,
            "conflict_detection_method": "comprehensive",
            "penalty_multiplier": 100000,
        }

        # Merge with any provided parameters
        if "parameters" in kwargs:
            default_params.update(kwargs.pop("parameters"))

        # REMOVE constraint_id from kwargs to avoid duplicate passing
        if "constraint_id" in kwargs:
            kwargs.pop("constraint_id")

        # Call parent with proper parameter order - REMOVE constraint_id from kwargs
        super().__init__(
            constraint_id=constraint_id,
            name=name,
            constraint_type=constraint_type,
            category=category,
            weight=weight,
            parameters=default_params,
            **kwargs,
        )

        # mapping: student_id -> list of exam ids
        self.student_exam_mapping: DefaultDict[UUID, List[UUID]] = defaultdict(list)
        if not hasattr(self, "_is_initialized"):
            self._is_initialized = False

    def get_definition(self) -> ConstraintDefinition:
        """Get constraint definition for registration"""
        return ConstraintDefinition(
            constraint_id=self.constraint_id,
            name=self.name,
            description="Ensures no student has multiple exams scheduled at the same time",
            constraint_type=self.constraint_type,
            category=self.category,
            parameters=self.parameters,
            validation_rules=[
                "At most one exam per student per time slot",
                "All course registrations considered",
                "Cross-faculty conflicts detected",
                "Carryover exam conflicts prevented",
            ],
            constraint_class=type(self),
            is_configurable=True,
        )

    def _initialize_implementation(
        self,
        problem: "ExamSchedulingProblem",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize constraint by building student-exam mappings"""
        try:
            self.student_exam_mapping.clear()

            # Get effective parameters
            check_cross_registration = self.get_parameter(
                "check_cross_registration", True
            )
            include_electives = self.get_parameter("include_electives", True)
            include_carryover = self.get_parameter("include_carryover", True)

            if not check_cross_registration:
                logger.debug(
                    "Cross-registration checks disabled for NoStudentConflictConstraint"
                )

            # Build mapping of students to their exams
            for registration in problem.course_registrations.values():
                student_id = registration.student_id
                course_id = registration.course_id

                # Apply filtering based on parameters
                if (
                    not include_carryover
                    and getattr(registration, "registration_type", "") == "carryover"
                ):
                    continue

                if (
                    not include_electives
                    and getattr(registration, "registration_type", "") == "elective"
                ):
                    continue

                # Find exams for this course
                course_exams = [
                    exam
                    for exam in problem.exams.values()
                    if exam.course_id == course_id
                ]

                for exam in course_exams:
                    self.student_exam_mapping[student_id].append(exam.id)

            # Remove duplicates
            for student_id in list(self.student_exam_mapping.keys()):
                self.student_exam_mapping[student_id] = list(
                    set(self.student_exam_mapping[student_id])
                )

            total_students = len(self.student_exam_mapping)
            multi_exam_students = sum(
                1 for exams in self.student_exam_mapping.values() if len(exams) > 1
            )

            logger.info(
                f"Initialized student-exam mapping: {total_students} students, "
                f"{multi_exam_students} with multiple exams"
            )

            # mark initialized
            self._is_initialized = True

        except Exception as e:
            logger.error(f"Error initializing no student conflict constraint: {e}")
            raise

    def _evaluate_implementation(
        self,
        problem: "ExamSchedulingProblem",
        solution: "TimetableSolution",
    ) -> List[ConstraintViolation]:
        """Evaluate constraint against solution"""
        violations: List[ConstraintViolation] = []

        try:
            # Check each student for conflicts
            for student_id, exam_ids in self.student_exam_mapping.items():
                if len(exam_ids) <= 1:
                    continue

                # Get time slot assignments for this student's exams
                student_schedule: Dict[UUID, List[UUID]] = (
                    {}
                )  # time_slot_id -> list of exam_ids

                for exam_id in exam_ids:
                    assignment = solution.assignments.get(exam_id)
                    # explicitly narrow slot_id to exclude None
                    slot_id = getattr(assignment, "time_slot_id", None)
                    if slot_id is None:
                        continue

                    if slot_id not in student_schedule:
                        student_schedule[slot_id] = []
                    student_schedule[slot_id].append(exam_id)

                # Check for conflicts (multiple exams in same slot)
                for time_slot_id, slot_exam_ids in student_schedule.items():
                    if len(slot_exam_ids) > 1:
                        # Get course codes for reporting
                        course_codes: List[str] = []
                        for exam_id in slot_exam_ids:
                            exam = problem.exams.get(exam_id)
                            if exam:
                                course_codes.append(
                                    getattr(exam, "course_code", str(exam_id))
                                )

                        violation = ConstraintViolation(
                            constraint_id=getattr(self, "id", uuid4()),
                            violation_id=uuid4(),
                            severity=ConstraintSeverity.CRITICAL,
                            affected_exams=slot_exam_ids,
                            affected_resources=[student_id],
                            description=f"Student {student_id} has {len(slot_exam_ids)} exams "
                            f"in slot {time_slot_id}: {', '.join(course_codes)}",
                            penalty=self.get_parameter("penalty_multiplier", 100000)
                            * len(slot_exam_ids),
                        )
                        violations.append(violation)

        except Exception as e:
            logger.error(f"Error evaluating no student conflict constraint: {e}")

        return violations

    def validate_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """Validate constraint parameters"""
        errors = super().validate_parameters(parameters)

        penalty_multiplier = parameters.get("penalty_multiplier", 100000)
        if penalty_multiplier <= 0:
            errors.append("penalty_multiplier must be positive")

        detection_method = parameters.get("conflict_detection_method", "comprehensive")
        if detection_method not in ["comprehensive", "basic", "cross_faculty_only"]:
            errors.append("Invalid conflict_detection_method")

        return errors

    def get_conflict_statistics(
        self, problem: "ExamSchedulingProblem"
    ) -> Dict[str, Any]:
        """Get statistics about potential conflicts in the problem"""
        if not getattr(self, "_is_initialized", False):
            init_fn = getattr(self, "initialize", None)
            if callable(init_fn):
                init_fn(problem)
            else:
                self._initialize_implementation(problem)

        total_students = len(self.student_exam_mapping)
        multi_exam_students = 0
        max_exams_per_student = 0
        total_potential_conflicts = 0
        exam_distribution: DefaultDict[int, int] = defaultdict(int)

        for student_id, exam_ids in self.student_exam_mapping.items():
            num_exams = len(exam_ids)
            exam_distribution[num_exams] += 1

            if num_exams > 1:
                multi_exam_students += 1
                max_exams_per_student = max(max_exams_per_student, num_exams)

                # Calculate potential conflicts for this student
                potential_conflicts = (num_exams * (num_exams - 1)) // 2
                total_potential_conflicts += potential_conflicts

        return {
            "total_students": total_students,
            "students_with_multiple_exams": multi_exam_students,
            "max_exams_per_student": max_exams_per_student,
            "total_potential_conflicts": total_potential_conflicts,
            "exam_distribution": dict(exam_distribution),
            "conflict_pressure": total_potential_conflicts
            / max(len(problem.time_slots), 1),
            "constraint_parameters": self.parameters,
        }

    def clone(
        self,
        new_weight: Optional[float] = None,
        new_parameters: Optional[Dict[str, Any]] = None,
    ) -> "NoStudentConflictConstraint":
        """Create a copy of this constraint with optional modifications"""
        kwargs = {
            "parameters": self.parameters.copy(),
            "database_config": getattr(self, "database_config", {}).copy(),
        }

        if new_parameters:
            kwargs["parameters"].update(new_parameters)

        clone = NoStudentConflictConstraint(**kwargs)

        if new_weight is not None:
            clone.weight = new_weight

        return clone
