# scheduling_engine/constraints/hard_constraints/room_continuity.py
"""
Optimized RoomContinuityConstraint - Multi-Slot Exam Room Consistency
"""

import math
from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


class RoomContinuityConstraint(CPSATBaseConstraint):
    """H9: Ensure exam uses same room across all occupied slots."""

    dependencies = []

    def initialize_variables(self):
        """No local variables needed."""
        pass

    def add_constraints(self):
        """Adds constraints to ensure multi-slot exams remain in the same room(s)."""
        constraints_added = 0

        for exam_id, exam in self.problem.exams.items():
            duration_slots = self.problem.get_exam_duration_in_slots(exam_id)
            if duration_slots <= 1:
                continue

            for room_id in self.problem.rooms:
                for day in self.problem.days.values():
                    # Check each possible start slot within the day
                    for i in range(len(day.timeslots) - duration_slots + 1):
                        start_slot_id = day.timeslots[i].id

                        # The y-variable for the start of the exam in this room
                        start_y_var = self.y.get((exam_id, room_id, start_slot_id))
                        if start_y_var is None:
                            continue

                        # Constrain subsequent slots
                        for j in range(1, int(duration_slots)):
                            next_slot_id = day.timeslots[i + j].id
                            next_y_var = self.y.get((exam_id, room_id, next_slot_id))
                            if next_y_var is not None:
                                # If the exam starts here (start_y_var=1), it must also be in the same room for the next slot.
                                self.model.Add(next_y_var == start_y_var)
                                constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} room continuity constraints."
        )
