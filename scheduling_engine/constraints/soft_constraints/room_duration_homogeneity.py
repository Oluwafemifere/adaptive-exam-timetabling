# scheduling_engine/constraints/soft_constraints/room_duration_homogeneity.py
"""
RoomDurationHomogeneityConstraint - Soft Constraint

This constraint penalizes using the same room on the same day for exams of
different durations. It encourages grouping exams of similar lengths together
to improve logistical consistency.

**This constraint is only enforced when slot_generation_mode is 'flexible'.**
"""

from collections import defaultdict
from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
from scheduling_engine.core.constraint_types import ConstraintDefinition
import logging

logger = logging.getLogger(__name__)


class RoomDurationHomogeneityConstraint(CPSATBaseConstraint):
    """Penalize scheduling exams of different durations in the same room on the same day."""

    dependencies = []

    def __init__(self, definition: ConstraintDefinition, problem, shared_vars, model):
        super().__init__(definition, problem, shared_vars, model)
        self.penalty_weight = self.definition.weight
        logger.info(
            f"🟡 Initializing SOFT constraint {self.constraint_id} with weight {self.penalty_weight}"
        )

    def initialize_variables(self):
        """Create penalty variables for each room-day combination."""
        if self.problem.slot_generation_mode != "flexible":
            return
        self.penalty_vars = {}
        for room_id in self.problem.rooms:
            for day_id in self.problem.days:
                key = (room_id, day_id)
                max_penalty = len(self.problem.exams)
                self.penalty_vars[key] = self.model.NewIntVar(
                    0, max_penalty, f"duration_homogeneity_penalty_{room_id}_{day_id}"
                )

    def add_constraints(self):
        """Add constraints to penalize duration heterogeneity."""
        if self.problem.slot_generation_mode != "flexible":
            logger.info(
                f"{self.constraint_id}: Skipping as slot_generation_mode is not 'flexible'."
            )
            self.constraint_count = 0
            return

        constraints_added = 0

        exams_by_duration = defaultdict(list)
        for exam_id in self.problem.exams:
            duration_slots = self.problem.get_exam_duration_in_slots(exam_id)
            exams_by_duration[duration_slots].append(exam_id)

        distinct_durations = list(exams_by_duration.keys())

        for room_id in self.problem.rooms:
            for day_id, day in self.problem.days.items():
                day_slot_ids = {ts.id for ts in day.timeslots}
                duration_present_vars = []

                for duration in distinct_durations:
                    is_present_var = self.model.NewBoolVar(
                        f"duration_{duration}_present_{room_id}_{day_id}"
                    )
                    duration_present_vars.append(is_present_var)

                    relevant_y_vars = []
                    for exam_id in exams_by_duration[duration]:
                        for slot_id in day_slot_ids:
                            y_key = (exam_id, room_id, slot_id)
                            if y_key in self.y:
                                relevant_y_vars.append(self.y[y_key])

                    if not relevant_y_vars:
                        self.model.Add(is_present_var == 0)
                        continue

                    self.model.AddBoolOr(relevant_y_vars).OnlyEnforceIf(is_present_var)
                    self.model.Add(sum(relevant_y_vars) == 0).OnlyEnforceIf(
                        is_present_var.Not()
                    )
                    constraints_added += 2

                penalty_key = (room_id, day_id)
                self.model.Add(
                    self.penalty_vars[penalty_key] >= sum(duration_present_vars) - 1
                )
                constraints_added += 1

        self.penalty_terms.extend(
            (self.penalty_weight, var) for var in self.penalty_vars.values()
        )
        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} room duration homogeneity constraints."
        )
