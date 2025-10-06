# scheduling_engine/constraints/hard_constraints/room_sequential_use.py
"""
CORRECTED RoomSequentialUseConstraint - Hard Constraint

This constraint ensures that for any given room and timeslot, at most one
exam can be occupying it. It prevents overlaps and is essential for the
'flexible' slot generation mode.
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


class RoomSequentialUseConstraint(CPSATBaseConstraint):
    """Ensures that at most one exam occupies any room in any single timeslot."""

    dependencies = ["RoomAssignmentConsistencyConstraint"]

    def initialize_variables(self):
        """No local variables needed."""
        pass

    def add_constraints(self):
        """
        For each room and timeslot, ensure that the total number of exams
        assigned to it is at most one.
        """
        if self.problem.slot_generation_mode != "flexible":
            logger.info(
                f"{self.constraint_id}: Skipping as slot_generation_mode is not 'flexible'."
            )
            self.constraint_count = 0
            return

        constraints_added = 0

        # For each specific room at a specific timeslot...
        for room_id in self.problem.rooms:
            for slot_id in self.problem.timeslots:

                # ...collect all the y_vars that represent an exam being assigned there.
                # The y[e,r,s] variable is 1 if exam 'e' is in room 'r' at slot 's'.
                exams_in_this_room_at_this_time = []
                for exam_id in self.problem.exams:
                    y_key = (exam_id, room_id, slot_id)
                    if y_key in self.y:
                        exams_in_this_room_at_this_time.append(self.y[y_key])

                # The sum of these boolean variables represents the number of exams in
                # the room at this time. This sum cannot be greater than 1.
                if exams_in_this_room_at_this_time:
                    self.model.Add(sum(exams_in_this_room_at_this_time) <= 1)
                    constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} sequential room use constraints."
        )

    def _get_start_covers(self, exam_id, target_slot_id):
        """
        Helper to find all start slots on the same day as target_slot_id
        that would cause the exam to occupy target_slot_id.

        NOTE: This function is no longer used by the corrected add_constraints method
        but is kept for potential debugging or reference.
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
