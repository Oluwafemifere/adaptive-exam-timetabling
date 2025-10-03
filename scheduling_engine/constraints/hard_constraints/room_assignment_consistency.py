# scheduling_engine/constraints/hard_constraints/room_assignment_consistency.py
"""
CORRECTED RoomAssignmentConsistencyConstraint - H3 Implementation

This constraint ensures that the sum of room assignments for an exam in a slot
equals the occupancy variable for that exam-slot combination.
"""

from collections import defaultdict
from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


class RoomAssignmentConsistencyConstraint(CPSATBaseConstraint):
    """H3: Room assignment consistent with occupancy - ∑ y[e,r,s] = z[e,s] ∀ e,s"""

    dependencies = ["OccupancyDefinitionConstraint"]

    def initialize_variables(self):
        """No local variables needed for this constraint."""
        pass

    def add_constraints(self):
        """Add room assignment consistency constraints."""
        constraints_added = 0

        exam_slot_rooms = defaultdict(list)
        for (exam_id, room_id, slot_id), y_var in self.y.items():
            exam_slot_rooms[(exam_id, slot_id)].append(y_var)

        for (exam_id, slot_id), room_vars in exam_slot_rooms.items():
            z_key = (exam_id, slot_id)
            if z_key in self.z:
                z_var = self.z[z_key]
                self.model.Add(sum(room_vars) == z_var)
                constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} room assignment consistency constraints."
        )

        if constraints_added == 0 and (self.y or self.z):
            logger.error(
                f"CRITICAL: {self.constraint_id} generated 0 constraints despite available variables!"
            )
            raise RuntimeError(
                f"{self.constraint_id}: Failed to generate any constraints."
            )
