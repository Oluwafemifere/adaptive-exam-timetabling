# scheduling_engine/constraints/hard_constraints/minimum_gap_between_exams.py
from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


class MinimumGapBetweenExamsConstraint(CPSATBaseConstraint):
    """
    STUDENT_CONFLICT_MODULE - C8: Minimum Gap Between Exams
    Uses optional intervals per (exam, day) guarded by presence p[e,d] = OR_t z[e,d,t].
    """

    dependencies = ["NoStudentTemporalOverlapConstraint"]
    constraint_category = "STUDENT_CONFLICT"

    def _create_local_variables(self):
        """Create presence-gated optional intervals and link start to chosen x only when active."""
        if not self.conflict_pairs:
            logger.info(
                f"{self.constraint_id}: No conflict pairs - skipping gap constraints"
            )
            return

        self._min_gap_slots = getattr(self.problem, "min_gap_slots", 1)
        self._intervals = {}
        self._presence = {}

        # Use only active time slots for domains
        active_slot_ids = [
            slot_id
            for slot_id, ts in self.problem.time_slots.items()
            if getattr(ts, "is_active", True)
        ]
        if not active_slot_ids:
            logger.info(f"{self.constraint_id}: No active time slots - skipping")
            return

        # Limit to exams that actually appear in any conflict pair
        conflict_exam_ids = set()
        for exam1_str, exam2_str in self.conflict_pairs:
            conflict_exam_ids.update([exam1_str, exam2_str])

        for exam_str in conflict_exam_ids:
            # Recover UUID for exam
            exam_id = next(
                (e.id for e in self.problem.exams.values() if str(e.id) == exam_str),
                None,
            )
            if not exam_id:
                continue

            exam = self.problem.exams[exam_id]
            duration_minutes = getattr(exam, "duration_minutes", 180)
            duration_slots = max(1, duration_minutes // 60)
            interval_duration = duration_slots + self._min_gap_slots

            for day in self.problem.days:
                # p[e,d] = OR_t z[e,d,t], bound with AddMaxEquality over BoolVars
                z_vars = []
                for slot_id in active_slot_ids:
                    z_key = (exam_id, day, slot_id)
                    if z_key in self.z:
                        z_vars.append(self.z[z_key])
                if not z_vars:
                    continue

                presence = self.model.NewBoolVar(
                    f"{self.constraint_id}_present_{exam_str}_{day}"
                )
                self.model.AddMaxEquality(presence, z_vars)

                # Start index domain over active slots; end domain accounts for interval_duration
                start_var = self.model.NewIntVar(
                    1,
                    len(active_slot_ids),
                    f"{self.constraint_id}_start_{exam_str}_{day}",
                )
                end_var = self.model.NewIntVar(
                    1,
                    len(active_slot_ids) + interval_duration,
                    f"{self.constraint_id}_end_{exam_str}_{day}",
                )

                # Optional interval guarded by presence p[e,d]
                interval = self.model.NewOptionalIntervalVar(
                    start_var,
                    interval_duration,
                    end_var,
                    presence,
                    f"{self.constraint_id}_interval_{exam_str}_{day}",
                )
                self._presence[(exam_str, day)] = presence
                self._intervals[(exam_str, day)] = interval
                self._local_vars[f"start_{exam_str}_{day}"] = start_var
                self._local_vars[f"end_{exam_str}_{day}"] = end_var
                self._local_vars[f"interval_{exam_str}_{day}"] = interval

                # Link start to chosen start slot only when x[e,d,t] is true
                for slot_idx, slot_id in enumerate(active_slot_ids):
                    x_key = (exam_id, day, slot_id)
                    if x_key in self.x:
                        self.model.Add(start_var == slot_idx + 1).OnlyEnforceIf(
                            self.x[x_key]
                        )

        logger.info(
            f"{self.constraint_id}: Created {len(self._intervals)} optional intervals"
        )

    def _add_constraint_implementation(self):
        """Apply NoOverlap per day; only present intervals (p[e,d]=1) are enforced to be disjoint."""
        if not getattr(self, "_intervals", None):
            logger.info(f"{self.constraint_id}: No intervals - skipping")
            return

        for day in self.problem.days:
            day_intervals = [
                interval
                for (exam_str, d), interval in self._intervals.items()
                if d == day
            ]
            if len(day_intervals) > 1:
                self.model.AddNoOverlap(day_intervals)
                self._increment_constraint_count()
                logger.debug(
                    f"{self.constraint_id}: Added NoOverlap for day {day} with {len(day_intervals)} intervals"
                )
