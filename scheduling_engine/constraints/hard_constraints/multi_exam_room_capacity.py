# scheduling_engine/constraints/hard_constraints/multi_exam_room_capacity.py

"""
C4: Multi-Exam Room Capacity Constraint - Mathematically Accurate Implementation

∀r ∈ R, d ∈ D, t ∈ T: ∑{enrol_e × y[e,r,d,t] : e ∈ E} ≤ effectiveCap_r

Ensures total enrollment doesn't exceed room effective capacity.
"""

from scheduling_engine.constraints.base_constraint import (
    CPSATBaseConstraint,
)
import logging

logger = logging.getLogger(__name__)


class MultiExamRoomCapacityConstraint(CPSATBaseConstraint):
    """
    MULTI_EXAM_CAPACITY_MODULE - C4: Multi-Exam Room Capacity

    Mathematical formulation: ∀r ∈ R, d ∈ D, t ∈ T: ∑{enrol_e × y[e,r,d,t] : e ∈ E} ≤ effectiveCap_r
    """

    dependencies = ["RoomAssignmentBasicConstraint"]
    constraint_category = "MULTI_EXAM_CAPACITY"

    def _create_local_variables(self):
        """Precompute exam enrollments."""
        self._exam_enrollments = {}
        for exam in self.problem.exams.values():
            exam_id = str(exam.id)
            # Get enrollment from exam or count students
            enrollment = getattr(
                exam, "enrollment", len(self.problem.get_students_for_exam(exam.id))
            )
            self._exam_enrollments[exam_id] = enrollment

        logger.info(
            f"{self.constraint_id}: Precomputed enrollments for "
            f"{len(self._exam_enrollments)} exams"
        )

    def _add_constraint_implementation(self):
        """Add multi-exam room capacity constraints."""
        if not self.y:
            raise RuntimeError(f"{self.constraint_id}: No y variables available")

        for room in self.problem.rooms.values():
            room_id = room.id
            room_key = str(room_id)
            effective_capacity = self.effective_capacities.get(room_key, room.capacity)

            for day in self.problem.days:
                for slot_id in self.problem.time_slots:
                    # Collect enrollment terms: enrol_e × y[e,r,d,t]
                    enrollment_terms = []

                    for exam in self.problem.exams.values():
                        exam_id = exam.id
                        exam_key = str(exam_id)

                        y_key = (exam_id, room_id, day, slot_id)
                        if y_key in self.y:
                            enrollment = self._exam_enrollments.get(exam_key, 0)
                            if enrollment > 0:
                                enrollment_terms.append(enrollment * self.y[y_key])

                    # Add capacity constraint if there are terms
                    if enrollment_terms:
                        assert effective_capacity
                        self.model.Add(sum(enrollment_terms) <= effective_capacity)
                        self._increment_constraint_count()

                        logger.debug(
                            f"{self.constraint_id}: Added capacity constraint for "
                            f"room {room_id},{day},{slot_id} - capacity: {effective_capacity}"
                        )
