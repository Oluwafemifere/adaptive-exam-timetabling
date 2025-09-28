"""
OverbookingPenaltyConstraint - S1 Implementation

S1: Enhanced overbooking penalty

For overbookable_r = 1 rooms, allow limited overbooking up to maxOverbookAbsolute_r.
Penalty: W_overbook × ∑_{r,s} overbookExtra_{r,s} where W_overbook = 1000.
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging
import math

logger = logging.getLogger(__name__)


class OverbookingPenaltyConstraint(CPSATBaseConstraint):
    """S1: Enhanced overbooking penalty for rooms that allow overbooking"""

    dependencies = []
    constraint_category = "SOFT_CONSTRAINTS"
    is_critical = False
    min_expected_constraints = 0  # May be 0 if no overbookable rooms

    def __init__(self, constraint_id, problem, shared_vars, model, factory=None):
        super().__init__(constraint_id, problem, shared_vars, model, factory)
        self.penalty_weight = 1000  # W_overbook
        logger.info(
            f"🟡 Initializing SOFT constraint {constraint_id} with weight {self.penalty_weight}"
        )

    def _create_local_variables(self):
        """Create auxiliary variables for overbooking penalty"""
        self.overbook_extra_vars = {}
        self.seated_vars = {}

        # Create auxiliary variables for each overbookable room and slot
        for room_id in self._rooms:
            room = self._rooms[room_id]
            is_overbookable = getattr(room, "overbookable", False)

            if is_overbookable:
                capacity = getattr(room, "capacity", 0)
                overbook_rate = getattr(room, "overbook_rate", 0.1)
                max_overbook_absolute = int(capacity * overbook_rate)

                for slot_id in self._timeslots:
                    # Variable for number of seated students
                    seated_key = (room_id, slot_id)
                    self.seated_vars[seated_key] = self.model.NewIntVar(
                        0,
                        capacity + max_overbook_absolute,
                        f"seated_{room_id}_{slot_id}",
                    )

                    # Variable for extra students beyond capacity
                    self.overbook_extra_vars[seated_key] = self.model.NewIntVar(
                        0, max_overbook_absolute, f"overbookExtra_{room_id}_{slot_id}"
                    )

    def _add_constraint_implementation(self):
        """Add overbooking penalty constraints"""
        constraints_added = 0

        for room_id, room in self._rooms.items():
            is_overbookable = getattr(room, "overbookable", False)
            if not is_overbookable:
                continue  # Only process overbookable rooms

            capacity = getattr(room, "capacity", 0)
            overbook_rate = getattr(room, "overbook_rate", 0.1)
            max_overbook_absolute = int(capacity * overbook_rate)

            for slot_id in self._timeslots:
                seated_key = (room_id, slot_id)

                # Ensure we don't exceed maximum overbooking limit
                self.model.Add(
                    self.overbook_extra_vars[seated_key] <= max_overbook_absolute
                )
                constraints_added += 1

        self.constraint_count = constraints_added

        if constraints_added == 0:
            logger.info(f"{self.constraint_id}: No overbooking constraints needed")
        else:
            logger.info(
                f"{self.constraint_id}: Added {constraints_added} overbooking penalty constraints"
            )

    def get_penalty_terms(self):
        """Get penalty terms for the objective function"""
        return getattr(self, "penalty_terms", [])

    def get_statistics(self):
        """Get constraint statistics"""
        stats = super().get_constraint_statistics()
        stats.update(
            {
                "penalty_weight": self.penalty_weight,
                "overbookable_rooms": len(
                    [
                        r
                        for r in self._rooms.values()
                        if getattr(r, "overbookable", False)
                    ]
                ),
                "overbook_variables": len(self.overbook_extra_vars),
                "penalty_terms": len(getattr(self, "penalty_terms", [])),
            }
        )
        return stats
