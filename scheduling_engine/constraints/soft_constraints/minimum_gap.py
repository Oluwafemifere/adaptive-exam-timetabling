# scheduling_engine/constraints/soft_constraints/minimum_gap.py
"""
MinimumGapConstraint - S8 Implementation (PARAMETERIZED & FIXED)

This soft constraint penalizes instances where there is less than a minimum
gap (in slots) between consecutive exams for the same student on the same day.
This allows the solver to schedule back-to-back exams if necessary to find a
feasible solution, but it will be penalized.
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
from scheduling_engine.core.constraint_types import ConstraintDefinition
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class MinimumGapConstraint(CPSATBaseConstraint):
    """S8: Penalize violations of minimum gap between exams for the same student."""

    dependencies = ["UnifiedStudentConflictConstraint"]

    def __init__(self, definition: ConstraintDefinition, problem, shared_vars, model):
        super().__init__(definition, problem, shared_vars, model)
        self.penalty_weight = self.definition.weight
        logger.info(
            f"🟡 Initializing SOFT constraint {self.constraint_id} with weight {self.penalty_weight}"
        )

    def initialize_variables(self):
        """Initialize violation variables for minimum gap."""
        self.violation_vars = []

    def add_constraints(self):
        """Add minimum gap penalty constraints between student exams."""
        constraints_added = 0

        student_exams = self._get_student_exam_mappings()
        if not student_exams:
            logger.info(f"{self.constraint_id}: No student-exam mappings available.")
            self.constraint_count = 0
            return

        day_slot_groupings = self.precomputed_data.get("day_slot_groupings", {})
        if not day_slot_groupings:
            logger.error(f"{self.constraint_id}: Day/slot groupings not found.")
            return

        min_gap_slots = self.get_parameter_value("min_gap_slots", default=1)
        logger.info(
            f"{self.constraint_id}: Using min_gap_slots = {min_gap_slots} for penalty."
        )

        if min_gap_slots < 0:
            logger.warning(
                f"{self.constraint_id}: min_gap_slots is negative, skipping."
            )
            return

        exam_durations = {
            exam_id: self.problem.get_exam_duration_in_slots(exam_id)
            for exam_id in self.problem.exams
        }

        for student_id, exam_ids in student_exams.items():
            if len(exam_ids) <= 1:
                continue

            exam_list = list(exam_ids)
            for day_id, slot_ids in day_slot_groupings.items():
                day_slots = {slot_id: i for i, slot_id in enumerate(slot_ids)}

                for i in range(len(exam_list)):
                    for j in range(i + 1, len(exam_list)):
                        e1_id, e2_id = exam_list[i], exam_list[j]
                        dur1, dur2 = exam_durations.get(e1_id, 1), exam_durations.get(
                            e2_id, 1
                        )

                        for s1_id in slot_ids:
                            if (e1_id, s1_id) not in self.x:
                                continue
                            for s2_id in slot_ids:
                                if (e2_id, s2_id) not in self.x:
                                    continue

                                idx1, idx2 = day_slots[s1_id], day_slots[s2_id]
                                var1, var2 = (
                                    self.x[(e1_id, s1_id)],
                                    self.x[(e2_id, s2_id)],
                                )

                                # Check for a violation in both directions
                                is_violation = False
                                if idx1 < idx2 and idx1 + dur1 + min_gap_slots > idx2:
                                    is_violation = True
                                elif idx2 < idx1 and idx2 + dur2 + min_gap_slots > idx1:
                                    is_violation = True

                                if is_violation:
                                    # This pair of assignments violates the gap. Create a
                                    # violation variable that is true iff both are scheduled.
                                    violation_var = self.model.NewBoolVar(
                                        f"gap_viol_{student_id}_{e1_id}_{e2_id}"
                                    )
                                    # A violation occurs if var1 AND var2 are true.
                                    self.model.AddBoolAnd([var1, var2]).OnlyEnforceIf(
                                        violation_var
                                    )
                                    self.model.Add(
                                        sum([var1, var2]) <= 1
                                    ).OnlyEnforceIf(violation_var.Not())

                                    self.violation_vars.append(violation_var)
                                    constraints_added += 2

        # Add all violation variables to the list of terms to be minimized.
        if self.violation_vars:
            self.penalty_terms.extend(
                (self.penalty_weight, var) for var in self.violation_vars
            )

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} minimum gap penalty constraints."
        )

    def _get_student_exam_mappings(self):
        """Helper to get student-exam mappings."""
        student_exams = defaultdict(list)
        for exam_id, exam in self.problem.exams.items():
            if hasattr(exam, "students") and exam.students:
                for student_id in exam.students.keys():
                    student_exams[student_id].append(exam_id)
        return student_exams
