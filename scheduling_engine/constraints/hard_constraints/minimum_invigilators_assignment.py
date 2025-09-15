# FIXED scheduling_engine/constraints/hard_constraints/minimum_invigilators_assignment.py

"""
FIXED Invigilator Module (C10-C13) - Handles cases with no invigilators

Key Fix: Gracefully handles cases where no invigilators are available in the problem data.
"""

from scheduling_engine.constraints.base_constraint import (
    CPSATBaseConstraint,
)

import logging

logger = logging.getLogger(__name__)

# ===============================================================================
# C10: Minimum Invigilators Assignment - FIXED
# ===============================================================================


class MinimumInvigilatorsAssignmentConstraint(CPSATBaseConstraint):
    """
    INVIGILATOR_MODULE - C10: Minimum Invigilators Assignment - FIXED

    Mathematical formulation: ∀e ∈ E, r ∈ R, d ∈ D, t ∈ T: y[e,r,d,t] ⇒ ∑{u[i,e,r,d,t] : i ∈ I} ≥ minInvNeeded[e,r]

    FIXED: Gracefully handles cases where no invigilators are available.
    """

    dependencies = ["MultiExamRoomCapacityConstraint"]
    constraint_category = "INVIGILATOR"

    def _create_local_variables(self):
        """Precompute minimum invigilators needed for each exam-room pair."""
        self._invigilators = self._get_invigilators()

        # FIXED: Check if invigilators are available
        if not self._invigilators:
            logger.warning(
                f"{self.constraint_id}: No invigilators available - constraint will be skipped"
            )
            self._min_inv_needed = {}
            return

        self._min_inv_needed = {}
        for exam in self.problem.exams.values():
            exam_id = exam.id
            enrollment = len(self.problem.get_students_for_exam(exam_id))
            for room in self.problem.rooms.values():
                room_id = room.id
                max_per_inv = getattr(room, "max_students_per_invigilator", 30)
                min_needed = max(
                    1, (enrollment + max_per_inv - 1) // max_per_inv
                )  # Ceiling
                self._min_inv_needed[(exam_id, room_id)] = min_needed

        logger.info(
            f"{self.constraint_id}: Precomputed minimum requirements for "
            f"{len(self._min_inv_needed)} exam-room pairs with {len(self._invigilators)} invigilators"
        )

    def _add_constraint_implementation(self):
        """Add minimum invigilator assignment constraints using shared u variables."""
        # FIXED: Check if we have both y variables and invigilators
        if not self.y:
            raise RuntimeError(f"{self.constraint_id}: Missing y variables")

        if not self._invigilators:
            logger.info(
                f"{self.constraint_id}: No invigilators available - skipping constraint implementation"
            )
            return

        if not self.u:
            logger.warning(
                f"{self.constraint_id}: No u variables available (no invigilators) - skipping constraint implementation"
            )
            return

        constraints_added = 0
        for exam in self.problem.exams.values():
            exam_id = exam.id
            for room in self.problem.rooms.values():
                room_id = room.id
                min_needed = self._min_inv_needed.get((exam_id, room_id), 1)

                for day in self.problem.days:
                    for slot_id in self.problem.time_slots:
                        y_key = (exam_id, room_id, day, slot_id)
                        if y_key in self.y:
                            y_var = self.y[y_key]

                            # Collect u variables for this exam-room-day-slot
                            u_vars = []
                            for invigilator in self._invigilators:
                                u_key = (invigilator.id, exam_id, room_id, day, slot_id)
                                if u_key in self.u:
                                    u_vars.append(self.u[u_key])

                            if u_vars:
                                # y[e,r,d,t] ⇒ ∑{u[i,e,r,d,t]} ≥ minInvNeeded
                                self.model.Add(sum(u_vars) >= min_needed).OnlyEnforceIf(
                                    y_var
                                )
                                constraints_added += 1
                                self._increment_constraint_count()

        logger.info(
            f"{self.constraint_id}: Added {constraints_added} invigilator assignment constraints"
        )

    def _get_invigilators(self):
        """Get invigilators from problem (handle different attribute names)."""
        if hasattr(self.problem, "invigilators") and self.problem.invigilators:
            return list(self.problem.invigilators.values())
        elif hasattr(self.problem, "staff") and self.problem.staff:
            return [
                s
                for s in self.problem.staff.values()
                if getattr(s, "can_invigilate", True)
            ]
        elif hasattr(self.problem, "instructors") and self.problem.instructors:
            return list(self.problem.instructors.values())
        return []
