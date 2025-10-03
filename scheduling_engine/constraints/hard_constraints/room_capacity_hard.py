# scheduling_engine/constraints/hard_constraints/room_capacity_hard.py
"""
FIXED RoomCapacityHardConstraint - H8 Implementation

This constraint enforces that for any room that is NOT overbookable, the total number
of students from all exams scheduled in it during a single timeslot does not exceed its capacity.
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


class RoomCapacityHardConstraint(CPSATBaseConstraint):
    """H8: Room capacity hard constraint for non-overbookable rooms only."""

    dependencies = ["RoomAssignmentConsistencyConstraint"]

    def initialize_variables(self):
        """No local variables needed."""
        pass

    def add_constraints(self):
        """Add room capacity constraints for non-overbookable rooms."""
        constraints_added = 0

        for room_id, room in self._rooms.items():
            if getattr(room, "overbookable", False):
                continue

            capacity = getattr(room, "exam_capacity", room.capacity)
            if capacity <= 0:
                continue

            for slot_id in self._timeslots:
                capacity_terms = []
                for exam_id, exam in self._exams.items():
                    y_key = (exam_id, room_id, slot_id)
                    if y_key in self.y:
                        enrollment = getattr(exam, "expected_students", 0)
                        if enrollment > 0:
                            capacity_terms.append(enrollment * self.y[y_key])

                if capacity_terms:
                    self.model.Add(sum(capacity_terms) <= capacity)
                    constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} hard capacity constraints."
        )
