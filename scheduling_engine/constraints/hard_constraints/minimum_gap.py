"""
MinimumGapConstraint - H7 Implementation

H7: Minimum gap between exams for same student

This constraint ensures that there is a minimum gap (in slots)
between consecutive exams for the same student on the same day.
"""

from scheduling_engine.constraints.base_constraint import (
    CPSATBaseConstraint,
    get_day_for_timeslot,
)
import logging
import math

logger = logging.getLogger(__name__)


class MinimumGapConstraint(CPSATBaseConstraint):
    """H7: Minimum gap between exams for same student"""

    dependencies = ["UnifiedStudentConflictConstraint"]
    constraint_category = "STUDENT_GAP"
    is_critical = True
    min_expected_constraints = 0  # May be 0 if no multi-exam students

    def _create_local_variables(self):
        """No local variables needed for this constraint"""
        pass

    def _add_constraint_implementation(self):
        """Add minimum gap constraints between student exams"""
        constraints_added = 0

        student_exams = self.precomputed_data.get("student_exams", {})
        if not student_exams:
            logger.info(f"{self.constraint_id}: No student-exam mappings available")
            self.constraint_count = 0
            return

        try:
            day_slot_groupings = self.get_day_slot_groupings()
        except ValueError as e:
            logger.error(f"{self.constraint_id}: {e}")
            self.constraint_count = 0
            return

        min_gap_slots = getattr(self.problem, "min_gap_slots", 1)

        # For each student with multiple exams
        for student_id, exam_ids in student_exams.items():
            if len(exam_ids) <= 1:
                continue

            exam_list = list(exam_ids)
            # For every day
            for day_key, slot_ids in day_slot_groupings.items():
                # Build a mapping from exam to possible slots on this day
                possible_slots = {
                    exam_id: [
                        idx
                        for idx, slot_id in enumerate(slot_ids)
                        if (exam_id, slot_id) in self.x
                    ]
                    for exam_id in exam_list
                }
                for i in range(len(exam_list)):
                    for j in range(i + 1, len(exam_list)):
                        exam1_id, exam2_id = exam_list[i], exam_list[j]

                        for idx1 in possible_slots[exam1_id]:
                            slot1_id = slot_ids[idx1]
                            var1 = self.z.get((exam1_id, slot1_id))
                            if var1 is None:
                                continue
                            exam1 = self.problem.exams.get(exam1_id)
                            if not exam1:
                                continue
                            dur1 = math.ceil(exam1.duration_minutes / 180.0)
                            exam1_end_idx = idx1 + dur1 - 1

                            # Forbid assignment of exam2 within min_gap_slots after exam1 ends
                            for idx2 in possible_slots[exam2_id]:
                                slot2_id = slot_ids[idx2]
                                var2 = self.z.get((exam2_id, slot2_id))
                                if var2 is None:
                                    continue
                                # Exam2 starts has to be STRICTLY after the forbidden gap
                                if 0 < idx2 - exam1_end_idx <= min_gap_slots:
                                    self.model.Add(var1 + var2 <= 1)
                                    constraints_added += 1
                                # Also forbid cases where the exams are swapped
                                elif 0 < exam1_end_idx - idx2 < min_gap_slots:
                                    self.model.Add(var1 + var2 <= 1)
                                    constraints_added += 1

        self.constraint_count = constraints_added
        if constraints_added == 0:
            logger.info(
                f"{self.constraint_id}: No constraints needed - no gap conflicts detected"
            )
        else:
            logger.info(
                f"{self.constraint_id}: Added {constraints_added} minimum gap constraints"
            )
