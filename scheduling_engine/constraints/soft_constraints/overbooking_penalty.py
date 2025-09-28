"""
OverbookingPenaltyConstraint - S1 Implementation (FIXED)

S1: Enhanced overbooking penalty

For overbookable_r = 1 rooms, allow limited overbooking up to maxOverbookAbsolute_r.
Penalty: W_overbook × ∑_{r,s} overbookExtra_{r,s} where W_overbook = 1000.

FIX: The implementation was incomplete. It now correctly calculates the number of
seated students in each room, links it to the overbooking penalty variable, and
adds the penalty term to the objective function.
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
                # Max possible students = capacity + overbooking allowance
                max_seated = capacity + max_overbook_absolute

                for slot_id in self._timeslots:
                    seated_key = (room_id, slot_id)
                    # Variable for number of seated students
                    self.seated_vars[seated_key] = self.model.NewIntVar(
                        0,
                        max_seated,
                        f"seated_{room_id}_{slot_id}",
                    )

                    # Variable for extra students beyond capacity
                    self.overbook_extra_vars[seated_key] = self.model.NewIntVar(
                        0, max_overbook_absolute, f"overbookExtra_{room_id}_{slot_id}"
                    )

    def _add_constraint_implementation(self):
        """Add overbooking penalty constraints"""
        constraints_added = 0

        # For each room and slot that is overbookable
        for (room_id, slot_id), overbook_var in self.overbook_extra_vars.items():
            room = self._rooms[room_id]
            capacity = getattr(room, "capacity", 0)
            seated_var = self.seated_vars[(room_id, slot_id)]

            # Calculate total seated students: seated_{r,s} = ∑_e enrol_e × y_{e,r,s}
            seated_terms = []
            for exam_id, exam in self._exams.items():
                enrollment = getattr(exam, "enrollment", 0)
                y_key = (exam_id, room_id, slot_id)
                if y_key in self.y:
                    seated_terms.append(enrollment * self.y[y_key])

            # Link the sum of enrollments to the seated_var
            if seated_terms:
                self.model.Add(seated_var == sum(seated_terms))
                constraints_added += 1
            else:
                self.model.Add(seated_var == 0)
                constraints_added += 1

            # Define overbooking: overbookExtra_{r,s} >= seated_{r,s} - capacity_r
            # This captures the number of students beyond the normal capacity.
            self.model.Add(overbook_var >= seated_var - capacity)
            constraints_added += 1

        # Store penalty terms for the objective function
        self.penalty_terms = [
            (self.penalty_weight, var) for var in self.overbook_extra_vars.values()
        ]

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
