# scheduling_engine/constraints/hard_constraints/invigilator_single_presence.py
"""
CRITICAL FIX - InvigilatorSinglePresenceConstraint
This constraint ensures that an invigilator can only be assigned to ONE room at a time during any given time slot.
An invigilator cannot be in multiple rooms simultaneously.
"""

from collections import defaultdict
from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


class InvigilatorSinglePresenceConstraint(CPSATBaseConstraint):
    """
    H12: Ensure invigilators are assigned to at most one room per time slot.

    Constraint Logic:
    - For each invigilator I and time slot T:
    - Sum of all u(I, exam, room, T) variables <= 1
    - This prevents an invigilator from being assigned to multiple rooms simultaneously
    """

    dependencies = ["MinimumInvigilatorsConstraint"]

    def initialize_variables(self):
        """No local variables needed for this constraint."""
        pass

    def add_constraints(self):
        """
        Enhanced constraint to prevent invigilator conflicts.

        Core Logic: For each (invigilator, timeslot) pair, ensure that the invigilator
        is assigned to at most one room/exam combination at that time.
        """
        uvars = self.u
        if not uvars:
            logger.info(f"{self.constraint_id}: No u variables, skipping.")
            self.constraint_count = 0
            return

        logger.info(
            f"{self.constraint_id}: Processing {len(uvars)} invigilator assignment variables."
        )

        invigilator_slot_assignments = defaultdict(list)
        for (invid, examid, roomid, slotid), uvar in uvars.items():
            key = (invid, slotid)
            invigilator_slot_assignments[key].append(uvar)

        constraints_added = 0
        for (invid, slotid), assignments in invigilator_slot_assignments.items():
            if len(assignments) > 1:
                # CRITICAL CONSTRAINT: An invigilator can only be in one place at a time
                # Sum of all u(invid, *, *, slotid) <= 1
                self.model.Add(sum(assignments) <= 1)
                constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} invigilator single-presence constraints."
        )
