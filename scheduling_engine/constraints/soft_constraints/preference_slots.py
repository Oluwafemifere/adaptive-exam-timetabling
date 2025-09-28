"""
PreferenceSlotsConstraint - S2 Implementation

S2: Preference slots penalty (enhanced)

For each exam e, define prefViol_e ∈ {0,1}:
prefViol_e = 1 iff ∑_{s ∈ prefSlots_e} x_{e,s} = 0
Penalty: W_pref × ∑_e prefViol_e where W_pref = 500.
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


class PreferenceSlotsConstraint(CPSATBaseConstraint):
    """S2: Preference slots penalty for exams not scheduled in preferred time slots"""

    dependencies = []
    constraint_category = "SOFT_CONSTRAINTS"
    is_critical = False
    min_expected_constraints = 0  # May be 0 if no exam preferences

    def __init__(self, constraint_id, problem, shared_vars, model, factory=None):
        super().__init__(constraint_id, problem, shared_vars, model, factory)
        self.penalty_weight = 500  # W_pref
        logger.info(
            f"🟡 Initializing SOFT constraint {constraint_id} with weight {self.penalty_weight}"
        )

    def _create_local_variables(self):
        """Create auxiliary variables for preference violations"""
        self.pref_viol_vars = {}

        # Create preference violation variables for exams with preferences
        for exam_id in self._exams:
            exam = self._exams[exam_id]
            pref_slots = getattr(exam, "preferred_slots", set())

            if pref_slots:
                self.pref_viol_vars[exam_id] = self.model.NewBoolVar(
                    f"prefViol_{exam_id}"
                )

    def _add_constraint_implementation(self):
        """Add preference slots penalty constraints"""
        constraints_added = 0

        if not self.pref_viol_vars:
            logger.info(f"{self.constraint_id}: No exam preferences found")
            self.constraint_count = 0
            return

        # For each exam with preferences
        for exam_id in self._exams:
            exam = self._exams[exam_id]
            pref_slots = getattr(exam, "preferred_slots", set())

            if not pref_slots or exam_id not in self.pref_viol_vars:
                continue

            pref_viol_var = self.pref_viol_vars[exam_id]

            # Collect x variables for preferred slots
            pref_x_vars = []
            for slot_id in pref_slots:
                x_key = (exam_id, slot_id)
                if x_key in self.x:
                    pref_x_vars.append(self.x[x_key])

            if pref_x_vars:
                # prefViol_e = 1 iff ∑_{s ∈ prefSlots_e} x_{e,s} = 0
                # This means: prefViol_e = 1 - max(∑_{s ∈ prefSlots_e} x_{e,s}, 1)
                # Since ∑_{s ∈ prefSlots_e} x_{e,s} is binary (0 or 1), we can use:
                # prefViol_e + ∑_{s ∈ prefSlots_e} x_{e,s} = 1

                self.model.Add(pref_viol_var + sum(pref_x_vars) == 1)
                constraints_added += 1

        # Store penalty weight for objective function
        self.penalty_terms = []
        for exam_id, pref_viol_var in self.pref_viol_vars.items():
            self.penalty_terms.append((self.penalty_weight, pref_viol_var))

        self.constraint_count = constraints_added

        if constraints_added == 0:
            logger.info(f"{self.constraint_id}: No preference constraints needed")
        else:
            logger.info(
                f"{self.constraint_id}: Added {constraints_added} preference penalty constraints"
            )

    def get_penalty_terms(self):
        """Get penalty terms for the objective function"""
        return getattr(self, "penalty_terms", [])

    def get_statistics(self):
        """Get constraint statistics"""
        stats = super().get_constraint_statistics()
        stats.update(
            {
                "penalty_weight": self.penalty_weight,
                "exams_with_preferences": len(self.pref_viol_vars),
                "penalty_terms": len(getattr(self, "penalty_terms", [])),
            }
        )
        return stats
