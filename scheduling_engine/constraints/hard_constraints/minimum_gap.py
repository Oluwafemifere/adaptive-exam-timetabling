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
    constraint_category = "STUDENT_CONSTRAINTS"
    is_critical = True
    min_expected_constraints = 0  # May be 0 if no multi-exam students

    def _create_local_variables(self):
        """No local variables needed for this constraint"""
        pass

    def _add_constraint_implementation(self):
        """Add minimum gap constraints between student exams"""
        constraints_added = 0

        # CRITICAL FIX: Get student_exams from multiple possible sources
        student_exams = self._get_student_exam_mappings()

        if not student_exams:
            logger.info(f"{self.constraint_id}: No student-exam mappings available")
            self.constraint_count = 0
            return

        logger.info(
            f"🔧 {self.constraint_id}: Processing {len(student_exams)} students for minimum gap constraints"
        )

        try:
            day_slot_groupings = self.get_day_slot_groupings()
        except ValueError as e:
            logger.error(f"{self.constraint_id}: {e}")
            self.constraint_count = 0
            return

        min_gap_slots = getattr(self.problem, "min_gap_slots", 1)
        if min_gap_slots < 1:
            logger.info(f"{self.constraint_id}: min_gap_slots is less than 1, skipping")
            self.constraint_count = 0
            return

        # Precompute exam durations
        exam_durations = {}
        for exam in self.problem.exams.values():
            exam_durations[exam.id] = math.ceil(exam.duration_minutes / 180.0)

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

                # Skip if no exams can be scheduled on this day
                if not any(possible_slots.values()):
                    continue

                for i in range(len(exam_list)):
                    exam1_id = exam_list[i]
                    dur1 = exam_durations.get(exam1_id, 1)
                    for j in range(i + 1, len(exam_list)):
                        exam2_id = exam_list[j]
                        dur2 = exam_durations.get(exam2_id, 1)

                        for idx1 in possible_slots[exam1_id]:
                            slot1_id = slot_ids[idx1]
                            var1 = self.x.get((exam1_id, slot1_id))
                            end1 = idx1 + dur1 - 1

                            for idx2 in possible_slots[exam2_id]:
                                slot2_id = slot_ids[idx2]
                                var2 = self.x.get((exam2_id, slot2_id))

                                if idx1 < idx2:
                                    # Exam2 starts too soon after Exam1 ends
                                    if idx2 <= end1 + min_gap_slots:
                                        self.model.Add(var1 + var2 <= 1)  # type: ignore
                                        constraints_added += 1
                                elif idx2 < idx1:
                                    # Exam1 starts too soon after Exam2 ends
                                    end2 = idx2 + dur2 - 1
                                    if idx1 <= end2 + min_gap_slots:
                                        self.model.Add(var1 + var2 <= 1)  # type: ignore
                                        constraints_added += 1

        self.constraint_count = constraints_added
        if constraints_added == 0:
            logger.info(
                f"{self.constraint_id}: No constraints needed - no gap conflicts detected"
            )
        else:
            logger.info(
                f"✅ {self.constraint_id}: Added {constraints_added} minimum gap constraints"
            )

    def _get_student_exam_mappings(self):
        """CRITICAL FIX: Get student-exam mappings from multiple sources"""
        # First try precomputed_data (set by UnifiedStudentConflictConstraint)
        if hasattr(self, "precomputed_data") and self.precomputed_data:
            student_exams = self.precomputed_data.get("student_exams", {})
            if student_exams:
                logger.debug(
                    f"{self.constraint_id}: Using student_exams from precomputed_data"
                )
                return student_exams

        # Fallback: try direct attribute
        if hasattr(self, "student_exams") and self.student_exams:
            logger.debug(
                f"{self.constraint_id}: Using student_exams from direct attribute"
            )
            return self.student_exams

        # Final fallback: build it ourselves (same logic as UnifiedStudentConflictConstraint)
        logger.debug(f"{self.constraint_id}: Building student_exams mapping locally")
        from collections import defaultdict

        student_exams = defaultdict(list)

        # Build course to exam mapping
        course_to_exam = {}
        for exam_id, exam in self.problem.exams.items():
            course_to_exam[exam.course_id] = exam_id

        # Map students to exams through their registered courses
        if hasattr(self.problem, "_student_courses"):
            for student_id, course_ids in self.problem._student_courses.items():
                for course_id in course_ids:
                    exam_id = course_to_exam.get(course_id)
                    if exam_id is not None:
                        student_exams[student_id].append(exam_id)

        return student_exams
