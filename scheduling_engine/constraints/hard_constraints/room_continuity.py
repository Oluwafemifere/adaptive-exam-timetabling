# scheduling_engine/constraints/hard_constraints/room_continuity.py
"""
CORRECTED RoomContinuityConstraint - Multi-Slot Exam Room Consistency for Full Phase 2 Model
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

    async def add_constraints(self):
        """
        Adds constraints to ensure multi-slot exams remain in the same room(s)
        for the full duration in the Phase 2 model.
        """
        constraints_added = 0

        # The Phase 2 model is provided with the fixed start times from Phase 1.
        phase1_results = self.precomputed_data.get("phase1_results")
        if not phase1_results:
            logger.warning(
                f"{self.constraint_id}: Phase 1 results not found, cannot enforce room continuity. Skipping."
            )
            self.constraint_count = 0
            return

        for exam_id, exam in self.problem.exams.items():
            duration_slots = self.problem.get_exam_duration_in_slots(exam_id)
            if duration_slots <= 1:
                continue

            start_slot_id, _ = phase1_results.get(exam_id, (None, None))
            if not start_slot_id:
                continue

            occupied_slots = self.problem.get_occupancy_slots(exam_id, start_slot_id)
            if len(occupied_slots) <= 1:
                continue

            # We enforce that if an exam is assigned to a room in its start slot,
            # it must also be assigned to that same room in all subsequent slots it occupies.
            for room_id in self.problem.rooms:
                start_y_var = self.y.get((exam_id, room_id, start_slot_id))
                if start_y_var is None:
                    continue

                for i in range(1, len(occupied_slots)):
                    next_slot_id = occupied_slots[i]
                    next_y_var = self.y.get((exam_id, room_id, next_slot_id))

                    if next_y_var is not None:
                        # The room assignment for subsequent slots must be identical to the start slot.
                        # This simple equivalence works because another constraint ensures the exam
                        # is assigned to at least one room at its start time.
                        self.model.Add(next_y_var == start_y_var)
                        constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} room continuity constraints for full Phase 2 model."
        )
