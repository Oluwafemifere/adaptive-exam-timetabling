# scheduling_engine/constraints/hard_constraints/invigilator_single_presence.py
"""
REWRITTEN - InvigilatorSinglePresenceConstraint (Simplified Model)
Ensures an invigilator can only be assigned to ONE room in any given time slot.
"""

from collections import defaultdict
from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


class InvigilatorSinglePresenceConstraint(CPSATBaseConstraint):
    """
    H12: Ensure invigilators are assigned to at most one room per time slot.

    Constraint Logic (Simplified Model):
    - For each invigilator `i` and time slot `s`:
    - The sum of all assignment variables w(i, r, s) over all rooms `r` must be <= 1.
    """

    dependencies = []

    def initialize_variables(self):
        """No local variables needed for this constraint."""
        pass

    def add_constraints(self):
        """
        Prevents an invigilator from being assigned to multiple rooms at the same time.
        """
        w_vars = self.w
        if not w_vars:
            logger.info(
                f"{self.constraint_id}: No invigilator assignment variables (w_vars), skipping."
            )
            self.constraint_count = 0
            return

        logger.info(
            f"{self.constraint_id}: Processing {len(w_vars)} invigilator-in-room assignment variables."
        )

        invigilator_slot_assignments = defaultdict(list)
        # The key for a `w_var` is (invigilator_id, room_id, slot_id)
        for (inv_id, room_id, slot_id), w_var in w_vars.items():
            grouping_key = (inv_id, slot_id)
            invigilator_slot_assignments[grouping_key].append(w_var)

        constraints_added = 0
        for (
            inv_id,
            slot_id,
        ), assignments in invigilator_slot_assignments.items():
            if len(assignments) > 1:
                # An invigilator can only be in one room in a given slot.
                self.model.Add(sum(assignments) <= 1)
                constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} invigilator single-presence constraints."
        )
