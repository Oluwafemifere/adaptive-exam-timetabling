# scheduling_engine/constraints/hard_constraints/start_uniqueness.py
"""
FIXED StartUniquenessConstraint - Foundation Core Constraint

Ensures that every exam is scheduled to start exactly one time.
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class StartUniquenessConstraint(CPSATBaseConstraint):
    """H1: Each exam starts exactly once - ∑ x[e,s] = 1 ∀ e ∈ E"""

    dependencies = []

    def initialize_variables(self):
        """No local variables needed for this constraint."""
        pass

    def add_constraints(self):
        """Add start uniqueness constraints: each exam starts exactly once."""
        constraints_added = 0

        exam_vars = defaultdict(list)
        for (exam_id, slot_id), x_var in self.x.items():
            exam_vars[exam_id].append(x_var)

        for exam_id, vars_list in exam_vars.items():
            self.model.AddExactlyOne(vars_list)
            constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} start uniqueness constraints."
        )

        if len(exam_vars) != len(self.problem.exams):
            logger.warning(
                f"{self.constraint_id}: Mismatch between exams with variables ({len(exam_vars)}) and total exams ({len(self.problem.exams)})."
            )
            if constraints_added == 0:
                raise RuntimeError(
                    f"{self.constraint_id}: Foundation constraint failed to generate any constraints!"
                )
