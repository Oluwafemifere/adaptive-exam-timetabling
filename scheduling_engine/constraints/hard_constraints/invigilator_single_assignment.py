# FIXED scheduling_engine/constraints/hard_constraints/invigilator_single_assignment.py

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)

# ===============================================================================
# C11: Invigilator Single Assignment - FIXED
# ===============================================================================


class InvigilatorSingleAssignmentConstraint(CPSATBaseConstraint):
    """
    INVIGILATOR_MODULE - C11: Invigilator Single Assignment - FIXED

    Mathematical formulation: ∀i ∈ I, d ∈ D, t ∈ T: AtMostOne({u[i,e,r,d,t] : e ∈ E, r ∈ R})

    FIXED: Gracefully handles cases where no invigilators are available.
    """

    dependencies = ["MinimumInvigilatorsAssignmentConstraint"]
    constraint_category = "INVIGILATOR"

    def _create_local_variables(self):
        """No local variables needed - uses shared u variables."""
        self._invigilators = self._get_invigilators()

        # FIXED: Check if invigilators are available
        if not self._invigilators:
            logger.warning(
                f"{self.constraint_id}: No invigilators available - constraint will be skipped"
            )
            return

        logger.info(
            f"{self.constraint_id}: Using shared u variables for "
            f"{len(self._invigilators)} invigilators"
        )

    def _add_constraint_implementation(self):
        """Add AtMostOne constraints for invigilator single assignment."""
        # FIXED: Check if invigilators are available
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
        for invigilator in self._invigilators:
            invigilator_id = invigilator.id
            for day in self.problem.days:
                for slot_id in self.problem.time_slots:
                    # Collect all u variables for this invigilator at this time
                    assignment_vars = []
                    for exam in self.problem.exams.values():
                        exam_id = exam.id
                        for room in self.problem.rooms.values():
                            room_id = room.id
                            u_key = (invigilator_id, exam_id, room_id, day, slot_id)
                            if u_key in self.u:
                                assignment_vars.append(self.u[u_key])

                    # Add AtMostOne if invigilator has potential assignments
                    if len(assignment_vars) > 1:
                        self.model.AddAtMostOne(assignment_vars)
                        constraints_added += 1
                        self._increment_constraint_count()

        logger.info(
            f"{self.constraint_id}: Added {constraints_added} single assignment constraints"
        )

    def _get_invigilators(self):
        """Get invigilators from problem."""
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
