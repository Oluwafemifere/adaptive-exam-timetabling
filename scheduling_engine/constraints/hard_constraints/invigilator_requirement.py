# scheduling_engine/constraints/hard_constraints/invigilator_requirement.py
"""
REWRITTEN Foundational Constraint - InvigilatorRequirementConstraint (Simplified Model)

This critical constraint ensures that for each room in a given slot, the number
of assigned invigilators is sufficient to cover the needs of all exams placed in that room.
"""
from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging
import math

logger = logging.getLogger(__name__)


class InvigilatorRequirementConstraint(CPSATBaseConstraint):
    """
    Ensures invigilator requirements for rooms are met.

    Constraint Logic (Simplified Model):
    For each room `r` and slot `s`:
    The number of invigilators assigned to that room must be greater than or equal to
    the total number of invigilators required by all exams assigned to that room.
    Sum over `i` of w(i,r,s) >= Sum over `e` of (inv_needed(e,r) * y(e,r,s))
    """

    dependencies = ["RoomAssignmentConsistencyConstraint"]

    def initialize_variables(self):
        """No local variables needed."""
        pass

    def add_constraints(self):
        """Links room assignments (y_vars) to invigilator requirements (w_vars)."""
        constraints_added = 0
        if not self.y or not self.w:
            logger.info(
                f"{self.constraint_id}: No room (y) or invigilator (w) assignment variables, skipping."
            )
            return

        spi = getattr(self.problem, "max_students_per_invigilator", 50)
        if spi <= 0:
            spi = 50
            logger.warning(
                f"{self.constraint_id}: max_students_per_invigilator is invalid, using default of 50."
            )

        # In the full Phase 2 model, we must iterate through all relevant slots.
        # Get the set of all unique slots from the y_vars keys.
        all_slots = {key[2] for key in self.y.keys()}

        for slot_id in all_slots:
            for room_id, room in self.problem.rooms.items():
                # Left side of the inequality: Total invigilators assigned to this room in this slot.
                assigned_invigilators = []
                for inv_id in self.problem.invigilators:
                    w_var = self.w.get((inv_id, room_id, slot_id))
                    if w_var:
                        assigned_invigilators.append(w_var)

                # Right side of the inequality: Total invigilators required in this room for this slot.
                required_invigilators_terms = []
                for exam_id, exam in self.problem.exams.items():
                    y_var = self.y.get((exam_id, room_id, slot_id))
                    if y_var:
                        # The number of invigilators needed for this exam *if* it's placed in this room.
                        students_in_room = min(
                            exam.expected_students, room.exam_capacity
                        )
                        inv_needed = (
                            math.ceil(students_in_room / spi)
                            if students_in_room > 0
                            else 0
                        )
                        required_invigilators_terms.append(inv_needed * y_var)

                # If there's a possibility of assigning exams to this room, add the constraint.
                if required_invigilators_terms:
                    self.model.Add(
                        sum(assigned_invigilators) >= sum(required_invigilators_terms)
                    )
                    constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} invigilator requirement constraints."
        )
