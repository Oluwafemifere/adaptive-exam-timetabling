# scheduling_engine/constraints/soft_constraints/overbooking_penalty.py
"""
OverbookingPenaltyConstraint - S1 Implementation (PARAMETERIZED & FIXED)
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
from scheduling_engine.core.constraint_types import ConstraintDefinition
import logging

logger = logging.getLogger(__name__)


class OverbookingPenaltyConstraint(CPSATBaseConstraint):
    """S1: Enhanced overbooking penalty for rooms that allow overbooking"""

    dependencies = []

    def __init__(self, definition: ConstraintDefinition, problem, shared_vars, model):
        super().__init__(definition, problem, shared_vars, model)
        self.penalty_weight = self.definition.weight
        logger.info(
            f"🟡 Initializing SOFT constraint {self.constraint_id} with weight {self.penalty_weight}"
        )

    def initialize_variables(self):
        """Create auxiliary variables for overbooking penalty."""
        self.overbook_extra_vars = {}

        for room_id, room in self._rooms.items():
            if getattr(room, "overbookable", False):
                capacity = getattr(room, "exam_capacity", room.capacity)
                # A simple upper bound for overbooking
                max_overbook = sum(
                    exam.expected_students for exam in self._exams.values()
                )

                for slot_id in self._timeslots:
                    key = (room_id, slot_id)
                    self.overbook_extra_vars[key] = self.model.NewIntVar(
                        0, max_overbook, f"overbookExtra_{room_id}_{slot_id}"
                    )

    def add_constraints(self):
        """Add overbooking penalty constraints."""
        constraints_added = 0

        for (room_id, slot_id), overbook_var in self.overbook_extra_vars.items():
            room = self._rooms[room_id]
            capacity = getattr(room, "exam_capacity", room.capacity)

            seated_terms = [
                exam.expected_students * self.y[key]
                for exam_id, exam in self._exams.items()
                if (key := (exam_id, room_id, slot_id)) in self.y
            ]

            if seated_terms:
                total_seated_var = self.model.NewIntVar(
                    0, 10000, f"seated_{room_id}_{slot_id}"
                )
                self.model.Add(total_seated_var == sum(seated_terms))
                self.model.Add(overbook_var >= total_seated_var - capacity)
                self.model.Add(overbook_var >= 0)
                constraints_added += 3
            else:
                self.model.Add(overbook_var == 0)
                constraints_added += 1

        self.penalty_terms.extend(
            (self.penalty_weight, var) for var in self.overbook_extra_vars.values()
        )
        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} overbooking penalty constraints."
        )
