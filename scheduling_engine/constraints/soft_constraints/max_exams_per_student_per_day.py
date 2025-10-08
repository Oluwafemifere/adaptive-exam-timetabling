# scheduling_engine/constraints/soft_constraints/max_exams_per_student_per_day.py
"""
MaxExamsPerStudentPerDayConstraint - S-Type Implementation (SOFT & PARAMETERIZED)

This soft constraint penalizes scheduling more than a maximum number of exams
for a single student on the same day.
"""

from collections import defaultdict
from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
from scheduling_engine.core.constraint_types import ConstraintDefinition
import logging

logger = logging.getLogger(__name__)


class MaxExamsPerStudentPerDayConstraint(CPSATBaseConstraint):
    """S-Type: Penalize scheduling more than 'max_exams_per_day' for a student on one day."""

    dependencies = ["UnifiedStudentConflictConstraint"]

    def __init__(self, definition: ConstraintDefinition, problem, shared_vars, model):
        super().__init__(definition, problem, shared_vars, model)
        self.penalty_weight = self.definition.weight
        logger.info(
            f"🟡 Initializing SOFT constraint {self.constraint_id} with weight {self.penalty_weight}"
        )

    def initialize_variables(self):
        """Create integer variables to hold the number of excess exams per student per day."""
        self.excess_exams_vars = []

    def add_constraints(self):
        """Add penalty for each exam scheduled for a student beyond the daily limit."""
        constraints_added = 0

        student_exams = self._get_student_exam_mappings()
        if not student_exams:
            logger.info(f"{self.constraint_id}: No student-exam mappings available.")
            self.constraint_count = 0
            return

        day_slot_groupings = self.precomputed_data.get("day_slot_groupings", {})
        if not day_slot_groupings:
            logger.error(f"{self.constraint_id}: Day/slot groupings not found.")
            return

        max_exams_per_day = int(
            self.get_parameter_value("max_exams_per_day", default=2)
        )
        logger.info(
            f"{self.constraint_id}: Applying penalty for more than {max_exams_per_day} exams per day."
        )

        for student_id, exam_ids in student_exams.items():
            if len(exam_ids) <= max_exams_per_day:
                continue

            for day_id, slot_ids in day_slot_groupings.items():
                # Collect all potential start variables for this student on this day
                student_exam_starts_this_day = [
                    self.x[key]
                    for exam_id in exam_ids
                    for slot_id in slot_ids
                    if (key := (exam_id, slot_id)) in self.x
                ]

                if len(student_exam_starts_this_day) > max_exams_per_day:
                    # This variable will represent the number of exams scheduled above the limit
                    excess_var = self.model.NewIntVar(
                        0, len(exam_ids), f"excess_exams_{student_id}_{day_id}"
                    )
                    self.excess_exams_vars.append(excess_var)

                    # We constrain the excess variable to be at least the number of exams over the limit.
                    # The solver, trying to minimize the objective, will push this value down to 0 if possible.
                    # excess_var >= sum(starts) - max_exams_per_day
                    self.model.Add(
                        sum(student_exam_starts_this_day) - max_exams_per_day
                        <= excess_var
                    )
                    constraints_added += 1

        # Add the penalty terms to the objective function.
        # The total penalty will be weight * (sum of all excess exams for all students on all days).
        if self.excess_exams_vars:
            self.penalty_terms.extend(
                (self.penalty_weight, var) for var in self.excess_exams_vars
            )

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} soft constraints for max exams per day."
        )

    def _get_student_exam_mappings(self):
        """
        Robustly get student-exam mappings by iterating through populated Exam objects.
        """
        student_exams = defaultdict(list)
        logger.debug(
            f"{self.constraint_id}: Building student-exam mappings from exam objects..."
        )
        for exam_id, exam in self.problem.exams.items():
            if hasattr(exam, "students") and exam.students:
                for student_id in exam.students.keys():
                    student_exams[student_id].append(exam_id)
        return student_exams
