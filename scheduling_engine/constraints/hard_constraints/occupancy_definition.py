# scheduling_engine/constraints/hard_constraints/occupancy_definition.py

"""
FIXED OccupancyDefinitionConstraint - H2 Implementation with StartCovers Logic

H2: Occupancy linking (start → occupied slots)
z[e,s] = ∑_{s0 ∈ StartCovers(e,s)} x[e,s0] ∀ e ∈ E, s ∈ S

This fixes the original implementation to properly handle multi-slot exams
using the StartCovers logic from the mathematical formulation.
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging
import math

logger = logging.getLogger(__name__)


class OccupancyDefinitionConstraint(CPSATBaseConstraint):
    """H2: Occupancy definition with proper StartCovers logic"""

    dependencies = ["StartUniquenessConstraint"]
    constraint_category = "CORE"
    is_critical = True
    min_expected_constraints = 1

    def _create_local_variables(self):
        """No local variables needed for this constraint"""
        pass

    def _add_constraint_implementation(self):
        """Add occupancy definition constraints with StartCovers logic"""
        constraints_added = 0

        # Precompute mappings for faster lookup
        z_keys = set(self.z.keys())
        x_keys = set(self.x.keys())

        # For each (exam, slot) combination in z variables
        for exam_id, slot_id in z_keys:
            z_var = self.z[(exam_id, slot_id)]

            # Find all start slots that would cause this exam to occupy this slot
            # StartCovers(e,s) = { s0 ∈ allowedStartSlots(e) : s0 ≤ s ≤ s0 + dur_e − 1 }
            start_covers = self._get_start_covers(exam_id, slot_id)

            start_vars = []
            for start_slot_id in start_covers:
                x_key = (exam_id, start_slot_id)
                if x_key in self.x:
                    start_vars.append(self.x[x_key])

            # Add constraint: z[e,s] = ∑_{s0 ∈ StartCovers(e,s)} x[e,s0]
            if start_vars:
                self.model.Add(z_var == sum(start_vars))
            else:
                self.model.Add(z_var == 0)

            constraints_added += 1

        self.constraint_count = constraints_added

        logger.info(
            f"{self.constraint_id}: Added {constraints_added} occupancy definition constraints with StartCovers"
        )

        # Validation
        if constraints_added == 0:
            logger.error(f"CRITICAL: {self.constraint_id} generated 0 constraints!")
            raise RuntimeError(
                f"{self.constraint_id}: No z variables available for occupancy definition"
            )

    def _get_start_covers(self, exam_id, target_slot_id):
        """Get all start slots that would cause exam to occupy target slot"""
        exam = self.problem.exams.get(exam_id)
        if not exam:
            return []

        # Calculate exam duration in slots
        duration_minutes = getattr(exam, "duration_minutes", 180)
        duration_slots = math.ceil(duration_minutes / 180.0)

        start_covers = []

        # Get the day containing the target slot
        target_day = self.problem.get_day_for_timeslot(target_slot_id)
        if not target_day:
            return start_covers

        # Find target slot position within its day
        target_slot_idx = None
        for idx, timeslot in enumerate(target_day.timeslots):
            if timeslot.id == target_slot_id:
                target_slot_idx = idx
                break

        if target_slot_idx is None:
            return start_covers

        # Check each possible start slot in the same day
        for start_idx in range(len(target_day.timeslots)):
            start_slot_id = target_day.timeslots[start_idx].id

            # Check if starting at start_slot_id would occupy target_slot_id
            # s0 ≤ s ≤ s0 + dur_e − 1
            if start_idx <= target_slot_idx <= start_idx + duration_slots - 1:
                # Also verify this is a valid start (exam fits within day)
                if start_idx + duration_slots <= len(target_day.timeslots):
                    start_covers.append(start_slot_id)

        return start_covers
