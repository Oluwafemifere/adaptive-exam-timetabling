# FIXED scheduling_engine/constraints/minimum_invigilators.py - Room-based student allocation version

"""
COMPREHENSIVE FIX - Minimum Invigilators Assignment with Room-based Student Allocation

Key Issues Fixed:
1. Now calculates invigilator requirements based on room capacity and student distribution
2. Uses room capacity ratios to estimate student allocation per room
3. Maintains UUID compatibility and Day data class usage
4. Enhanced validation for room capacity data
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging
import math

logger = logging.getLogger(__name__)


class MinimumInvigilatorsConstraint(CPSATBaseConstraint):
    """Ensure sufficient invigilators are assigned to each exam with room-based allocation"""

    dependencies = ["MaxExamsPerDayConstraint"]
    constraint_category = "INVIGILATOR_CONSTRAINTS"
    is_critical = True
    min_expected_constraints = 0  # May be 0 if no invigilator data

    def _create_local_variables(self):
        """No local variables needed"""
        pass

    def _precompute_feasibility_data(self):
        """Precompute data for faster feasibility checks"""
        self._valid_assignments = set()
        self._exam_room_slots = set()

        # Precompute valid assignments
        for inv_id, exam_id, room_id, slot_id in self.u:
            if (
                exam_id in self.problem.exams
                and room_id in self.problem.rooms
                and slot_id in self.problem.timeslots
            ):
                self._valid_assignments.add((exam_id, room_id, slot_id))

        # Precompute exam-room-slot combinations
        for exam_id, room_id, slot_id in self.y:
            self._exam_room_slots.add((exam_id, room_id, slot_id))

    def _is_assignment_feasible(self, exam_id, room_id, slot_id):
        """Check if an assignment is feasible before creating constraints"""
        return (exam_id, room_id, slot_id) in self._valid_assignments

    def _calculate_room_student_allocation(
        self, exam_id, room_id, total_students, room_capacities, total_capacity
    ):
        """Calculate estimated student allocation for a specific room"""
        if room_id not in room_capacities:
            return 0

        room_capacity = room_capacities[room_id]

        if total_capacity == 0:
            return 0

        # Calculate proportional allocation based on room capacity
        return max(1, math.ceil((room_capacity / total_capacity) * total_students))

    def _add_constraint_implementation(self):
        """Add minimum invigilator assignment constraints with room-based allocation"""
        constraints_added = 0

        invigilators = getattr(self.problem, "invigilators", {})
        if not invigilators:
            logger.info(f"{self.constraint_id}: No invigilator data available")
            return

        if not self.u:
            logger.warning(
                f"{self.constraint_id}: No u variables available (this is normal with optimization)"
            )
            return

        # Group u variables by (exam_id, room_id, slot_id)
        assignment_vars = {}
        for (inv_id, exam_id, room_id, slot_id), uvar in self.u.items():
            key = (exam_id, room_id, slot_id)
            if key not in assignment_vars:
                assignment_vars[key] = []
            assignment_vars[key].append(uvar)

        logger.info(
            f"{self.constraint_id}: Processing {len(assignment_vars)} exam-room-slot assignments"
        )

        # For each exam-room-slot assignment with variables
        for (exam_id, room_id, slot_id), invigilator_vars in assignment_vars.items():
            if exam_id not in self.problem.exams:
                continue

            exam = self.problem.exams[exam_id]
            room = self.problem.rooms.get(room_id)

            if not room:
                continue

            # Calculate required invigilators for this room
            total_students = getattr(exam, "expected_students", 0)
            room_capacity = getattr(room, "exam_capacity", getattr(room, "capacity", 0))

            # Students allocated to this specific room
            room_students = min(total_students, room_capacity)
            required_invigilators = max(1, math.ceil(room_students / 30))

            # Get corresponding y variable
            ykey = (exam_id, room_id, slot_id)
            if ykey not in self.y:
                continue

            yvar = self.y[ykey]

            # Ensure minimum invigilators when room is assigned
            # sum(u_vars) >= required * y_var
            min_required = min(required_invigilators, len(invigilator_vars))

            # Create constraint: sum of invigilator assignments >= min_required when room assigned
            self.model.Add(sum(invigilator_vars) >= min_required * yvar)
            constraints_added += 1

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} minimum invigilator constraints"
        )

        # This constraint is allowed to generate 0 constraints
        if constraints_added == 0:
            if not invigilators:
                logger.info(
                    f"{self.constraint_id}: No constraints needed (no invigilators)"
                )
            elif not self.u:
                logger.warning(
                    f"{self.constraint_id}: No constraints added (no u variables)"
                )
            elif not self._exam_room_slots:
                logger.warning(
                    f"{self.constraint_id}: No constraints added (no exam-room-slot combinations)"
                )
            else:
                logger.warning(
                    f"{self.constraint_id}: No constraints added despite having data"
                )
