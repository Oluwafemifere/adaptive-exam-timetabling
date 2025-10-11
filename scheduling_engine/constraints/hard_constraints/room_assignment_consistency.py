# scheduling_engine/constraints/hard_constraints/room_assignment_consistency.py
"""
CORRECTED RoomAssignmentConsistencyConstraint - H3 Implementation

This constraint ensures that the sum of room assignments for an exam in a slot
equals the occupancy variable for that exam-slot combination in Phase 1, and
ensures every exam in a subproblem is placed in Phase 2.
"""

from collections import defaultdict
from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


class RoomAssignmentConsistencyConstraint(CPSATBaseConstraint):
    """H3: Ensures consistency between room assignments and exam presence in a slot."""

    dependencies = ["OccupancyDefinitionConstraint"]

    def initialize_variables(self):
        """No local variables needed for this constraint."""
        pass

    async def add_constraints(self):
        """
        Add room assignment consistency constraints.
        Handles both Phase 1 (linking to z_vars) and Phase 2 (ensuring placement).
        """
        constraints_added = 0
        exam_slot_rooms = defaultdict(list)
        for (exam_id, room_id, slot_id), y_var in self.y.items():
            exam_slot_rooms[(exam_id, slot_id)].append(y_var)

        # Detect the phase by checking if z_vars were created for this model.
        is_phase1_mode = bool(self.z)

        if is_phase1_mode:
            # --- PHASE 1 LOGIC (UNCHANGED) ---
            # Link room assignments (y) to occupancy (z).
            logger.debug(
                f"{self.constraint_id}: Running in Phase 1 mode (linking y -> z)."
            )
            for (exam_id, slot_id), room_vars in exam_slot_rooms.items():
                z_key = (exam_id, slot_id)
                if z_key in self.z:
                    z_var = self.z[z_key]
                    # If an exam occupies a slot (z=1), it must be in at least one room (sum(y) > 0).
                    self.model.Add(sum(room_vars) > 0).OnlyEnforceIf(z_var)
                    # If an exam does not occupy a slot (z=0), it cannot be in any room (sum(y) = 0).
                    self.model.Add(sum(room_vars) == 0).OnlyEnforceIf(z_var.Not())
                    constraints_added += 2
        else:
            # --- START OF FIX ---
            # --- PHASE 2 LOGIC (CORRECTED) ---
            # For a given subproblem, every exam must be placed. Small exams go into
            # exactly one room, large exams can be split.
            logger.debug(
                f"{self.constraint_id}: Running in Phase 2 mode (ensuring room assignment)."
            )

            # Find the capacity of the largest single room.
            max_room_capacity = 0
            if self.problem.rooms:
                max_room_capacity = max(
                    r.exam_capacity for r in self.problem.rooms.values()
                )

            for (exam_id, slot_id), room_vars in exam_slot_rooms.items():
                exam = self.problem.exams.get(exam_id)
                if not exam:
                    continue

                # If the exam can fit into the largest single room, enforce it is placed in exactly one.
                if exam.expected_students <= max_room_capacity:
                    self.model.Add(sum(room_vars) == 1)
                else:
                    # If the exam is too large for any single room, it must be split,
                    # so it needs at least one room (and the capacity constraint will handle the rest).
                    self.model.Add(sum(room_vars) >= 1)
                constraints_added += 1
            # --- END OF FIX ---

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} room assignment consistency constraints."
        )

        if constraints_added == 0 and self.y:
            logger.error(
                f"CRITICAL: {self.constraint_id} generated 0 constraints despite available y_vars!"
            )
            raise RuntimeError(
                f"{self.constraint_id}: Failed to generate any constraints."
            )
