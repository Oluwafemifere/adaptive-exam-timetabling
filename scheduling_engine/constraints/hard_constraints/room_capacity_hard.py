# scheduling_engine/constraints/hard_constraints/room_capacity_hard.py
"""
REVISED & ROBUST Room Capacity Constraints for Two-Phase Decomposition.

- RoomCapacityHardConstraint (Phase 2): Correctly enforces that an exam fits into its assigned rooms. The logic is now phase-aware and explicitly forbids assigning an exam to a single room that is too small.

- AggregateCapacityConstraint (Phase 1): Re-implemented with stronger, more realistic heuristics. It now checks not only total student numbers but also the total number of exams against the total number of available rooms.
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


class RoomCapacityHardConstraint(CPSATBaseConstraint):
    """
    H8: Enforces two critical capacity conditions in Phase 2:
    1. An exam CANNOT be placed in a single room that is smaller than its student count.
    2. The combined capacity of all rooms assigned to an exam must be sufficient for its total student count.
    """

    dependencies = ["RoomAssignmentConsistencyConstraint"]

    def initialize_variables(self):
        """No local variables needed."""
        pass

    def add_constraints(self):
        """
        Adds robust, "sure-fire" capacity constraints for the Phase 2 subproblem.
        """
        constraints_added = 0
        # Determine the set of exams and the single slot_id from the y_vars present in this subproblem.
        exam_slot_pairs = {(key[0], key[2]) for key in self.y.keys()}

        for exam_id, slot_id in exam_slot_pairs:
            exam = self._exams.get(exam_id)
            if not exam or exam.expected_students <= 0:
                continue

            assigned_capacity_terms = []

            for room in self._rooms.values():
                y_var = self.y.get((exam_id, room.id, slot_id))
                if y_var is None:
                    continue

                # The core logic is to sum the capacity of assigned rooms.
                assigned_capacity_terms.append(room.exam_capacity * y_var)

            # PRIMARY RULE: The sum of capacities for all assigned rooms must be sufficient.
            # If an exam is assigned to a single room, sum(terms) becomes `room_capacity * 1`,
            # correctly enforcing `room_capacity >= student_count`.
            # If an exam is split, it enforces that the combined space is sufficient.
            if assigned_capacity_terms:
                self.model.Add(sum(assigned_capacity_terms) >= exam.expected_students)
                constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} robust room capacity constraints for the subproblem."
        )


class AggregateCapacityConstraint(CPSATBaseConstraint):
    """
    REVISED: Stronger aggregate capacity constraints for the Phase 1 timetabling model.
    """

    dependencies = ["OccupancyDefinitionConstraint"]

    def initialize_variables(self):
        """No local variables needed for this constraint."""
        pass

    def add_constraints(self):
        """
        For each time slot, ensure:
        1. The total number of exams scheduled does not exceed the total number of available rooms.
        2. The total student demand does not exceed the total available room capacity.
        """
        constraints_added = 0
        if not self.z:
            logger.warning(
                f"{self.constraint_id}: No occupancy variables (z_vars), skipping."
            )
            return

        total_room_capacity = sum(
            room.exam_capacity for room in self.problem.rooms.values()
        )
        total_num_rooms = len(self.problem.rooms)

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
            f"{self.constraint_id}: Added {constraints_added} aggregate capacity & room count constraints."
        )
