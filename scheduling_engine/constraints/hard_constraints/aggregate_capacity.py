# scheduling_engine/constraints/hard_constraints/aggregate_capacity.py
from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging
from backend.app.utils.celery_task_utils import task_progress_tracker

logger = logging.getLogger(__name__)


class AggregateCapacityConstraint(CPSATBaseConstraint):
    """
    REVISED: Stronger aggregate capacity constraints for the Phase 1 timetabling model.
    """

    dependencies = ["OccupancyDefinitionConstraint"]

    def initialize_variables(self):
        """No local variables needed for this constraint."""
        pass

    @task_progress_tracker(
        start_progress=30,
        end_progress=31,
        phase="building_phase_1_model",
        message="Applying aggregate capacity limits...",
    )
    async def add_constraints(self):
        """
        For each time slot, ensure:
        1. The total number of exams scheduled does not exceed the total number of available rooms.
        2. The total student demand does not exceed the total available room capacity.
        """
        constraints_added = 0
        if not self.z:
            logger.info(
                f"{self.constraint_id}: No occupancy variables (z_vars), skipping."
            )
            return

        total_room_capacity = sum(
            room.exam_capacity for room in self.problem.rooms.values()
        )
        total_num_rooms = len(self.problem.rooms)

        if total_num_rooms == 0 or total_room_capacity == 0:
            logger.error(
                f"{self.constraint_id}: No rooms or room capacity available. This will likely cause infeasibility."
            )
            # We don't return, to let the constraint add `sum(...) <= 0` which correctly shows the infeasibility.

        logger.info(
            f"{self.constraint_id}: Applying global limits per slot: Total Capacity={total_room_capacity}, Total Rooms={total_num_rooms}."
        )

        for slot_id in self.problem.timeslots:
            # Get all occupancy variables (z_vars) for the current slot
            occupancy_vars_in_slot = [
                self.z.get((exam_id, slot_id))
                for exam_id in self.problem.exams
                if self.z.get((exam_id, slot_id)) is not None
            ]

            # --- START OF FIX ---
            # **SURE-FIRE CONSTRAINT 1 (Phase 1):**
            # The number of exams active in a slot cannot exceed the number of available rooms.
            if occupancy_vars_in_slot:
                self.model.Add(sum(occupancy_vars_in_slot) <= total_num_rooms)
                constraints_added += 1
            # --- END OF FIX ---

            # **SURE-FIRE CONSTRAINT 2 (Phase 1):**
            # Total student demand in a slot must not exceed total capacity.
            student_demand_in_slot = [
                self.z.get((exam_id, slot_id)) * exam.expected_students
                for exam_id, exam in self.problem.exams.items()
                if self.z.get((exam_id, slot_id)) is not None
            ]
            if student_demand_in_slot:
                self.model.Add(sum(student_demand_in_slot) <= total_room_capacity)
                constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} aggregate capacity & room count constraints across {len(self.problem.timeslots)} slots."
        )
