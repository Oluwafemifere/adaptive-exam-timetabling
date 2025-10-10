# scheduling_engine/constraints/hard_constraints/unified_student_conflict.py
"""
UNIFIED STUDENT CONFLICT CONSTRAINT - Correct Implementation

This constraint ensures no student is scheduled for multiple exams in the same timeslot,
regardless of room assignments.
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class UnifiedStudentConflictConstraint(CPSATBaseConstraint):
    """H5/H10: Unified student conflict prevention - prevents temporal overlaps."""

    dependencies = ["OccupancyDefinitionConstraint"]

    def initialize_variables(self):
        """No local variables needed."""
        # This is also a good place to build and cache data.
        self.student_exams = self._build_student_exam_mapping()
        # Make this data available to other constraints that might depend on it
        if isinstance(self.precomputed_data, dict):
            self.precomputed_data["student_exams"] = self.student_exams

    def add_constraints(self):
        """
        MODIFIED: Add hard conflict constraints ONLY for overlaps involving two or more 'normal' registrations.
        All other conflicts (e.g., normal-vs-carryover) are handled by soft constraints.
        """
        constraints_added = 0
        if not self.z:
            raise RuntimeError(
                f"{self.constraint_id}: No z (occupancy) variables available."
            )

        if not self.student_exams:
            logger.info(
                f"{self.constraint_id}: No student registrations found, skipping."
            )
            self.constraint_count = 0
            return

        # --- VALIDATION LOGIC REMAINS UNCHANGED ---
        total_available_minutes = sum(
            ts.duration_minutes
            for day in self.problem.days.values()
            for ts in day.timeslots
        )
        logger.info(
            f"VALIDATION: Total available exam minutes in period: {total_available_minutes}"
        )
        for student_id, exam_ids in self.student_exams.items():
            total_student_exam_minutes = sum(
                self.problem.exams[eid].duration_minutes
                for eid in exam_ids
                if eid in self.problem.exams
            )
            if total_student_exam_minutes > total_available_minutes:
                logger.critical(
                    f"IMPOSSIBLE SCHEDULE DETECTED FOR STUDENT: {student_id}"
                )
                logger.critical(
                    f"  -> Total required exam time: {total_student_exam_minutes} minutes."
                )
                logger.critical(
                    f"  -> Total available time in whole period: {total_available_minutes} minutes."
                )
                logger.critical(f"  -> Exams: {exam_ids}")
        # --- END OF VALIDATION LOGIC ---

        for student_id, exam_ids in self.student_exams.items():
            if len(exam_ids) <= 1:
                continue

            for slot_id in self.problem.timeslots:
                # --- START OF MODIFICATION ---
                # Step 1: Gather ONLY the 'normal' exam occupancies for this student in this slot.
                normal_exams_in_slot = []
                for exam_id in exam_ids:
                    exam = self.problem.exams.get(exam_id)
                    if not exam:
                        continue

                    if exam.students.get(student_id) == "normal":
                        z_key = (exam_id, slot_id)
                        if z_key in self.z:
                            normal_exams_in_slot.append(self.z[z_key])

                # Step 2: If there's a potential for an overlap of two or more NORMAL exams, enforce the hard constraint.
                if len(normal_exams_in_slot) > 1:
                    self.model.Add(sum(normal_exams_in_slot) <= 1)
                    constraints_added += 1
                # --- END OF MODIFICATION ---

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} 'normal-vs-normal' student conflict constraints."
        )

    def _build_student_exam_mapping(self):
        """
        Build mapping of students to their registered exams by iterating through
        the populated Exam objects.
        """
        student_exams = defaultdict(list)
        logger.info("Building student-exam mappings from exam objects...")

        for exam_id, exam in self.problem.exams.items():
            # The 'students' attribute is a dictionary {student_id: registration_type}
            if hasattr(exam, "students") and exam.students:
                for student_id in exam.students.keys():
                    student_exams[student_id].append(exam_id)

        logger.info(f"Built mappings for {len(student_exams)} students.")
        return student_exams
