# scheduling_engine/constraints/hard_constraints/room_sequential_use.py

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging
from collections import defaultdict
from backend.app.utils.celery_task_utils import task_progress_tracker

logger = logging.getLogger(__name__)


class RoomSequentialUseConstraint(CPSATBaseConstraint):
    """
    Ensures that exam schedules do not temporally overlap within the same room.
    This constraint is now active in all modes during Phase 2.
    """

    dependencies = ["RoomAssignmentConsistencyConstraint"]

    def initialize_variables(self):
        """No local variables needed; intervals will be created during constraint addition."""
        pass

    @task_progress_tracker(
        start_progress=61,
        end_progress=63,
        phase="building_phase_2_model",
        message="Applying room sequential use (no overlap)...",
    )
    def add_constraints(self):
        """
        For each room, create a set of optional time intervals corresponding to
        exam start times and add a 'NoOverlap' constraint to prevent collisions.
        """

        phase1_results = self.precomputed_data.get("phase1_results")
        if not phase1_results:
            logger.info(
                f"{self.constraint_id}: Skipping as this is a Phase 2 constraint and Phase 1 results are not available."
            )
            self.constraint_count = 0
            return

        constraints_added = 0

        # --- Step 1: Group exams by their fixed start slot from Phase 1 ---
        exams_by_start_slot = defaultdict(list)
        for exam_id, (start_slot_id, _) in phase1_results.items():
            exams_by_start_slot[start_slot_id].append(exam_id)

        # --- Step 2: For each start time, find the maximum duration ---
        # This determines how long a room will be occupied if this group is placed there.
        max_duration_by_start_slot = {}
        for start_slot_id, exam_ids in exams_by_start_slot.items():
            max_duration = 0
            for exam_id in exam_ids:
                duration_in_slots = self.problem.get_exam_duration_in_slots(exam_id)
                if duration_in_slots > max_duration:
                    max_duration = duration_in_slots
            max_duration_by_start_slot[start_slot_id] = max_duration

        # --- Step 3: Create NoOverlap constraints for each room ---
        for room_id in self.problem.rooms:
            intervals_for_this_room = []

            # We must operate on a consistent, ordered list of slots for a day
            for day in self.problem.days.values():
                day_slots = sorted(day.timeslots, key=lambda ts: ts.start_time)
                day_slot_ids_ordered = [ts.id for ts in day_slots]

                # For each potential start time on this day...
                for i, start_slot_id in enumerate(day_slot_ids_ordered):
                    if start_slot_id not in exams_by_start_slot:
                        continue

                    # The boolean variable that determines if this interval "exists".
                    # It exists if *any* exam from this start-time group is placed in this room.
                    is_group_in_room_var = self.model.NewBoolVar(
                        f"group_at_{start_slot_id}_in_room_{room_id}"
                    )

                    # Collect the y_vars for all exams in this start group for this specific room.
                    relevant_y_vars = []
                    for exam_id in exams_by_start_slot[start_slot_id]:
                        y_key = (exam_id, room_id, start_slot_id)
                        if y_key in self.y:
                            relevant_y_vars.append(self.y[y_key])

                    if not relevant_y_vars:
                        continue  # No possibility of this group being in this room.

                    # Link the boolean to the y_vars: is_group_in_room_var is TRUE if OR(y_vars) is TRUE.
                    self.model.AddBoolOr(relevant_y_vars).OnlyEnforceIf(
                        is_group_in_room_var
                    )
                    self.model.Add(sum(relevant_y_vars) == 0).OnlyEnforceIf(
                        is_group_in_room_var.Not()
                    )

                    # Define the interval's properties.
                    start_index = i
                    duration = max_duration_by_start_slot[start_slot_id]
                    end_index = start_index + duration

                    # Create the optional interval.
                    interval = self.model.NewOptionalIntervalVar(
                        start=start_index,
                        size=duration,
                        end=end_index,
                        is_present=is_group_in_room_var,
                        name=f"interval_room_{room_id}_slot_{start_slot_id}",
                    )
                    intervals_for_this_room.append(interval)

            # --- Step 4: Add the NoOverlap constraint for the room ---
            if len(intervals_for_this_room) > 1:
                self.model.AddNoOverlap(intervals_for_this_room)
                constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} 'NoOverlap' constraints for room usage."
        )
