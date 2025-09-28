"""
DailyWorkloadBalanceConstraint - S7 Implementation

S7: Daily workload balance (new soft constraint)

For each day d, define balanceViol_d ∈ ℤ_{≥0} measuring deviation
from ideal daily exam distribution:
balanceViol_d ≥ |∑_{e,s:day(s)=d} x_{e,s} - avgExamsPerDay|
Penalty: W_balance × ∑_d balanceViol_d where W_balance = 200.
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging
import math

logger = logging.getLogger(__name__)


class DailyWorkloadBalanceConstraint(CPSATBaseConstraint):
    """S7: Daily workload balance penalty for uneven exam distribution across days"""

    dependencies = ["StartUniquenessConstraint"]
    constraint_category = "SOFT_CONSTRAINTS"
    is_critical = False
    min_expected_constraints = 0  # May be 0 if only one day

    def __init__(self, constraint_id, problem, shared_vars, model, factory=None):
        super().__init__(constraint_id, problem, shared_vars, model, factory)
        self.penalty_weight = 200  # W_balance
        logger.info(
            f"🟡 Initializing SOFT constraint {constraint_id} with weight {self.penalty_weight}"
        )

    def _create_local_variables(self):
        """Create auxiliary variables for daily balance violations"""
        self.balance_viol_vars = {}
        self.daily_exam_count_vars = {}
        self.avg_exams_per_day_var = None

        try:
            day_slot_groupings = self.get_day_slot_groupings()
        except ValueError:
            return

        if not day_slot_groupings:
            return

        total_days = len(day_slot_groupings)
        max_exams_per_day = len(self._exams)

        # Create variables for each day
        for day_key in day_slot_groupings.keys():
            self.daily_exam_count_vars[day_key] = self.model.NewIntVar(
                0, max_exams_per_day, f"dailyExamCount_{day_key}"
            )

            self.balance_viol_vars[day_key] = self.model.NewIntVar(
                0, max_exams_per_day, f"balanceViol_{day_key}"
            )

        # Create average exams per day variable
        if total_days > 0:
            self.avg_exams_per_day_var = self.model.NewIntVar(
                0, max_exams_per_day, "avgExamsPerDay"
            )

    def _add_constraint_implementation(self):
        """Add daily workload balance penalty constraints"""
        constraints_added = 0

        if not self.x:
            logger.info(f"{self.constraint_id}: No exam start variables found")
            self.constraint_count = 0
            return

        try:
            day_slot_groupings = self.get_day_slot_groupings()
        except ValueError as e:
            logger.error(f"{self.constraint_id}: {e}")
            self.constraint_count = 0
            return

        if not day_slot_groupings or not self.daily_exam_count_vars:
            logger.info(
                f"{self.constraint_id}: No day groupings or variables available"
            )
            self.constraint_count = 0
            return

        total_days = len(day_slot_groupings)

        # Calculate daily exam counts: ∑_{e,s:day(s)=d} x_{e,s}
        for day_key, slot_ids in day_slot_groupings.items():
            if day_key not in self.daily_exam_count_vars:
                continue

            daily_count_var = self.daily_exam_count_vars[day_key]

            # Sum all x variables for slots in this day
            daily_exam_terms = []
            for exam_id in self._exams:
                for slot_id in slot_ids:
                    x_key = (exam_id, slot_id)
                    if x_key in self.x:
                        daily_exam_terms.append(self.x[x_key])

            if daily_exam_terms:
                self.model.Add(daily_count_var == sum(daily_exam_terms))
                constraints_added += 1

        # Calculate average exams per day: avgExamsPerDay = (∑_d dailyExamCount_d) / |D|
        if self.avg_exams_per_day_var is not None and total_days > 0:
            daily_count_vars = list(self.daily_exam_count_vars.values())
            if daily_count_vars:
                # avgExamsPerDay * |D| = ∑_d dailyExamCount_d
                self.model.Add(
                    self.avg_exams_per_day_var * total_days == sum(daily_count_vars)
                )
                constraints_added += 1

        # Calculate balance violations: balanceViol_d ≥ |dailyExamCount_d - avgExamsPerDay|
        if self.avg_exams_per_day_var is not None:
            for day_key in day_slot_groupings.keys():
                if (
                    day_key not in self.daily_exam_count_vars
                    or day_key not in self.balance_viol_vars
                ):
                    continue

                daily_count_var = self.daily_exam_count_vars[day_key]
                balance_viol_var = self.balance_viol_vars[day_key]

                # |dailyExamCount_d - avgExamsPerDay| implementation using two constraints:
                # balanceViol_d ≥ dailyExamCount_d - avgExamsPerDay
                # balanceViol_d ≥ avgExamsPerDay - dailyExamCount_d
                self.model.Add(
                    balance_viol_var >= daily_count_var - self.avg_exams_per_day_var
                )
                self.model.Add(
                    balance_viol_var >= self.avg_exams_per_day_var - daily_count_var
                )
                constraints_added += 2

        # Store penalty terms for objective function
        self.penalty_terms = []
        for day_key, balance_viol_var in self.balance_viol_vars.items():
            self.penalty_terms.append((self.penalty_weight, balance_viol_var))

        self.constraint_count = constraints_added

        if constraints_added == 0:
            logger.info(f"{self.constraint_id}: No daily balance constraints needed")
        else:
            logger.info(
                f"{self.constraint_id}: Added {constraints_added} daily workload balance constraints"
            )

    def get_penalty_terms(self):
        """Get penalty terms for the objective function"""
        return getattr(self, "penalty_terms", [])

    def get_statistics(self):
        """Get constraint statistics"""
        stats = super().get_constraint_statistics()
        days_count = (
            len(self.daily_exam_count_vars)
            if hasattr(self, "daily_exam_count_vars")
            else 0
        )
        stats.update(
            {
                "penalty_weight": self.penalty_weight,
                "days": days_count,
                "daily_variables": days_count,
                "balance_variables": (
                    len(self.balance_viol_vars)
                    if hasattr(self, "balance_viol_vars")
                    else 0
                ),
                "penalty_terms": len(getattr(self, "penalty_terms", [])),
            }
        )
        return stats
