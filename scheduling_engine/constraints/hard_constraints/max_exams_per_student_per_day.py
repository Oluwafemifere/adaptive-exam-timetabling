# scheduling_engine/constraints/hard_constraints/max_exams_per_student_per_day.py

"""
MaxExamsPerStudentPerDayConstraint - H6 Implementation

H6: Max exams per student per day - ∑ x[e,s] ≤ maxExamsPerDay ∀ student p, day d

This constraint ensures that no student has more than the maximum allowed
number of exams starting on the same day.
"""

from collections import defaultdict
from scheduling_engine.constraints.base_constraint import (
    CPSATBaseConstraint,
    get_day_for_timeslot,
)
import logging

logger = logging.getLogger(__name__)


class MaxExamsPerStudentPerDayConstraint(CPSATBaseConstraint):
    """H6: Max exams per student per day constraint"""

    dependencies = ["StartUniquenessConstraint"]
    constraint_category = "STUDENT_LIMITS"
    is_critical = True
    min_expected_constraints = 0  # May be 0 if no students or single-exam students

    def _create_local_variables(self):
        """No local variables needed for this constraint"""
        pass

    def _add_constraint_implementation(self):
        """Add max exams per student per day constraints"""
        constraints_added = 0

        # Get student-exam mappings
        student_exams = self.precomputed_data.get("student_exams", {})
        if not student_exams:
            logger.info(f"{self.constraint_id}: No student-exam mappings available")
            self.constraint_count = 0
            return

        # Get day-slot groupings
        try:
            day_slot_groupings = self.get_day_slot_groupings()
        except ValueError as e:
            logger.error(f"{self.constraint_id}: {e}")
            self.constraint_count = 0
            return

        # Get max exams per day limit from problem
        max_exams_per_day = getattr(self.problem, "max_exams_per_day", 3)

        # For each student and each day, limit exam starts
        for student_id, exam_ids in student_exams.items():
            if len(exam_ids) <= 1:
                continue  # Skip students with 0 or 1 exam

            for day_key, slot_ids in day_slot_groupings.items():
                student_exam_starts_this_day = []

                # Collect all x variables for this student's exams on this day
                for exam_id in exam_ids:
                    for slot_id in slot_ids:
                        x_key = (exam_id, slot_id)
                        if x_key in self.x:
                            student_exam_starts_this_day.append(self.x[x_key])

                # Add constraint if student has potential multiple exams this day
                if len(student_exam_starts_this_day) > max_exams_per_day:
                    self.model.Add(
                        sum(student_exam_starts_this_day) <= max_exams_per_day
                    )
                    constraints_added += 1

        self.constraint_count = constraints_added

        if constraints_added == 0:
            logger.info(
                f"{self.constraint_id}: No constraints needed - no students exceed daily exam limits"
            )
        else:
            logger.info(
                f"{self.constraint_id}: Added {constraints_added} max exams per day constraints"
            )
