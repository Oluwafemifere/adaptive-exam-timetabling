"""
InvigilatorLoadBalanceConstraint - S4 Implementation

S4: Invigilator load imbalance (enhanced)

Let work_i = ∑_{e,r,s} u_{i,e,r,s}. Define avgWork = (∑_i work_i) / |I|.
For each i: loadImbalance_i ≥ |work_i - avgWork|
Penalty: W_load × ∑_i loadImbalance_i where W_load = 300.
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


class InvigilatorLoadBalanceConstraint(CPSATBaseConstraint):
    """S4: Invigilator load imbalance penalty for uneven workload distribution"""

    dependencies = ["InvigilatorSingleAssignmentConstraint"]
    constraint_category = "SOFT_CONSTRAINTS"
    is_critical = False
    min_expected_constraints = 0  # May be 0 if no invigilators

    def __init__(self, constraint_id, problem, shared_vars, model, factory=None):
        super().__init__(constraint_id, problem, shared_vars, model, factory)
        self.penalty_weight = 300  # W_load
        logger.info(
            f"🟡 Initializing SOFT constraint {constraint_id} with weight {self.penalty_weight}"
        )

    def _create_local_variables(self):
        """Create auxiliary variables for load balance"""
        self.work_vars = {}
        self.load_imbalance_vars = {}
        self.avg_work_var = None

        # Check if we have invigilators and u variables
        if not hasattr(self.problem, "invigilators") or not self.problem.invigilators:
            return

        if not self.u:
            return

        invigilators = self.problem.invigilators
        total_invigilators = len(invigilators)

        # Estimate maximum possible work per invigilator
        max_possible_work = len(self._exams) * len(self._timeslots)

        # Create work variables for each invigilator
        for invigilator_id in invigilators:
            self.work_vars[invigilator_id] = self.model.NewIntVar(
                0, max_possible_work, f"work_{invigilator_id}"
            )

            self.load_imbalance_vars[invigilator_id] = self.model.NewIntVar(
                0, max_possible_work, f"loadImbalance_{invigilator_id}"
            )

        # Create average work variable
        if total_invigilators > 0:
            self.avg_work_var = self.model.NewIntVar(0, max_possible_work, "avgWork")

    def _add_constraint_implementation(self):
        """Add invigilator load balance constraints"""
        constraints_added = 0

        if not hasattr(self.problem, "invigilators") or not self.problem.invigilators:
            logger.info(f"{self.constraint_id}: No invigilators found")
            self.constraint_count = 0
            return

        if not self.u:
            logger.info(
                f"{self.constraint_id}: No invigilator assignment variables found"
            )
            self.constraint_count = 0
            return

        if not self.work_vars:
            logger.info(f"{self.constraint_id}: No work variables created")
            self.constraint_count = 0
            return

        invigilators = self.problem.invigilators
        total_invigilators = len(invigilators)

        # Calculate work for each invigilator: work_i = ∑_{e,r,s} u_{i,e,r,s}
        for invigilator_id in invigilators:
            if invigilator_id not in self.work_vars:
                continue

            work_var = self.work_vars[invigilator_id]

            # Sum all u variables for this invigilator
            work_terms = []
            for u_key, u_var in self.u.items():
                if len(u_key) == 4 and u_key[0] == invigilator_id:
                    # u_key = (invigilator_id, exam_id, room_id, slot_id)
                    work_terms.append(u_var)

            if work_terms:
                self.model.Add(work_var == sum(work_terms))
                constraints_added += 1

        # Calculate average work: avgWork = (∑_i work_i) / |I|
        if self.avg_work_var is not None and total_invigilators > 0:
            total_work_terms = list(self.work_vars.values())
            if total_work_terms:
                # avgWork * |I| = ∑_i work_i
                self.model.Add(
                    self.avg_work_var * total_invigilators == sum(total_work_terms)
                )
                constraints_added += 1

        # Calculate load imbalance: loadImbalance_i ≥ |work_i - avgWork|
        if self.avg_work_var is not None:
            for invigilator_id in invigilators:
                if (
                    invigilator_id not in self.work_vars
                    or invigilator_id not in self.load_imbalance_vars
                ):
                    continue

                work_var = self.work_vars[invigilator_id]
                imbalance_var = self.load_imbalance_vars[invigilator_id]

                # |work_i - avgWork| implementation using two constraints:
                # loadImbalance_i ≥ work_i - avgWork
                # loadImbalance_i ≥ avgWork - work_i
                self.model.Add(imbalance_var >= work_var - self.avg_work_var)
                self.model.Add(imbalance_var >= self.avg_work_var - work_var)
                constraints_added += 2

        # Store penalty terms for objective function
        self.penalty_terms = []
        for invigilator_id, imbalance_var in self.load_imbalance_vars.items():
            self.penalty_terms.append((self.penalty_weight, imbalance_var))

        self.constraint_count = constraints_added

        if constraints_added == 0:
            logger.info(f"{self.constraint_id}: No load balance constraints needed")
        else:
            logger.info(
                f"{self.constraint_id}: Added {constraints_added} invigilator load balance constraints"
            )

    def get_penalty_terms(self):
        """Get penalty terms for the objective function"""
        return getattr(self, "penalty_terms", [])

    def get_statistics(self):
        """Get constraint statistics"""
        stats = super().get_constraint_statistics()
        invigilator_count = len(self.work_vars) if hasattr(self, "work_vars") else 0
        stats.update(
            {
                "penalty_weight": self.penalty_weight,
                "invigilators": invigilator_count,
                "work_variables": (
                    len(self.work_vars) if hasattr(self, "work_vars") else 0
                ),
                "imbalance_variables": (
                    len(self.load_imbalance_vars)
                    if hasattr(self, "load_imbalance_vars")
                    else 0
                ),
                "penalty_terms": len(getattr(self, "penalty_terms", [])),
            }
        )
        return stats
