# scheduling_engine/constraints/hard_constraints/occupancy_definition.py

"""
FIXED C2: Occupancy Definition Constraint - Mathematically Accurate Implementation

∀e ∈ E, d ∈ D, t ∈ T: z[e,d,t] ↔ ⋁{x[e,d,t'] : t' ∈ StartTimes(e,t)}

Links occupancy variables to start variables using bidirectional implications.
StartTimes(e,t) = {t' ∈ T : t' ≤ t ≤ t' + dur_e - 1}
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


class OccupancyDefinitionConstraint(CPSATBaseConstraint):
    """
    CORE_MODULE - C2: Occupancy Definition

    Mathematical formulation: ∀e ∈ E, d ∈ D, t ∈ T: z[e,d,t] ↔ ⋁{x[e,d,t'] : t' ∈ StartTimes(e,t)}
    """

    dependencies = ["StartUniquenessConstraint"]
    constraint_category = "CORE"

    def _create_local_variables(self):
        """Precompute StartTimes(e,t) mappings, restricted to active slots."""
        self._start_times_map = {}

        # Filter time slots to only active ones
        active_slot_ids = [
            slot_id
            for slot_id, ts in self.problem.time_slots.items()
            if getattr(ts, "is_active", True)
        ]

        for exam in self.problem.exams.values():
            exam_id = exam.id
            # Calculate duration in time slots
            duration_minutes = getattr(exam, "duration_minutes", 180)
            duration_slots = max(1, duration_minutes // 60)

            for day in self.problem.days:
                for slot_idx, slot_id in enumerate(active_slot_ids):
                    # StartTimes(e,t) = {t' ∈ T : t' ≤ t ≤ t' + dur_e - 1}
                    valid_starts = []
                    for start_idx, start_slot_id in enumerate(active_slot_ids):
                        if start_idx <= slot_idx <= start_idx + duration_slots - 1:
                            valid_starts.append(start_slot_id)

                    if valid_starts:
                        key = (exam_id, day, slot_id)
                        self._start_times_map[key] = valid_starts

        logger.info(
            f"{self.constraint_id}: Precomputed StartTimes for "
            f"{len(self._start_times_map)} (exam,day,slot) combinations"
        )

    def _add_constraint_implementation(self):
        """Add bidirectional occupancy linking constraints, skipping inactive slots."""
        if not self.x or not self.z:
            raise RuntimeError(f"{self.constraint_id}: Missing x or z variables")

        for (exam_id, day, slot_id), start_slots in self._start_times_map.items():
            # Guard: skip if the target occupancy slot is inactive
            ts = self.problem.time_slots.get(slot_id)
            if ts is not None and hasattr(ts, "is_active") and not ts.is_active:
                continue

            z_key = (exam_id, day, slot_id)
            if z_key not in self.z:
                continue

            z_var = self.z[z_key]

            # Get corresponding start variables, filtered to active start slots
            x_vars = []
            for start_slot_id in start_slots:
                ts_start = self.problem.time_slots.get(start_slot_id)
                if (
                    ts_start is not None
                    and hasattr(ts_start, "is_active")
                    and not ts_start.is_active
                ):
                    continue
                x_key = (exam_id, day, start_slot_id)
                if x_key in self.x:
                    x_vars.append(self.x[x_key])

            if not x_vars:
                continue

            # Forward: z[e,d,t] → ⋁{x[e,d,t']}
            self.model.AddBoolOr(x_vars).OnlyEnforceIf(z_var)
            self._increment_constraint_count()

            # Backward: each start implies occupancy
            for x_var in x_vars:
                self.model.AddImplication(x_var, z_var)
                self._increment_constraint_count()
