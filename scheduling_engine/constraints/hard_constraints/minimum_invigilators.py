# scheduling_engine/constraints/hard_constraints/minimum_invigilators.py
"""
COMPREHENSIVE FIX - Minimum Invigilators Assignment (PARAMETERIZED)

This constraint ensures a sufficient number of invigilators are assigned to each exam,
based on the number of students in each specific room.
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging
import math

logger = logging.getLogger(__name__)


class MinimumInvigilatorsConstraint(CPSATBaseConstraint):
    """Ensure sufficient invigilators are assigned to each exam with room-based allocation."""

    dependencies = []

    def initialize_variables(self):
        """No local variables needed."""
        pass

    def add_constraints(self):
        """Add minimum invigilator assignment constraints."""
        constraints_added = 0

        if not self.problem.invigilators:
            logger.info(
                f"{self.constraint_id}: No invigilator data available, skipping."
            )
            self.constraint_count = 0
            return

        if not self.u:
            logger.warning(
                f"{self.constraint_id}: No u (invigilator assignment) variables available."
            )
            self.constraint_count = 0
            return

        # PARAMETERIZATION: Get students per invigilator from config, with a safe default.
        students_per_invigilator = self.get_parameter_value(
            "students_per_invigilator", default=50
        )
        if students_per_invigilator <= 0:
            students_per_invigilator = 50  # Fallback
        logger.info(
            f"{self.constraint_id}: Using students_per_invigilator = {students_per_invigilator}"
        )

        # Group u variables by (exam_id, room_id, slot_id) for efficiency
        assignment_vars = {}
        for (inv_id, exam_id, room_id, slot_id), uvar in self.u.items():
            assignment_vars.setdefault((exam_id, room_id, slot_id), []).append(uvar)

        for (exam_id, room_id, slot_id), invigilator_vars in assignment_vars.items():
            exam = self.problem.exams.get(exam_id)
            room = self.problem.rooms.get(room_id)
            if not exam or not room:
                continue

            # Estimate students in this specific room. For simplicity, we assume the exam fills this room up to its capacity.
            # A more complex model could create variables for student allocation.
            students_in_room = min(exam.expected_students, room.exam_capacity)

            required_invigilators = math.ceil(
                students_in_room / students_per_invigilator
            )
            # Ensure at least one invigilator if the room is used
            if students_in_room > 0:
                required_invigilators = max(1, required_invigilators)
            else:
                required_invigilators = 0

            y_var = self.y.get((exam_id, room_id, slot_id))
            if y_var is None:
                continue

            # Constraint: sum(invigilator_vars) >= required_invigilators * y_var
            # This means IF y_var is 1 (exam is in this room/slot), THEN the sum of assigned invigilators must be at least the required number.
            self.model.Add(
                sum(invigilator_vars) >= required_invigilators
            ).OnlyEnforceIf(y_var)
            constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} minimum invigilator constraints."
        )
