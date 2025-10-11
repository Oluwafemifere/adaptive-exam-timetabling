# scheduling_engine/constraints/hard_constraints/invigilator_continuity.py
"""
InvigilatorContinuityConstraint - Hard Constraint for Phase 2

Ensures that for any multi-slot exam, the invigilator(s) assigned to the
room(s) where the exam is held remain the same for the entire duration of the exam.
"""
from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


class InvigilatorContinuityConstraint(CPSATBaseConstraint):
    """H-Type: Ensures invigilators stay in a room for an exam's full duration."""

    dependencies = ["RoomContinuityConstraint"]

    def initialize_variables(self):
        """No local variables needed."""
        pass

    async def add_constraints(self):
        """Add invigilator continuity constraints for multi-slot exams."""
        constraints_added = 0
        phase1_results = self.precomputed_data.get("phase1_results")
        if not phase1_results:
            logger.warning(
                f"{self.constraint_id}: Phase 1 results not found in precomputed data. Skipping."
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

            for room_id in self.problem.rooms:
                # The primary decision variable is if the exam is in this room at the start.
                y_start_var = self.y.get((exam_id, room_id, start_slot_id))
                # --- FIX 1: Check for None explicitly ---
                if y_start_var is None:
                    continue

                for inv_id in self.problem.invigilators:
                    # The invigilator's assignment status at the start time.
                    w_start_var = self.w.get((inv_id, room_id, start_slot_id))
                    # --- FIX 2: Check for None explicitly ---
                    if w_start_var is None:
                        continue

                    # For every subsequent slot the exam occupies...
                    for i in range(1, len(occupied_slots)):
                        next_slot_id = occupied_slots[i]
                        w_next_var = self.w.get((inv_id, room_id, next_slot_id))

                        # --- FIX 3: Check for None explicitly ---
                        if w_next_var is not None:
                            # If the exam is in this room (y_start_var=1), then the invigilator's
                            # assignment status in the next slot must equal their status in the start slot.
                            # This part is already correct! .OnlyEnforceIf is how you create conditional constraints.
                            self.model.Add(w_next_var == w_start_var).OnlyEnforceIf(
                                y_start_var
                            )
                            constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} invigilator continuity constraints."
        )
