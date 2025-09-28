# scheduling_engine/constraints/hard_constraints/max_exams_per_student_per_day.py

"""
MaxExamsPerStudentPerDayConstraint - H6 Implementation (FIXED)

H6: Max exams per student per day - ∑ x[e,s] ≤ maxExamsPerDay ∀ student p, day d

This constraint ensures that no student has more than the maximum allowed
number of exams starting on the same day.

FIX: Added a robust data retrieval method with a fallback to prevent silent failures
when precomputed student-exam mappings are not available. This ensures the constraint
always has the data it needs and avoids creating faulty, overly-restrictive constraints.
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
    constraint_category = "STUDENT_CONSTRAINTS"
    is_critical = True
    min_expected_constraints = 0  # May be 0 if no students or single-exam students

    def _create_local_variables(self):
        """No local variables needed for this constraint"""
        pass

    def _add_constraint_implementation(self):
        """Add max exams per student per day constraints"""
        constraints_added = 0

        # CRITICAL FIX: Get student-exam mappings using a robust method with fallback
        student_exams = self._get_student_exam_mappings()
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

    def _get_student_exam_mappings(self):
        """
        CRITICAL FIX: Get student-exam mappings from multiple sources to ensure data is always found.
        This pattern prevents silent failures if precomputed data is not available from a dependency.
        """
        # First try precomputed_data
        if hasattr(self, "precomputed_data") and self.precomputed_data:
            student_exams = self.precomputed_data.get("student_exams", {})
            if student_exams:
                logger.debug(
                    f"{self.constraint_id}: Using student_exams from precomputed_data"
                )
                return student_exams

        # Fallback: build it from the problem model's internal registrations
        logger.warning(
            f"{self.constraint_id}: student_exams not in precomputed_data. Building locally."
        )
        student_exams = defaultdict(list)

        # Build course to exam mapping
        course_to_exam = {
            exam.course_id: exam.id for exam in self.problem.exams.values()
        }

        # Map students to exams through their registered courses using the correct attribute
        if hasattr(self.problem, "_student_courses"):
            for student_id, course_ids in self.problem._student_courses.items():
                for course_id in course_ids:
                    exam_id = course_to_exam.get(course_id)
                    if exam_id:
                        student_exams[student_id].append(exam_id)

        return student_exams
