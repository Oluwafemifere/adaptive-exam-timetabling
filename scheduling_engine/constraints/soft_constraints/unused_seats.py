"""
UnusedSeatsConstraint - S8 Implementation

S8: Unused seats consolidation (enhanced)

For each room r and slot s, define unusedSeatsPenalty_{r,s} = max(0, cap_r - seated_{r,s}):
Penalty: W_unused × ∑_{r,s} unusedSeatsPenalty_{r,s} where W_unused = 50.
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


class UnusedSeatsConstraint(CPSATBaseConstraint):
    """S8: Unused seats consolidation penalty to encourage efficient room utilization"""

    dependencies = ["RoomAssignmentBasicConstraint"]
    constraint_category = "SOFT_CONSTRAINTS"
    is_critical = False
    min_expected_constraints = 0  # May be 0 if all rooms are fully utilized

    def __init__(self, constraint_id, problem, shared_vars, model, factory=None):
        super().__init__(constraint_id, problem, shared_vars, model, factory)
        self.penalty_weight = 50  # W_unused
        logger.info(
            f"🟡 Initializing SOFT constraint {constraint_id} with weight {self.penalty_weight}"
        )

    def _create_local_variables(self):
        """Create auxiliary variables for unused seats penalty"""
        self.unused_seats_vars = {}
        self.seated_vars = {}

        # Create auxiliary variables for each room and slot
        for room_id in self._rooms:
            room = self._rooms[room_id]
            capacity = getattr(room, "capacity", 0)

            for slot_id in self._timeslots:
                seated_key = (room_id, slot_id)

                # Variable for number of seated students
                self.seated_vars[seated_key] = self.model.NewIntVar(
                    0, capacity, f"seated_{room_id}_{slot_id}"
                )

                # Variable for unused seats (penalty term)
                self.unused_seats_vars[seated_key] = self.model.NewIntVar(
                    0, capacity, f"unusedSeats_{room_id}_{slot_id}"
                )

    def _add_constraint_implementation(self):
        """Add unused seats penalty constraints"""
        constraints_added = 0

        if not self.y:
            logger.info(f"{self.constraint_id}: No room assignment variables found")
            self.constraint_count = 0
            return

        if not self.unused_seats_vars:
            logger.info(f"{self.constraint_id}: No unused seats variables created")
            self.constraint_count = 0
            return

        # For each room and slot
        for room_id in self._rooms:
            room = self._rooms[room_id]
            capacity = getattr(room, "capacity", 0)

            for slot_id in self._timeslots:
                seated_key = (room_id, slot_id)

                if seated_key not in self.seated_vars:
                    continue

                seated_var = self.seated_vars[seated_key]
                unused_seats_var = self.unused_seats_vars[seated_key]

                # Calculate total seated students: seated_{r,s} = ∑_e enrol_e × y_{e,r,s}
                seated_terms = []
                for exam_id in self._exams:
                    exam = self._exams[exam_id]
                    enrollment = getattr(exam, "enrollment", 0)

                    y_key = (exam_id, room_id, slot_id)
                    if y_key in self.y:
                        seated_terms.append(enrollment * self.y[y_key])

                if seated_terms:
                    # seated_{r,s} = ∑_e enrol_e × y_{e,r,s}
                    self.model.Add(seated_var == sum(seated_terms))
                    constraints_added += 1
                else:
                    # No exams assigned to this room-slot, so seated = 0
                    self.model.Add(seated_var == 0)
                    constraints_added += 1

                # unusedSeats_{r,s} = max(0, cap_r - seated_{r,s})
                # This is equivalent to: unusedSeats_{r,s} = cap_r - seated_{r,s}
                # when we only count positive unused seats in the penalty
                self.model.Add(unused_seats_var == capacity - seated_var)
                constraints_added += 1

        # Store penalty terms for objective function
        self.penalty_terms = []
        for seated_key, unused_seats_var in self.unused_seats_vars.items():
            self.penalty_terms.append((self.penalty_weight, unused_seats_var))

        self.constraint_count = constraints_added

        if constraints_added == 0:
            logger.info(f"{self.constraint_id}: No unused seats constraints needed")
        else:
            logger.info(
                f"{self.constraint_id}: Added {constraints_added} unused seats penalty constraints"
            )

    def get_penalty_terms(self):
        """Get penalty terms for the objective function"""
        return getattr(self, "penalty_terms", [])

    def get_statistics(self):
        """Get constraint statistics"""
        stats = super().get_constraint_statistics()
        room_slot_pairs = (
            len(self.unused_seats_vars) if hasattr(self, "unused_seats_vars") else 0
        )
        stats.update(
            {
                "penalty_weight": self.penalty_weight,
                "room_slot_pairs": room_slot_pairs,
                "seated_variables": (
                    len(self.seated_vars) if hasattr(self, "seated_vars") else 0
                ),
                "unused_seats_variables": room_slot_pairs,
                "penalty_terms": len(getattr(self, "penalty_terms", [])),
            }
        )
        return stats
