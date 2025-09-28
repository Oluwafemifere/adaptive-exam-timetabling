# scheduling_engine/constraints/hard_constraints/room_capacity_hard.py

"""
FIXED RoomCapacityHardConstraint - H8 Implementation

H8: Room capacity physical hard rule (non-overbookable rooms)
∑ enrol_e * y[e,r,s] ≤ cap_r ∀ r with overbookable_r = 0, s ∈ S

This fixes the original implementation to:
1. Only apply to non-overbookable rooms
2. Remove artificial buffering
3. Use exact capacity limits as specified
4. Enforce capacity solely based on expected students
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class RoomCapacityHardConstraint(CPSATBaseConstraint):
    """H8: Room capacity hard constraint for non-overbookable rooms only"""

    dependencies = ["RoomAssignmentConsistencyConstraint"]
    constraint_category = "RESOURCE_CONSTRAINTS"
    is_critical = False
    min_expected_constraints = 0

    def _create_local_variables(self):
        """No local variables needed"""
        pass

    def _add_constraint_implementation(self):
        """Add room capacity constraints for non-overbookable rooms only"""
        constraints_added = 0

        for room_id, room in self._rooms.items():
            # H8: Only apply to non-overbookable rooms (overbookable_r = 0)
            is_overbookable = getattr(room, "overbookable", False)
            if is_overbookable:
                continue  # Skip overbookable rooms per H8 specification

            capacity = getattr(room, "exam_capacity", getattr(room, "capacity", 0))
            if capacity <= 0:
                continue

            # Add constraint for each slot
            for slot_id in self._timeslots:
                capacity_terms = []
                for exam_id in self._exams:
                    # Check if this exam-room-slot combination exists
                    y_key = (exam_id, room_id, slot_id)
                    if y_key in self.y:
                        exam = self._exams[exam_id]
                        enrollment = self._get_expected_students(exam)
                        if enrollment > 0:
                            capacity_terms.append(enrollment * self.y[y_key])

                if capacity_terms:
                    # H8: ∑ enrol_e * y[e,r,s] ≤ cap_r (exact capacity, no buffering)
                    self.model.Add(sum(capacity_terms) <= capacity)
                    constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(f"Added {constraints_added} hard capacity constraints")

    def _get_expected_students(self, exam):
        """Get expected students for the exam, fallback to 0 if not available"""
        return getattr(
            exam, "expected_students", 0
        )  # Use 0 if expected_students is missing
