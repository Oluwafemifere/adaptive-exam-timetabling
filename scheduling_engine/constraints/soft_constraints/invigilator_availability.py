# scheduling_engine/constraints/soft_constraints/invigilator_availability.py
"""
InvigilatorAvailabilityConstraint - S6 Implementation (PARAMETERIZED & FIXED)
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
from scheduling_engine.core.constraint_types import ConstraintDefinition
import logging

logger = logging.getLogger(__name__)


class InvigilatorAvailabilityConstraint(CPSATBaseConstraint):
    """S6: Invigilator availability violation penalty for unavailable assignments"""

    dependencies = []

    def __init__(self, definition: ConstraintDefinition, problem, shared_vars, model):
        super().__init__(definition, problem, shared_vars, model)
        self.penalty_weight = self.definition.weight
        logger.info(
            f"🟡 Initializing SOFT constraint {self.constraint_id} with weight {self.penalty_weight}"
        )

    def initialize_variables(self):
        """Create auxiliary variables for availability violations."""
        self.availability_viol_vars = {}
        for inv_id, invigilator in self.problem.invigilators.items():
            # availability is a dict of {date_str: [period_name, ...]}
            for date_str, periods in getattr(invigilator, "availability", {}).items():
                for day in self.problem.days.values():
                    if str(day.date) == date_str:
                        for timeslot in day.timeslots:
                            if "all" in periods or timeslot.name in periods:
                                key = (inv_id, timeslot.id)
                                self.availability_viol_vars[key] = (
                                    self.model.NewBoolVar(
                                        f"availabilityViol_{inv_id}_{timeslot.id}"
                                    )
                                )

    def add_constraints(self):
        """Add invigilator availability penalty constraints."""
        constraints_added = 0
        if not self.u:
            logger.info(
                f"{self.constraint_id}: No invigilator variables found, skipping."
            )
            return

        if not self.availability_viol_vars:
            logger.info(
                f"{self.constraint_id}: No availability violations to track, skipping."
            )
            return

        for (inv_id, slot_id), viol_var in self.availability_viol_vars.items():
            # Sum of all assignments for this invigilator in this unavailable slot
            assignments_in_slot = [
                u_var
                for (u_inv, _, _, u_slot), u_var in self.u.items()
                if u_inv == inv_id and u_slot == slot_id
            ]

            if assignments_in_slot:
                # If sum > 0, a violation occurred. viol_var must be 1.
                self.model.Add(sum(assignments_in_slot) > 0).OnlyEnforceIf(viol_var)
                self.model.Add(sum(assignments_in_slot) == 0).OnlyEnforceIf(
                    viol_var.Not()
                )
                constraints_added += 2

        self.penalty_terms.extend(
            (self.penalty_weight, var) for var in self.availability_viol_vars.values()
        )
        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} invigilator availability penalty constraints."
        )
