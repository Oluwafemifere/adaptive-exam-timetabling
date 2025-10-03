# scheduling_engine/constraints/hard_constraints/start_feasibility.py
"""
StartFeasibilityConstraint - H11 Implementation

This constraint ensures that exams can only start at feasible slots where they
can complete within the same day.
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging
import math

logger = logging.getLogger(__name__)


class StartFeasibilityConstraint(CPSATBaseConstraint):
    """H11: Start feasibility and slot fit constraint."""

    dependencies = []

    def initialize_variables(self):
        """No local variables needed for this constraint."""
        pass

    def add_constraints(self):
        """Add start feasibility constraints."""
        constraints_added = 0
        for (exam_id, slot_id), x_var in self.x.items():
            if not self._is_start_feasible(exam_id, slot_id):
                self.model.Add(x_var == 0)
                constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} start infeasibility constraints."
        )

    def _is_start_feasible(self, exam_id, slot_id):
        """Check if an exam can start at a given slot and finish within the day."""
        return self.problem.is_start_feasible(exam_id, slot_id)
