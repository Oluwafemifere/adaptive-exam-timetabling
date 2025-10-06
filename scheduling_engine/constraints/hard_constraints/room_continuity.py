# scheduling_engine/constraints/hard_constraints/room_continuity.py
"""
CORRECTED RoomContinuityConstraint - Multi-Slot Exam Room Consistency
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
        """
        Adds constraints to ensure multi-slot exams remain in the same room(s)
        by linking room assignments across slots to the exam's single start time.
        """
        constraints_added = 0

        for exam_id, exam in self.problem.exams.items():
            duration_slots = self.problem.get_exam_duration_in_slots(exam_id)
            if duration_slots <= 1:
                continue

            for day in self.problem.days.values():
                # Iterate through all feasible start slots in the day for this exam
                for i in range(len(day.timeslots) - duration_slots + 1):
                    start_slot_id = day.timeslots[i].id
                    x_var = self.x.get((exam_id, start_slot_id))

                    # If there's no start variable for this slot, we can't constrain it.
                    if x_var is None:
                        continue

                    # For every room, enforce that if the exam starts in this slot (x_var=1),
                    # the room assignment must be the same for all subsequent slots.
                    for room_id in self.problem.rooms:
                        start_y_var = self.y.get((exam_id, room_id, start_slot_id))
                        if start_y_var is None:
                            continue

                        for j in range(1, int(duration_slots)):
                            next_slot_id = day.timeslots[i + j].id
                            next_y_var = self.y.get((exam_id, room_id, next_slot_id))

                            if next_y_var is not None:
                                # CORRECTED LOGIC:
                                # This is a one-way implication. If the exam starts here,
                                # then the room choice for the next slot must be the same
                                # as the room choice for the start slot.
                                self.model.Add(next_y_var == start_y_var).OnlyEnforceIf(
                                    x_var
                                )
                                constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} room continuity constraints."
        )
