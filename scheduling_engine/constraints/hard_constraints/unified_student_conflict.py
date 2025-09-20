# UNIFIED scheduling_engine/constraints/unified_student_conflict.py

"""
UNIFIED STUDENT CONFLICT CONSTRAINT - Correct Implementation

This constraint ensures no student is scheduled for multiple exams in the same timeslot,
regardless of room assignments. This is the correct implementation that prevents
individual student conflicts rather than using overly restrictive global constraints.

CRITICAL FIXES:
1. Correct per-student constraint implementation instead of global restrictions
2. Proper handling of student-exam registrations
3. Efficient constraint grouping by student and timeslot
4. Enhanced validation and debugging
5. Graceful degradation for edge cases
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging
from collections import defaultdict
from uuid import UUID

logger = logging.getLogger(__name__)


class UnifiedStudentConflictConstraint(CPSATBaseConstraint):
    """H5/H10: Unified student conflict prevention - prevents temporal overlaps"""

    dependencies = ["OccupancyDefinitionConstraint"]
    constraint_category = "STUDENT_CONFLICTS"
    is_critical = True
    min_expected_constraints = 0  # May be 0 if no students or exams

    def _create_local_variables(self):
        """No local variables needed"""
        pass

    def _add_constraint_implementation(self):
        """Add correct student conflict constraints - prevent students from having multiple exams in same timeslot"""
        constraints_added = 0

        # Validate Z variables are available
        if not hasattr(self, "z") or not self.z:
            logger.error(f"❌ CRITICAL {self.constraint_id}: No z variables available")
            logger.error(
                "This indicates a dependency issue with OccupancyDefinitionConstraint"
            )
            raise RuntimeError(
                "Cannot create student conflict constraints - no z variables"
            )

        # Build student-exam mapping
        student_exams = self._build_student_exam_mapping()

        if not student_exams:
            logger.info(
                f"{self.constraint_id}: No student registrations found - no constraints needed"
            )
            self.constraint_count = 0
            return

        logger.info(
            f"🔧 {self.constraint_id}: Processing {len(student_exams)} students with exam registrations"
        )

        # Precompute timeslot list and create a local reference for faster access
        slot_ids = list(self.problem.timeslots.keys())
        z_dict = self.z  # Local reference for faster lookup

        # For each student, ensure they don't have multiple exams in the same timeslot
        for student_id, exam_ids in student_exams.items():
            # Create a set for faster membership testing
            exam_set = set(exam_ids)
            for slot_id in slot_ids:
                student_exams_in_slot = []
                # Check each exam for this student in the current timeslot
                for exam_id in exam_ids:
                    z_key = (exam_id, slot_id)
                    # Use direct dict.get for faster lookup
                    z_var = z_dict.get(z_key)
                    if z_var is not None:
                        student_exams_in_slot.append(z_var)

                # Add constraint: each student can have at most one exam per timeslot
                if len(student_exams_in_slot) > 1:
                    self.model.Add(sum(student_exams_in_slot) <= 1)
                    constraints_added += 1

        self.constraint_count = constraints_added

        # Report results
        if constraints_added == 0:
            logger.info(
                f"{self.constraint_id}: No constraints needed (no temporal conflicts detected)"
            )
        else:
            logger.info(
                f"✅ {self.constraint_id}: Added {constraints_added} student conflict constraints "
                f"for {len(student_exams)} students across {len(slot_ids)} timeslots"
            )

    def _build_student_exam_mapping(self):
        """Build mapping of students to their registered exams using course registrations"""
        student_exams = defaultdict(list)

        # Build course to exam mapping
        course_to_exam = {}
        for exam_id, exam in self.problem.exams.items():
            course_to_exam[exam.course_id] = exam_id

        # Map students to exams through their registered courses
        for student_id, course_ids in self.problem._student_courses.items():
            for course_id in course_ids:
                exam_id = course_to_exam.get(course_id)
                if exam_id is not None:
                    student_exams[student_id].append(exam_id)

        return student_exams

    def _debug_constraint_creation_failure(self):
        """Debug why constraint creation failed when conflicts exist"""
        logger.debug("Debug analysis for constraint creation:")
        logger.debug(f" • Available z variables: {len(self.z)}")

        # Sample z variable analysis
        sample_z_keys = list(self.z.keys())[:5] if self.z else []
        logger.debug(f" • Sample z keys: {sample_z_keys}")

        # Student registration analysis
        logger.debug(f" • Total students: {len(self.problem.students)}")
        logger.debug(f" • Total exams: {len(self.problem.exams)}")
