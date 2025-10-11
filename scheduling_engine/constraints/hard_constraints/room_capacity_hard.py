# scheduling_engine/constraints/hard_constraints/room_capacity_hard.py

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging
from collections import defaultdict
from backend.app.utils.celery_task_utils import task_progress_tracker

logger = logging.getLogger(__name__)


class RoomCapacityHardConstraint(CPSATBaseConstraint):
    """
    H8: Enforces that the total number of students from all exams in a room at a given
    time does not exceed the room's capacity.
    """

    dependencies = ["RoomAssignmentConsistencyConstraint"]

    def initialize_variables(self):
        """No local variables needed."""
        pass

    @task_progress_tracker(
        start_progress=56,
        end_progress=58,
        phase="building_phase_2_model",
        message="Applying room capacity limits...",
    )
    async def add_constraints(self):
        """
        Adds robust, aggregate capacity constraints for the Phase 2 packing model.
        """
        constraints_added = 0
        if not self.y:
            logger.info(
                f"{self.constraint_id}: No room assignment variables (y_vars), skipping."
            )
            return

        # Group all exam assignment variables by their (room, slot) pair.
        assignments_by_room_slot = defaultdict(list)
        for (exam_id, room_id, slot_id), y_var in self.y.items():
            exam = self._exams.get(exam_id)
            if exam:
                # Store the variable and the number of students it represents.
                assignments_by_room_slot[(room_id, slot_id)].append(
                    (y_var, exam.expected_students)
                )

        # For each room in each slot, constrain the total seated students.
        for (room_id, slot_id), assignments in assignments_by_room_slot.items():
            room = self._rooms.get(room_id)
            if not room or room.exam_capacity <= 0:
                continue

            # Create a list of terms where each term is (y_var * number_of_students).
            student_load_terms = [y_var * students for y_var, students in assignments]

            # Add the core constraint: The sum of all student loads in this room at this
            # time must not exceed the room's capacity.
            if student_load_terms:
                self.model.Add(sum(student_load_terms) <= room.exam_capacity)
                constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} aggregate room capacity constraints."
        )
