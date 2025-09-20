# scheduling_engine/constraints/hard_constraints/start_feasibility.py

"""
StartFeasibilityConstraint - H11 Implementation

H11: Start feasibility and slot fit - allowedStartSlots(e) enforces day boundaries

This constraint ensures that exams can only start at feasible slots where they
can complete within the same day. It enforces the mathematical definition:
allowedStartSlots(e) = { s ∈ SLOTS : t(s) ≤ 4 - dur_e }
"""

from scheduling_engine.constraints.base_constraint import (
    CPSATBaseConstraint,
    get_day_for_timeslot,
    get_slot_index_in_day,
)
import logging
import math

logger = logging.getLogger(__name__)


class StartFeasibilityConstraint(CPSATBaseConstraint):
    """H11: Start feasibility and slot fit constraint"""

    dependencies = []  # Foundation constraint
    constraint_category = "CORE"
    is_critical = True
    min_expected_constraints = 0  # May be 0 if all x variables respect feasibility

    def _create_local_variables(self):
        """No local variables needed for this constraint"""
        pass

    def _add_constraint_implementation(self):
        """Add start feasibility constraints"""
        constraints_added = 0

        # Check each x variable for feasibility
        for (exam_id, slot_id), x_var in self.x.items():
            if not self._is_start_feasible(exam_id, slot_id):
                # This start is infeasible - force x[e,s] = 0
                self.model.Add(x_var == 0)
                constraints_added += 1

        self.constraint_count = constraints_added

        if constraints_added == 0:
            logger.info(
                f"{self.constraint_id}: No constraints needed - all start variables are feasible"
            )
        else:
            logger.info(
                f"{self.constraint_id}: Added {constraints_added} start feasibility constraints"
            )

    def _is_start_feasible(self, exam_id, slot_id):
        """Check if an exam can start at a given slot and finish within the day"""
        try:
            # Get exam details
            exam = self.problem.exams.get(exam_id)
            if not exam:
                return False

            # Calculate required slots
            duration_minutes = getattr(exam, "duration_minutes", 180)
            required_slots = math.ceil(duration_minutes / 180.0)  # 180 min per slot

            # Get day containing this slot
            day = self.problem.get_day_for_timeslot(slot_id)
            if not day:
                return False

            # Find slot position within day
            slot_index = None
            for idx, timeslot in enumerate(day.timeslots):
                if timeslot.id == slot_id:
                    slot_index = idx
                    break

            if slot_index is None:
                return False

            # Check if exam fits within day: t(s) ≤ 4 - dur_e
            # Since we have 3 slots per day (indices 0, 1, 2), this becomes:
            # slot_index ≤ 3 - required_slots
            return slot_index <= (3 - required_slots)

        except Exception as e:
            logger.warning(
                f"Feasibility check failed for exam {exam_id}, slot {slot_id}: {e}"
            )
            return True  # Default to feasible if check fails
