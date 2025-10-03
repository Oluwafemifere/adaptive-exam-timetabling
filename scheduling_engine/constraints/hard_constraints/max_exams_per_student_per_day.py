# scheduling_engine/constraints/hard_constraints/max_exams_per_student_per_day.py
"""
MaxExamsPerStudentPerDayConstraint - H6 Implementation (FIXED & PARAMETERIZED)

This constraint ensures that no student has more than the maximum allowed
number of exams starting on the same day. It is now parameterized.
"""

from collections import defaultdict
from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


class MaxExamsPerStudentPerDayConstraint(CPSATBaseConstraint):
    """H6: Max exams per student per day constraint."""

    dependencies = ["UnifiedStudentConflictConstraint"]

    def initialize_variables(self):
        """No local variables needed for this constraint."""
        pass

    def add_constraints(self):
        """Add max exams per student per day constraints."""
        constraints_added = 0

        student_exams = self._get_student_exam_mappings()
        if not student_exams:
            logger.info(f"{self.constraint_id}: No student-exam mappings available.")
            self.constraint_count = 0
            return

        day_slot_groupings = self.precomputed_data.get("day_slot_groupings", {})
        if not day_slot_groupings:
            logger.error(
                f"{self.constraint_id}: Day/slot groupings not found in precomputed data."
            )
            self.constraint_count = 0
            return

        # PARAMETERIZATION: Get max exams per day from config, with a safe default.
        max_exams_per_day = self.get_parameter_value("max_exams_per_day", default=2)
        logger.info(
            f"{self.constraint_id}: Using max_exams_per_day = {max_exams_per_day}"
        )

        for student_id, exam_ids in student_exams.items():
            if len(exam_ids) <= max_exams_per_day:
                continue

            for day_id, slot_ids in day_slot_groupings.items():
                student_exam_starts_this_day = []
                for exam_id in exam_ids:
                    for slot_id in slot_ids:
                        x_key = (exam_id, slot_id)
                        if x_key in self.x:
                            student_exam_starts_this_day.append(self.x[x_key])

                if len(student_exam_starts_this_day) > max_exams_per_day:
                    self.model.Add(
                        sum(student_exam_starts_this_day) <= max_exams_per_day
                    )
                    constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} max exams per day constraints."
        )

    def _get_student_exam_mappings(self):
        """
        FIXED: Robustly get student-exam mappings by iterating through populated Exam objects.
        This makes the constraint self-sufficient and independent of faulty caching.
        """
        student_exams = defaultdict(list)
        logger.info(
            f"{self.constraint_id}: Building student-exam mappings from exam objects..."
        )

        for exam_id, exam in self.problem.exams.items():
            if hasattr(exam, "students") and exam.students:
                for student_id in exam.students.keys():
                    student_exams[student_id].append(exam_id)

        if not student_exams:
            logger.warning(
                f"{self.constraint_id}: No student-exam mappings could be built."
            )
        else:
            logger.info(
                f"{self.constraint_id}: Built mappings for {len(student_exams)} students."
            )

        return student_exams
