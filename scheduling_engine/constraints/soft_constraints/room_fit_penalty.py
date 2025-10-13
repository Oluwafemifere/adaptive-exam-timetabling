# scheduling_engine/constraints/soft_constraints/room_fit_penalty.py
"""
RoomFitPenaltyConstraint - Soft Constraint for Phase 2

This constraint penalizes assigning an exam to a room that is much larger than necessary.
It encourages the solver to find the "best fit" room for each exam, leading to
more efficient space utilization and preventing all exams from being placed in a single large room.
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
from scheduling_engine.core.constraint_types import ConstraintDefinition
import logging

logger = logging.getLogger(__name__)


class RoomFitPenaltyConstraint(CPSATBaseConstraint):
    """S-Type: Penalize wasted space in room assignments."""

    dependencies = []

    def __init__(self, definition: ConstraintDefinition, problem, shared_vars, model):
        super().__init__(definition, problem, shared_vars, model)
        # The weight can be low; the goal is just to guide the choice between valid options.
        # --- START OF FIX ---
        # The parameter value might be a string, so it must be cast to a float for calculations.
        self.penalty_weight = float(
            definition.get_parameter_value("weight", default=1.0)
        )
        # --- END OF FIX ---
        logger.info(
            f"🟡 Initializing SOFT constraint {self.constraint_id} with weight {self.penalty_weight}"
        )

    def initialize_variables(self):
        """No new variables are needed; we will create penalty terms directly from y_vars."""
        pass

    async def add_constraints(self):
        """Add penalties for assigning exams to oversized rooms."""
        # This constraint should only run in Phase 2 when y_vars are present.
        if not self.y:
            logger.debug(
                f"{self.constraint_id}: No room assignment variables (y), skipping."
            )
            self.constraint_count = 0
            return

        constraints_added = 0
        for (exam_id, room_id, slot_id), y_var in self.y.items():
            exam = self.problem.exams.get(exam_id)
            room = self.problem.rooms.get(room_id)

            if not exam or not room:
                continue

            # Only penalize if the room is larger than the exam's student count.
            if room.exam_capacity > exam.expected_students:
                wasted_space = room.exam_capacity - exam.expected_students

                # The penalty is the amount of wasted space multiplied by the assignment variable.
                # The base weight is applied when summing up the objective function.
                penalty_value = int(self.penalty_weight * wasted_space)
                self.penalty_terms.append((penalty_value, y_var))
                constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added penalty logic for {constraints_added} potential room assignments to encourage better fit."
        )
