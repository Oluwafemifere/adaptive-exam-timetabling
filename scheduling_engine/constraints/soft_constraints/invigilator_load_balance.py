from ortools.sat.python import cp_model
from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
from scheduling_engine.core.constraint_types import ConstraintDefinition
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class InvigilatorLoadBalanceConstraint(CPSATBaseConstraint):
    """S4: Invigilator load imbalance penalty for uneven workload distribution."""

    dependencies = []

    def __init__(
        self,
        definition: ConstraintDefinition,
        problem,
        shared_vars,
        model: cp_model.CpModel,
    ):
        super().__init__(definition, problem, shared_vars, model)
        self.penalty_weight = self.definition.weight
        logger.info(
            f"🟡 Initializing SOFT constraint {self.constraint_id} with weight {self.penalty_weight}"
        )

    def initialize_variables(self):
        """Create auxiliary variables for workload balancing."""
        self.work_vars: dict[str, cp_model.IntVar] = {}
        self.max_work_var: cp_model.IntVar | None = None
        self.min_work_var: cp_model.IntVar | None = None
        self.workload_range_var: cp_model.IntVar | None = None

        if not getattr(self.problem, "invigilators", None) or not getattr(
            self, "w", None
        ):
            return

        max_possible_work = len(self.problem.timeslots)

        for inv_id in self.problem.invigilators:
            self.work_vars[inv_id] = self.model.NewIntVar(
                0, max_possible_work, f"work_{inv_id}"
            )

        if self.work_vars:
            self.max_work_var = self.model.NewIntVar(
                0, max_possible_work, "max_invigilator_work"
            )
            self.min_work_var = self.model.NewIntVar(
                0, max_possible_work, "min_invigilator_work"
            )
            self.workload_range_var = self.model.NewIntVar(
                0, max_possible_work, "workload_range"
            )

    async def add_constraints(self):
        """Add constraints to minimize the range of invigilator workloads."""
        if not self.work_vars:
            logger.info(f"{self.constraint_id}: No invigilators found, skipping.")
            self.constraint_count = 0
            return

        if (
            self.max_work_var is None
            or self.min_work_var is None
            or self.workload_range_var is None
        ):
            logger.warning(
                f"{self.constraint_id}: Missing auxiliary variables, skipping constraint."
            )
            self.constraint_count = 0
            return

        constraints_added = 0
        invigilator_assignments = defaultdict(list)

        for (inv_id, room_id, slot_id), w_var in self.w.items():
            invigilator_assignments[inv_id].append(w_var)

        # Compute workload per invigilator
        for inv_id, work_var in self.work_vars.items():
            terms = invigilator_assignments.get(inv_id, [])
            if terms:
                self.model.Add(work_var == sum(terms))
            else:
                self.model.Add(work_var == 0)

            constraints_added += 1

        all_work_vars = list(self.work_vars.values())

        # Safe max/min operations
        self.model.AddMaxEquality(self.max_work_var, all_work_vars)
        self.model.AddMinEquality(self.min_work_var, all_work_vars)
        constraints_added += 2

        # Workload range
        self.model.Add(
            self.workload_range_var == (self.max_work_var - self.min_work_var)
        )
        constraints_added += 1

        self.penalty_terms.append((self.penalty_weight, self.workload_range_var))
        self.constraint_count = constraints_added

        logger.info(
            f"{self.constraint_id}: Added {constraints_added} invigilator load balance constraints."
        )
