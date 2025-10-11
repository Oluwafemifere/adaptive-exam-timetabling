# scheduling_engine/constraints/soft_constraints/carryover_student_conflict.py
"""
CarryoverStudentConflictConstraint - Soft Constraint (PARAMETERIZED & REVISED)

This constraint now penalizes ANY temporal conflict for a student that involves
at least one 'carryover' registration. This correctly handles both
'Normal vs. Carryover' and 'Carryover vs. Carryover' scenarios.
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
from scheduling_engine.core.constraint_types import ConstraintDefinition
import logging

logger = logging.getLogger(__name__)


class CarryoverStudentConflictConstraint(CPSATBaseConstraint):
    """Penalize any student conflict involving a carryover registration."""

    dependencies = ["UnifiedStudentConflictConstraint"]

    def __init__(self, definition: ConstraintDefinition, problem, shared_vars, model):
        super().__init__(definition, problem, shared_vars, model)
        self.penalty_weight = self.definition.weight
        logger.info(
            f"Initializing SOFT constraint {self.constraint_id} with weight {self.penalty_weight}"
        )

    def initialize_variables(self):
        """Initialize penalty variables for each potential conflict."""
        self.penalty_vars = []

    async def add_constraints(self):
        """Add penalties for any conflict involving a carryover student."""
        constraints_added = 0
        student_exams = self.precomputed_data.get("student_exams", {})
        if not student_exams:
            logger.warning(
                f"{self.constraint_id}: student_exams not found in precomputed_data."
            )
            return

        for student_id, exam_ids in student_exams.items():
            if len(exam_ids) <= 1:
                continue

            for slot_id in self.problem.timeslots:
                # --- START OF MODIFICATION ---

                # Step 1: Gather all exams for the student in this slot and check if any are carryovers.
                all_student_exams_in_slot = []
                has_carryover_registration = False

                for exam_id in exam_ids:
                    exam = self.problem.exams.get(exam_id)
                    if not exam:
                        continue

                    if exam.students.get(student_id) == "carryover":
                        has_carryover_registration = True

                    z_key = (exam_id, slot_id)
                    if z_key in self.z:
                        all_student_exams_in_slot.append(self.z[z_key])

                # Step 2: If there's a potential for an overlap (more than 1 exam) AND at least one of them
                # is a carryover registration, then create a penalty.
                if len(all_student_exams_in_slot) > 1 and has_carryover_registration:
                    # This variable will be 1 if the sum of scheduled exams is > 1, and 0 otherwise.
                    # The solver will try to keep this at 0 to avoid the penalty.
                    violation_var = self.model.NewBoolVar(
                        f"carryover_conflict_{student_id}_{slot_id}"
                    )

                    # If sum >= 2, violation_var must be 1.
                    self.model.Add(sum(all_student_exams_in_slot) >= 2).OnlyEnforceIf(
                        violation_var
                    )
                    # If sum <= 1, violation_var must be 0.
                    self.model.Add(sum(all_student_exams_in_slot) <= 1).OnlyEnforceIf(
                        violation_var.Not()
                    )

                    self.penalty_vars.append(violation_var)
                    constraints_added += 2

                # --- END OF MODIFICATION ---

        if self.penalty_vars:
            self.penalty_terms.extend(
                (self.penalty_weight, var) for var in self.penalty_vars
            )

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added penalty logic for {constraints_added} potential carryover conflicts."
        )
