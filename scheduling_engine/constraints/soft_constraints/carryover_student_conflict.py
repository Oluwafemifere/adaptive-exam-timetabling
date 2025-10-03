# scheduling_engine/constraints/soft_constraints/carryover_student_conflict.py
"""
CarryoverStudentConflictConstraint - Soft Constraint (PARAMETERIZED)

This constraint penalizes an exam if the number of students with a 'carryover'
registration who have a conflict with another exam exceeds a defined threshold.
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
from scheduling_engine.core.constraint_types import ConstraintDefinition
import logging

logger = logging.getLogger(__name__)


class CarryoverStudentConflictConstraint(CPSATBaseConstraint):
    """Penalize excessive carryover student conflicts for an exam."""

    dependencies = ["UnifiedStudentConflictConstraint"]

    def __init__(self, definition: ConstraintDefinition, problem, shared_vars, model):
        super().__init__(definition, problem, shared_vars, model)
        self.penalty_weight = self.definition.weight
        logger.info(
            f"Initializing SOFT constraint {self.constraint_id} with weight {self.penalty_weight}"
        )

    def initialize_variables(self):
        """Initialize penalty variables for each exam."""
        self.penalty_vars = {}
        for exam_id in self.problem.exams:
            self.penalty_vars[exam_id] = self.model.NewBoolVar(
                f"carryover_penalty_{exam_id}"
            )

    def add_constraints(self):
        """Add carryover student conflict penalty constraints."""

        max_allowed_conflicts = self.get_parameter_value(
            "max_allowed_conflicts", default=3
        )
        logger.info(
            f"{self.constraint_id}: Using max_allowed_conflicts = {max_allowed_conflicts}, weight = {self.penalty_weight}"
        )

        student_exams = self.precomputed_data.get("student_exams", {})
        if not student_exams:
            logger.warning(
                f"{self.constraint_id}: student_exams not found in precomputed_data."
            )
            return

        for exam1_id, exam1 in self.problem.exams.items():
            carryover_students = {
                sid for sid, rtype in exam1.students.items() if rtype == "carryover"
            }
            if not carryover_students:
                self.model.Add(self.penalty_vars[exam1_id] == 0)
                continue

            student_conflict_indicators = []

            for student_id in carryover_students:
                student_exam_ids = [eid for eid in student_exams.get(student_id, [])]
                if not student_exam_ids:
                    continue

                slot_conflict_vars = []

                # Check conflicts slot by slot
                for slot_id in self.problem.timeslots:
                    student_exams_in_slot = []
                    for eid in student_exam_ids:
                        z_var = self.z.get((eid, slot_id))
                        if z_var is not None:
                            student_exams_in_slot.append(z_var)

                    if len(student_exams_in_slot) <= 1:
                        continue

                    slot_conflict = self.model.NewBoolVar(
                        f"slot_conflict_{student_id}_{exam1_id}_{slot_id}"
                    )

                    # If slot_conflict is true then sum >= 2
                    self.model.Add(sum(student_exams_in_slot) >= 2).OnlyEnforceIf(
                        slot_conflict
                    )
                    # If slot_conflict is false then sum <= 1
                    self.model.Add(sum(student_exams_in_slot) <= 1).OnlyEnforceIf(
                        slot_conflict.Not()
                    )

                    slot_conflict_vars.append(slot_conflict)

                if not slot_conflict_vars:
                    continue

                student_has_conflict_var = self.model.NewBoolVar(
                    f"student_conflict_{student_id}_{exam1_id}"
                )

                self.model.AddBoolOr(slot_conflict_vars).OnlyEnforceIf(
                    student_has_conflict_var
                )
                self.model.Add(sum(slot_conflict_vars) == 0).OnlyEnforceIf(
                    student_has_conflict_var.Not()
                )

                student_conflict_indicators.append(student_has_conflict_var)

            if not student_conflict_indicators:
                self.model.Add(self.penalty_vars[exam1_id] == 0)
                continue

            total_conflicting_students = sum(student_conflict_indicators)

            # Penalty if total conflicts exceed threshold
            self.model.Add(
                total_conflicting_students >= (max_allowed_conflicts + 1)
            ).OnlyEnforceIf(self.penalty_vars[exam1_id])

            self.model.Add(
                total_conflicting_students <= max_allowed_conflicts
            ).OnlyEnforceIf(self.penalty_vars[exam1_id].Not())

        if self.penalty_vars:
            self.penalty_terms.extend(
                (self.penalty_weight, var) for var in self.penalty_vars.values()
            )

        self.constraint_count = len(self.problem.exams) * 2
        logger.info(
            f"{self.constraint_id}: Added carryover conflict penalty logic for {len(self.problem.exams)} exams."
        )
