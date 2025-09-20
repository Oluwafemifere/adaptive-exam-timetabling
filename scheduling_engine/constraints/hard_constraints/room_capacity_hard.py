# scheduling_engine/constraints/hard_constraints/room_capacity_hard.py

"""
FIXED RoomCapacityHardConstraint - H8 Implementation

H8: Room capacity physical hard rule (non-overbookable rooms)
∑ enrol_e * y[e,r,s] ≤ cap_r ∀ r with overbookable_r = 0, s ∈ S

This fixes the original implementation to:
1. Only apply to non-overbookable rooms
2. Remove artificial buffering
3. Use exact capacity limits as specified
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class RoomCapacityHardConstraint(CPSATBaseConstraint):
    """H8: Room capacity hard constraint for non-overbookable rooms only"""

    dependencies = ["RoomAssignmentConsistencyConstraint"]
    constraint_category = "ROOM_CAPACITY"
    is_critical = False
    min_expected_constraints = 0

    def _create_local_variables(self):
        """No local variables needed"""
        pass

    def _add_constraint_implementation(self):
        """Add room capacity constraints for non-overbookable rooms only"""
        constraints_added = 0

        rooms = self.problem.rooms
        timeslots = self.problem.timeslots
        exams = self.problem.exams

        # Group y variables by (room_id, slot_id)
        room_slot_assignments = defaultdict(list)
        for (exam_id, room_id, slot_id), var in self.y.items():
            room_slot_assignments[(room_id, slot_id)].append((exam_id, var))

        # Track rooms for reporting
        total_rooms = len(rooms)
        non_overbookable_rooms = 0
        capacity_constrained_rooms = 0

        for room_id, room in rooms.items():
            # H8: Only apply to non-overbookable rooms (overbookable_r = 0)
            is_overbookable = getattr(room, "overbookable", False)
            if is_overbookable:
                continue  # Skip overbookable rooms per H8 specification

            non_overbookable_rooms += 1
            capacity = getattr(room, "exam_capacity", getattr(room, "capacity", 0))

            if capacity <= 0:
                continue

            capacity_constrained_rooms += 1

            # Add constraint for each slot
            for slot_id in timeslots:
                key = (room_id, slot_id)
                if key not in room_slot_assignments:
                    continue

                capacity_terms = []
                for exam_id, var in room_slot_assignments[key]:
                    enrollment = self._get_safe_enrollment(exams[exam_id])
                    if enrollment > 0:
                        capacity_terms.append(enrollment * var)

                if capacity_terms:
                    # H8: ∑ enrol_e * y[e,r,s] ≤ cap_r (exact capacity, no buffering)
                    self.model.Add(sum(capacity_terms) <= capacity)
                    constraints_added += 1

        self.constraint_count = constraints_added

        # Enhanced reporting
        logger.info(
            f"✅ {self.constraint_id}: Added {constraints_added} hard capacity constraints"
        )
        logger.info(
            f" • Total rooms: {total_rooms}, Non-overbookable: {non_overbookable_rooms}, "
            f"Capacity-constrained: {capacity_constrained_rooms}"
        )

        if constraints_added == 0:
            if non_overbookable_rooms == 0:
                logger.info(
                    f"{self.constraint_id}: No constraints needed (all rooms are overbookable)"
                )
            else:
                logger.warning(
                    f"⚠️ {self.constraint_id}: No capacity constraints created despite non-overbookable rooms"
                )

    def _get_safe_enrollment(self, exam):
        """Get enrollment with fallbacks and safety checks"""
        enrollment_attrs = [
            "actual_enrollment",
            "enrollment",
            "expected_students",
            "student_count",
        ]

        for attr in enrollment_attrs:
            if hasattr(exam, attr):
                value = getattr(exam, attr)
                if isinstance(value, int) and value > 0:
                    return value

        return 30  # Conservative default
