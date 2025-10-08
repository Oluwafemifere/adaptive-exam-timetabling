# scheduling_engine/constraints/soft_constraints/invigilator_load_balance.py
"""
REWRITTEN - InvigilatorLoadBalanceConstraint (Simplified Model)
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
from scheduling_engine.core.constraint_types import ConstraintDefinition
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class InvigilatorLoadBalanceConstraint(CPSATBaseConstraint):
    """S4: Invigilator load imbalance penalty for uneven workload distribution."""

    dependencies = []

    def __init__(self, definition: ConstraintDefinition, problem, shared_vars, model):
        super().__init__(definition, problem, shared_vars, model)
        self.penalty_weight = self.definition.weight
        logger.info(
            f"🟡 Initializing SOFT constraint {self.constraint_id} with weight {self.penalty_weight}"
        )

    def initialize_variables(self):
        """Create auxiliary variables for load balance."""
        self.work_vars = {}
        self.load_imbalance_vars = {}
        self.avg_work_var = None

        if not self.problem.invigilators or not self.w:
            return

        total_invigilators = len(self.problem.invigilators)
        # An invigilator's work is the number of slots they are assigned to.
        max_work = len(self.problem.timeslots)

        for inv_id in self.problem.invigilators:
            self.work_vars[inv_id] = self.model.NewIntVar(0, max_work, f"work_{inv_id}")
            self.load_imbalance_vars[inv_id] = self.model.NewIntVar(
                0, max_work, f"loadImbalance_{inv_id}"
            )

        if total_invigilators > 0:
            self.avg_work_var = self.model.NewIntVar(0, max_work, "avgWork")

    def add_constraints(self):
        """Add invigilator load balance constraints."""
        constraints_added = 0
        if not self.work_vars:
            logger.info(
                f"{self.constraint_id}: No invigilators or variables, skipping."
            )
            return

        total_invigilators = len(self.problem.invigilators)

        # Group assignment variables w(inv, room, slot) by invigilator
        invigilator_assignments = defaultdict(list)
        for (inv_id, room_id, slot_id), w_var in self.w.items():
            invigilator_assignments[inv_id].append(w_var)

        for inv_id, work_var in self.work_vars.items():
            # The work for an invigilator is the sum of all slots they work in.
            # Since Phase 2 is per-slot, this represents their work in this slot.
            # A full load balance requires Phase 1 info, but this penalizes being
            # assigned to many rooms at once (which is impossible with H12).
            # The primary logic holds: sum of assignments defines work.
            work_terms = invigilator_assignments.get(inv_id, [])
            if work_terms:
                self.model.Add(work_var == sum(work_terms))
                constraints_added += 1

        if self.avg_work_var is not None and total_invigilators > 0:
            total_work = list(self.work_vars.values())
            if total_work:
                # Note: In a Phase 2 subproblem, this calculates the average for just one slot.
                # The penalty still works to distribute invigilators evenly among assignments
                # if multiple sub-optimal but feasible solutions exist.
                self.model.Add(
                    self.avg_work_var * total_invigilators == sum(total_work)
                )
                constraints_added += 1

        if self.avg_work_var is not None:
            for inv_id, imbalance_var in self.load_imbalance_vars.items():
                work_var = self.work_vars[inv_id]
                diff_var = self.model.NewIntVar(
                    -len(self.problem.timeslots),
                    len(self.problem.timeslots),
                    f"diff_{inv_id}",
                )
                self.model.Add(diff_var == work_var - self.avg_work_var)
                self.model.AddAbsEquality(imbalance_var, diff_var)
                constraints_added += 2

        self.penalty_terms.extend(
            (self.penalty_weight, var) for var in self.load_imbalance_vars.values()
        )
        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} invigilator load balance constraints."
        )
