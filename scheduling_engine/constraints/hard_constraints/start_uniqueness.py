# scheduling_engine/constraints/hard_constraints/start_uniqueness.py

"""
C1: Start Uniqueness Constraint - Mathematically Accurate Implementation

∀e ∈ E: ExactlyOne({x[e,d,t] : d ∈ D, t ∈ T})

Ensures each exam starts exactly once across all days and time slots.
Uses native CP-SAT ExactlyOne constraint for optimal performance.
"""

from scheduling_engine.constraints.base_constraint import (
    CPSATBaseConstraint,
)
import logging

logger = logging.getLogger(__name__)


class StartUniquenessConstraint(CPSATBaseConstraint):
    """
    CORE_MODULE - C1: Start Uniqueness

    Mathematical formulation: ∀e ∈ E: ExactlyOne({x[e,d,t] : d ∈ D, t ∈ T})
    """

    dependencies = []  # No dependencies - this is foundational
    constraint_category = "CORE"

    def _create_local_variables(self):
        """No local variables needed - uses only shared x variables."""
        logger.debug(f"{self.constraint_id}: No local variables needed")

    def _add_constraint_implementation(self):
        """Add ExactlyOne constraints for each exam's start time."""
        if not self.x:
            raise RuntimeError(f"{self.constraint_id}: No x variables available")

        for exam in self.problem.exams.values():
            exam_id = exam.id

            # Collect all start variables for this exam: {x[e,d,t] : d ∈ D, t ∈ T}
            start_vars = []
            for day in self.problem.days:
                for slot_id in self.problem.time_slots:
                    ts = self.problem.time_slots.get(slot_id)
                    if ts is not None and hasattr(ts, "is_active") and not ts.is_active:
                        continue
                    key = (exam_id, day, slot_id)
                    if key in self.x:
                        start_vars.append(self.x[key])

            if start_vars:
                # ∀e ∈ E: ExactlyOne({x[e,d,t] : d ∈ D, t ∈ T})
                self.model.AddExactlyOne(start_vars)
                self._increment_constraint_count()

                logger.debug(
                    f"{self.constraint_id}: Added ExactlyOne for exam {exam_id} "
                    f"({len(start_vars)} variables)"
                )
            else:
                logger.warning(
                    f"{self.constraint_id}: No start variables for exam {exam_id}"
                )
