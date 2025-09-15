# scheduling_engine/constraints/hard_constraints/max_exams_per_day_per_student.py

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


# ===============================================================================
# C9: Maximum Exams Per Day Per Student
# ===============================================================================


class MaxExamsPerDayPerStudentConstraint(CPSATBaseConstraint):
    """
    STUDENT_CONFLICT_MODULE - C9: Maximum Exams Per Day Per Student

    Mathematical formulation: ∀s ∈ S, d ∈ D: ∑{x[e,d,t] : e ∈ studentExams_s, t ∈ T} ≤ maxExamsPerDay
    """

    dependencies = ["StartUniquenessConstraint"]
    constraint_category = "STUDENT_CONFLICT"

    def _create_local_variables(self):
        """Use shared student-exam mapping and filter constrained students."""
        self._max_exams_per_day = getattr(self.problem, "max_exams_per_day_student", 2)

        # Only process students who have more exams than the limit
        self._constrained_students = {
            student_id: exam_ids
            for student_id, exam_ids in self.student_exams.items()
            if len(exam_ids) > self._max_exams_per_day
        }

        logger.info(
            f"{self.constraint_id}: Max per day: {self._max_exams_per_day}, "
            f"{len(self._constrained_students)} students need constraints"
        )

    def _add_constraint_implementation(self):
        """Add maximum exams per day constraints."""
        if not self.x:
            raise RuntimeError(f"{self.constraint_id}: No x variables available")

        for student_id, exam_ids in self._constrained_students.items():
            for day in self.problem.days:
                # Collect start variables for this student's exams on this day
                student_x_vars = []

                for exam_str in exam_ids:
                    # Convert to original exam ID
                    exam_id = next(
                        (
                            e.id
                            for e in self.problem.exams.values()
                            if str(e.id) == exam_str
                        ),
                        None,
                    )
                    if exam_id:
                        for slot_id in self.problem.time_slots:
                            x_key = (exam_id, day, slot_id)
                            if x_key in self.x:
                                student_x_vars.append(self.x[x_key])

                # Add constraint if student has exams
                if student_x_vars:
                    self.model.Add(sum(student_x_vars) <= self._max_exams_per_day)
                    self._increment_constraint_count()

                    logger.debug(
                        f"{self.constraint_id}: Added max constraint for "
                        f"student {student_id} on day {day}"
                    )
