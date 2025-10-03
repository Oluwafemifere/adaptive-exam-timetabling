# scheduling_engine/constraints/hard_constraints/instructor_conflict.py
"""
InstructorConflictConstraint - H13 Implementation

This constraint ensures that an instructor for a course cannot be assigned
as an invigilator for the exam of that same course.
"""
from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


class InstructorConflictConstraint(CPSATBaseConstraint):
    """H13: Instructor cannot invigilate their own exam."""

    dependencies = []

    def initialize_variables(self):
        """No local variables needed for this constraint."""
        pass

    def add_constraints(self):
        """Add constraints to prevent instructors from invigilating their own courses."""
        constraints_added = 0
        if not self.u:
            logger.info(
                f"{self.constraint_id}: No invigilator variables (u), skipping."
            )
            self.constraint_count = 0
            return

        for (invigilator_id, exam_id, room_id, slot_id), u_var in self.u.items():
            exam = self.problem.exams.get(exam_id)
            if not exam:
                continue

            # The invigilator ID corresponds to a staff/instructor ID.
            # Check if this invigilator is one of the instructors for the exam.
            if invigilator_id in exam.instructor_ids:
                # Forbid this assignment.
                self.model.Add(u_var == 0)
                constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} instructor self-invigilation constraints."
        )
