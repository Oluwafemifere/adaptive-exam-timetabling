# FIXED scheduling_engine/constraints/hard_constraints/invigilator_availability.py

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)

# ===============================================================================
# C12: Invigilator Availability - FIXED
# ===============================================================================


class InvigilatorAvailabilityConstraint(CPSATBaseConstraint):
    """
    INVIGILATOR_MODULE - C12: Invigilator Availability - FIXED

    Mathematical formulation: ∀i ∈ I, d ∈ D, t ∈ T: responsibility + assignments ≤ 1

    FIXED: Gracefully handles cases where no invigilators are available.
    """

    dependencies = ["InvigilatorSingleAssignmentConstraint"]
    constraint_category = "INVIGILATOR"

    def _create_local_variables(self):
        """Precompute invigilator responsibilities."""
        self._invigilators = self._get_invigilators()

        # FIXED: Check if invigilators are available
        if not self._invigilators:
            logger.warning(
                f"{self.constraint_id}: No invigilators available - constraint will be skipped"
            )
            self._invigilator_responsible = {}
            return

        self._invigilator_responsible = {}
        for exam in self.problem.exams.values():
            responsible_inv = getattr(exam, "invigilator", None)
            if responsible_inv:
                responsible_id = str(responsible_inv)
                if responsible_id not in self._invigilator_responsible:
                    self._invigilator_responsible[responsible_id] = []
                self._invigilator_responsible[responsible_id].append(exam.id)

        logger.info(
            f"{self.constraint_id}: Mapped responsibilities for "
            f"{len(self._invigilator_responsible)} invigilators out of {len(self._invigilators)} total"
        )

    def _add_constraint_implementation(self):
        """Add invigilator availability constraints."""
        # FIXED: Check if invigilators are available
        if not self._invigilators:
            logger.info(
                f"{self.constraint_id}: No invigilators available - skipping constraint implementation"
            )
            return

        if not self.z:
            logger.warning(
                f"{self.constraint_id}: Missing z variables - skipping constraint implementation"
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
            responsible_exams = self._invigilator_responsible.get(
                str(invigilator_id), []
            )

            for day in self.problem.days:
                for slot_id in self.problem.time_slots:
                    # Collect responsibility variables (z for responsible exams)
                    responsibility_vars = []
                    for exam_id in responsible_exams:
                        z_key = (exam_id, day, slot_id)
                        if z_key in self.z:
                            responsibility_vars.append(self.z[z_key])

                    # Collect assignment variables (u for this invigilator)
                    assignment_vars = []
                    for exam in self.problem.exams.values():
                        for room in self.problem.rooms.values():
                            u_key = (invigilator_id, exam.id, room.id, day, slot_id)
                            if u_key in self.u:
                                assignment_vars.append(self.u[u_key])

                    # Add availability constraint
                    all_vars = responsibility_vars + assignment_vars
                    if len(all_vars) > 1:
                        self.model.Add(sum(all_vars) <= 1)
                        constraints_added += 1
                        self._increment_constraint_count()

        logger.info(
            f"{self.constraint_id}: Added {constraints_added} availability constraints"
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
