# scheduling_engine/constraints/hard_constraints/occupancy_definition.py
"""
FIXED OccupancyDefinitionConstraint - H2 Implementation with StartCovers Logic

This fixes the original implementation to properly handle multi-slot exams
using the StartCovers logic from the mathematical formulation.
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging
import math

logger = logging.getLogger(__name__)


class OccupancyDefinitionConstraint(CPSATBaseConstraint):
    """H2: Occupancy definition with proper StartCovers logic."""

    dependencies = ["StartUniquenessConstraint"]

    def initialize_variables(self):
        """No local variables needed for this constraint."""
        pass

    async def add_constraints(self):
        """FIXED: Add occupancy definition constraints with robust equivalence logic."""
        constraints_added = 0

        for (exam_id, slot_id), z_var in self.z.items():
            start_covers = self._get_start_covers(exam_id, slot_id)
            start_vars = [self.x[key] for key in start_covers if key in self.x]

            if start_vars:
                # --- START OF FIX ---
                # This establishes the robust equivalence: z_var <=> OR(start_vars)

                # 1. Forward Implication: OR(start_vars) => z_var
                # This is equivalent to: for each x in start_vars, x => z_var
                for x_var in start_vars:
                    self.model.AddImplication(x_var, z_var)
                    constraints_added += 1

                # 2. Reverse Implication: z_var => OR(start_vars)
                self.model.AddBoolOr(start_vars).OnlyEnforceIf(z_var)
                constraints_added += 1
                # --- END OF FIX ---
            else:
                # If there are no possible start times that cover this slot, z must be false.
                self.model.Add(z_var == 0)
                constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} occupancy definition constraints."
        )

        if constraints_added == 0 and self.z:
            logger.error(f"CRITICAL: {self.constraint_id} generated 0 constraints!")
            raise RuntimeError(
                f"{self.constraint_id}: No z variables available for occupancy definition."
            )

    def _get_start_covers(self, exam_id, target_slot_id):
        """Get all start slots that would cause an exam to occupy a target slot."""
        exam = self.problem.exams.get(exam_id)
        if not exam:
            return []

        duration_slots = self.problem.get_exam_duration_in_slots(exam_id)

        target_day = self.problem.get_day_for_timeslot(target_slot_id)
        if not target_day:
            return []

        try:
            target_slot_idx = [ts.id for ts in target_day.timeslots].index(
                target_slot_id
            )
        except ValueError:
            return []

        start_covers = []
        for start_idx, start_slot in enumerate(target_day.timeslots):
            # If an exam starts at start_idx and occupies target_slot_idx
            if start_idx <= target_slot_idx < start_idx + duration_slots:
                # And the exam finishes within the day
                if start_idx + duration_slots <= len(target_day.timeslots):
                    start_covers.append((exam_id, start_slot.id))

        return start_covers
