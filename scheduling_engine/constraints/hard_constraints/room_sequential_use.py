# scheduling_engine/constraints/hard_constraints/room_sequential_use.py
"""
RoomSequentialUseConstraint - Hard Constraint

This constraint ensures that if any exam is ongoing in a room during a timeslot,
no new exam can start in that same room. It prevents overlaps and enforces
that only one exam "owns" a room at any given time.

**This constraint is only enforced when slot_generation_mode is 'flexible'.**
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


class RoomSequentialUseConstraint(CPSATBaseConstraint):
    """Ensures no new exam starts in a room while another is ongoing."""

    dependencies = ["OccupancyDefinitionConstraint"]

    def initialize_variables(self):
        """No local variables needed."""
        pass

    def add_constraints(self):
        """
        For each room and timeslot, ensure that the total number of exams
        occupying it is at most one.
        """
        if self.problem.slot_generation_mode != "flexible":
            logger.info(
                f"{self.constraint_id}: Skipping as slot_generation_mode is not 'flexible'."
            )
            self.constraint_count = 0
            return

        constraints_added = 0

        for room_id in self.problem.rooms:
            for slot_id in self.problem.timeslots:
                occupancy_terms = []
                for exam_id in self.problem.exams:
                    start_covers = self._get_start_covers(exam_id, slot_id)
                    for start_exam_id, start_slot_id in start_covers:
                        y_key = (start_exam_id, room_id, start_slot_id)
                        if y_key in self.y:
                            occupancy_terms.append(self.y[y_key])

                if occupancy_terms:
                    self.model.Add(sum(occupancy_terms) <= 1)
                    constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} sequential room use constraints."
        )

    def _get_start_covers(self, exam_id, target_slot_id):
        """
        Helper to find all start slots on the same day as target_slot_id
        that would cause the exam to occupy target_slot_id.
        """
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
            if start_idx <= target_slot_idx < start_idx + duration_slots:
                if start_idx + duration_slots <= len(target_day.timeslots):
                    start_covers.append((exam_id, start_slot.id))

        return start_covers
