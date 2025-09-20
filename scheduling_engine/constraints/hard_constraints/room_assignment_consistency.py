# scheduling_engine/constraints/hard_constraints/room_assignment_consistency.py

"""
CORRECTED RoomAssignmentConsistencyConstraint - H3 Implementation

This replaces the incorrect RoomAssignmentBasicConstraint with the proper H3 constraint:
∑ y[e,r,s] = z[e,s] ∀ e ∈ E, s ∈ S

The constraint ensures that the sum of room assignments for an exam in a slot
equals the occupancy variable for that exam-slot combination.
"""

from collections import defaultdict
from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


class RoomAssignmentConsistencyConstraint(CPSATBaseConstraint):
    """H3: Room assignment consistent with occupancy - ∑ y[e,r,s] = z[e,s] ∀ e,s"""

    dependencies = ["OccupancyDefinitionConstraint"]
    constraint_category = "CORE"
    is_critical = True
    min_expected_constraints = 1

    def _create_local_variables(self):
        """No local variables needed for this constraint"""
        pass

    def _add_constraint_implementation(self):
        """Add room assignment consistency constraints"""
        constraints_added = 0

        # Group y variables by (exam_id, slot_id)
        exam_slot_rooms = defaultdict(list)

        for (exam_id, room_id, slot_id), y_var in self.y.items():
            exam_slot_rooms[(exam_id, slot_id)].append(y_var)

        # Add constraint: sum of room assignments = occupancy
        for (exam_id, slot_id), room_vars in exam_slot_rooms.items():
            z_key = (exam_id, slot_id)
            if z_key in self.z:
                z_var = self.z[z_key]
                # ∑ y[e,r,s] = z[e,s]
                self.model.Add(sum(room_vars) == z_var)
                constraints_added += 1

        self.constraint_count = constraints_added

        logger.info(
            f"{self.constraint_id}: Added {constraints_added} room assignment consistency constraints"
        )

        # Validation
        if constraints_added == 0:
            logger.error(f"CRITICAL: {self.constraint_id} generated 0 constraints!")
            if not self.y:
                logger.error("ROOT CAUSE: No y variables created!")
                raise RuntimeError(f"{self.constraint_id}: No y variables available")
            if not self.z:
                logger.error("ROOT CAUSE: No z variables created!")
                raise RuntimeError(f"{self.constraint_id}: No z variables available")
