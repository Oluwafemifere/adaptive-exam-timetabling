# scheduling_engine/constraints/soft_constraints/daily_workload_balance.py
"""
DailyWorkloadBalanceConstraint - S7 Implementation (PARAMETERIZED & FIXED)
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
from scheduling_engine.core.constraint_types import ConstraintDefinition
import logging

logger = logging.getLogger(__name__)


class DailyWorkloadBalanceConstraint(CPSATBaseConstraint):
    """S7: Daily workload balance penalty for uneven exam distribution across days"""

    dependencies = ["StartUniquenessConstraint"]

    def __init__(self, definition: ConstraintDefinition, problem, shared_vars, model):
        super().__init__(definition, problem, shared_vars, model)
        self.penalty_weight = self.definition.weight
        logger.info(
            f"🟡 Initializing SOFT constraint {self.constraint_id} with weight {self.penalty_weight}"
        )

    def initialize_variables(self):
        """Create auxiliary variables for daily balance violations"""
        self.balance_viol_vars = {}
        self.daily_exam_count_vars = {}
        self.avg_exams_per_day_var = None

        day_slot_groupings = self.precomputed_data.get("day_slot_groupings", {})
        if not day_slot_groupings:
            logger.warning(f"{self.constraint_id}: Day/slot groupings not found.")
            return

        total_days = len(day_slot_groupings)
        max_exams_per_day = len(self._exams)

        for day_key in day_slot_groupings.keys():
            self.daily_exam_count_vars[day_key] = self.model.NewIntVar(
                0, max_exams_per_day, f"dailyExamCount_{day_key}"
            )
            self.balance_viol_vars[day_key] = self.model.NewIntVar(
                0, max_exams_per_day, f"balanceViol_{day_key}"
            )

        if total_days > 0:
            self.avg_exams_per_day_var = self.model.NewIntVar(
                0, max_exams_per_day, "avgExamsPerDay"
            )

    def add_constraints(self):
        """Add daily workload balance penalty constraints"""
        constraints_added = 0
        if not self.x:
            logger.info(f"{self.constraint_id}: No exam start variables found")
            return

        day_slot_groupings = self.precomputed_data.get("day_slot_groupings", {})
        if not day_slot_groupings or not self.daily_exam_count_vars:
            logger.info(
                f"{self.constraint_id}: No day groupings or variables available"
            )
            return

        total_days = len(day_slot_groupings)

        for day_key, slot_ids in day_slot_groupings.items():
            if day_key in self.daily_exam_count_vars:
                daily_exam_terms = [
                    self.x[key]
                    for exam_id in self._exams
                    for slot_id in slot_ids
                    if (key := (exam_id, slot_id)) in self.x
                ]
                if daily_exam_terms:
                    self.model.Add(
                        self.daily_exam_count_vars[day_key] == sum(daily_exam_terms)
                    )
                    constraints_added += 1

        if self.avg_exams_per_day_var is not None and total_days > 0:
            daily_counts = list(self.daily_exam_count_vars.values())
            if daily_counts:
                self.model.Add(
                    self.avg_exams_per_day_var * total_days == sum(daily_counts)
                )
                constraints_added += 1

        if self.avg_exams_per_day_var is not None:
            for day_key in day_slot_groupings:
                if (
                    day_key in self.daily_exam_count_vars
                    and day_key in self.balance_viol_vars
                ):
                    daily_count_var = self.daily_exam_count_vars[day_key]
                    balance_viol_var = self.balance_viol_vars[day_key]
                    diff_var = self.model.NewIntVar(
                        -len(self._exams), len(self._exams), f"diff_{day_key}"
                    )
                    self.model.Add(
                        diff_var == daily_count_var - self.avg_exams_per_day_var
                    )
                    self.model.AddAbsEquality(balance_viol_var, diff_var)
                    constraints_added += 2

        self.penalty_terms.extend(
            (self.penalty_weight, var) for var in self.balance_viol_vars.values()
        )
        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} daily workload balance constraints"
        )
