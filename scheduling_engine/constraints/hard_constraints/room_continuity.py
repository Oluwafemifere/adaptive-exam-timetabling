# scheduling_engine\constraints\hard_constraints\room_continuity.py - Day data class version

"""
Optimized RoomContinuityConstraint - Multi-Slot Exam Room Consistency with Day data class
"""

import math
from scheduling_engine.constraints.base_constraint import (
    CPSATBaseConstraint,
    get_day_for_timeslot,
    get_day_slot_ids,
)
import logging

logger = logging.getLogger(__name__)


class RoomContinuityConstraint(CPSATBaseConstraint):
    """H9: Ensure exam uses same room across all occupied slots."""

    dependencies = ["NoStudentConflictsSameRoomConstraint"]
    constraint_category = "RESOURCE_CONSTRAINTS"
    is_critical = True
    min_expected_constraints = 0

    def _create_local_variables(self):
        pass

    def _add_constraint_implementation(self):
        constraints_added = 0
        y_vars = self.y
        exams = self.problem.exams
        timeslots = self.problem.timeslots

        # Precompute multi-slot exams and their duration
        multi_slot_exams = {
            exam_id: exam
            for exam_id, exam in exams.items()
            if math.ceil(exam.duration_minutes / 180.0) > 1
        }

        # Group y variables by exam and room
        exam_room_vars = {}
        for (e_id, r_id, s_id), var in y_vars.items():
            if e_id in multi_slot_exams:
                exam_room_vars.setdefault(e_id, {}).setdefault(r_id, []).append(var)

        # Add constraints for each exam and room with multiple slots
        for exam_id, rooms in exam_room_vars.items():
            for room_id, vars_list in rooms.items():
                if len(vars_list) > 1:
                    # All variables for this exam-room must be equal
                    base_var = vars_list[0]
                    for other_var in vars_list[1:]:
                        self.model.Add(base_var == other_var)
                    constraints_added += len(vars_list) - 1

        self.constraint_count = constraints_added
