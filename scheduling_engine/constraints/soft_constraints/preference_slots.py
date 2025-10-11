# scheduling_engine/constraints/soft_constraints/preference_slots.py
"""
PreferenceSlotsConstraint - S2 Implementation (PARAMETERIZED & FIXED)
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
from scheduling_engine.core.constraint_types import ConstraintDefinition
import logging

logger = logging.getLogger(__name__)


class PreferenceSlotsConstraint(CPSATBaseConstraint):
    """S2: Preference slots penalty for exams not scheduled in preferred time slots"""

    dependencies = []

    def __init__(self, definition: ConstraintDefinition, problem, shared_vars, model):
        super().__init__(definition, problem, shared_vars, model)
        self.penalty_weight = self.definition.weight
        logger.info(
            f"🟡 Initializing SOFT constraint {self.constraint_id} with weight {self.penalty_weight}"
        )

    def initialize_variables(self):
        """Create auxiliary variables for preference violations."""
        self.pref_viol_vars = {}
        for exam_id, exam in self._exams.items():
            if getattr(exam, "morning_only", False):
                self.pref_viol_vars[exam_id] = self.model.NewBoolVar(
                    f"prefViol_{exam_id}"
                )

    async def add_constraints(self):
        """Add preference slots penalty constraints."""
        constraints_added = 0
        if not self.pref_viol_vars:
            logger.info(f"{self.constraint_id}: No exam preferences found.")
            return

        for exam_id, viol_var in self.pref_viol_vars.items():
            # An exam is morning_only. Penalize if scheduled in a non-morning slot.
            non_morning_x_vars = []
            for slot_id, timeslot in self._timeslots.items():
                if "morning" not in timeslot.name.lower():
                    if (key := (exam_id, slot_id)) in self.x:
                        non_morning_x_vars.append(self.x[key])

            if non_morning_x_vars:
                # If any non-morning var is 1, the violation is 1.
                self.model.AddBoolOr(non_morning_x_vars).OnlyEnforceIf(viol_var)
                self.model.Add(sum(non_morning_x_vars) == 0).OnlyEnforceIf(
                    viol_var.Not()
                )
                constraints_added += 2

        self.penalty_terms.extend(
            (self.penalty_weight, var) for var in self.pref_viol_vars.values()
        )
        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} preference penalty constraints."
        )
