"""
StudentGapPenaltyConstraint - S3 Implementation

S3: Student gap penalties (enhanced daily tracking)

For each student p and day d, define gapViol_{p,d} ∈ {0,1} which becomes 1
when the student has undesired gaps between exams on the same day.
Penalty: W_gap × ∑_{p,d} gapViol_{p,d} where W_gap = 2000.
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging
import math

logger = logging.getLogger(__name__)


class StudentGapPenaltyConstraint(CPSATBaseConstraint):
    """S3: Student gap penalties for undesired gaps between exams on same day"""

    dependencies = ["UnifiedStudentConflictConstraint"]
    constraint_category = "SOFT_CONSTRAINTS"
    is_critical = False
    min_expected_constraints = 0  # May be 0 if no multi-exam students

    def __init__(self, constraint_id, problem, shared_vars, model, factory=None):
        super().__init__(constraint_id, problem, shared_vars, model, factory)
        self.penalty_weight = 2000  # W_gap
        logger.info(
            f"🟡 Initializing SOFT constraint {constraint_id} with weight {self.penalty_weight}"
        )

    def _create_local_variables(self):
        """Create auxiliary variables for gap violations"""
        self.gap_viol_vars = {}

        student_exams = self.precomputed_data.get("student_exams", {})
        if not student_exams:
            return

        try:
            day_slot_groupings = self.get_day_slot_groupings()
        except ValueError:
            return

        # Create gap violation variables for students with multiple exams
        for student_id, exam_ids in student_exams.items():
            if len(exam_ids) <= 1:
                continue

            for day_key in day_slot_groupings.keys():
                gap_key = (student_id, day_key)
                self.gap_viol_vars[gap_key] = self.model.NewBoolVar(
                    f"gapViol_{student_id}_{day_key}"
                )

    def _add_constraint_implementation(self):
        """Add student gap penalty constraints"""
        constraints_added = 0

        student_exams = self.precomputed_data.get("student_exams", {})
        if not student_exams:
            logger.info(f"{self.constraint_id}: No student-exam mappings available")
            self.constraint_count = 0
            return

        if not self.gap_viol_vars:
            logger.info(f"{self.constraint_id}: No gap violation variables created")
            self.constraint_count = 0
            return

        try:
            day_slot_groupings = self.get_day_slot_groupings()
        except ValueError as e:
            logger.error(f"{self.constraint_id}: {e}")
            self.constraint_count = 0
            return

        min_gap_slots = getattr(self.problem, "min_gap_slots", 1)

        # For each student with multiple exams
        for student_id, exam_ids in student_exams.items():
            if len(exam_ids) <= 1:
                continue

            exam_list = list(exam_ids)

            # For each day
            for day_key, slot_ids in day_slot_groupings.items():
                gap_key = (student_id, day_key)
                if gap_key not in self.gap_viol_vars:
                    continue

                gap_viol_var = self.gap_viol_vars[gap_key]

                # Find exam pairs that violate gap requirements on this day
                gap_violation_indicators = []

                for i in range(len(exam_list)):
                    for j in range(i + 1, len(exam_list)):
                        exam1_id, exam2_id = exam_list[i], exam_list[j]

                        # Check for gap violations between these two exams
                        for idx1, slot1_id in enumerate(slot_ids):
                            z1_key = (exam1_id, slot1_id)
                            if z1_key not in self.z:
                                continue

                            exam1 = self.problem.exams.get(exam1_id)
                            if not exam1:
                                continue

                            dur1 = math.ceil(exam1.duration_minutes / 180.0)
                            exam1_end_idx = idx1 + dur1 - 1

                            # Check slots that would violate the gap requirement
                            for idx2, slot2_id in enumerate(slot_ids):
                                z2_key = (exam2_id, slot2_id)
                                if z2_key not in self.z:
                                    continue

                                # Check if this creates a gap violation
                                gap_distance = abs(idx2 - exam1_end_idx) - 1

                                if 0 <= gap_distance < min_gap_slots:
                                    # This combination creates a gap violation
                                    violation_var = self.model.NewBoolVar(
                                        f"gap_violation_{student_id}_{day_key}_{exam1_id}_{exam2_id}_{idx1}_{idx2}"
                                    )

                                    # violation_var = 1 if both exams are scheduled
                                    self.model.Add(violation_var <= self.z[z1_key])
                                    self.model.Add(violation_var <= self.z[z2_key])
                                    self.model.Add(
                                        violation_var
                                        >= self.z[z1_key] + self.z[z2_key] - 1
                                    )

                                    gap_violation_indicators.append(violation_var)
                                    constraints_added += 3

                # gapViol_{p,d} = 1 if any gap violation occurs on this day
                if gap_violation_indicators:
                    self.model.Add(
                        gap_viol_var
                        >= sum(gap_violation_indicators) / len(gap_violation_indicators)
                    )
                    constraints_added += 1
                else:
                    # No potential gap violations, so gap_viol_var = 0
                    self.model.Add(gap_viol_var == 0)
                    constraints_added += 1

        # Store penalty terms for objective function
        self.penalty_terms = []
        for gap_key, gap_viol_var in self.gap_viol_vars.items():
            self.penalty_terms.append((self.penalty_weight, gap_viol_var))

        self.constraint_count = constraints_added

        if constraints_added == 0:
            logger.info(f"{self.constraint_id}: No gap penalty constraints needed")
        else:
            logger.info(
                f"{self.constraint_id}: Added {constraints_added} student gap penalty constraints"
            )

    def get_penalty_terms(self):
        """Get penalty terms for the objective function"""
        return getattr(self, "penalty_terms", [])

    def get_statistics(self):
        """Get constraint statistics"""
        stats = super().get_constraint_statistics()
        stats.update(
            {
                "penalty_weight": self.penalty_weight,
                "student_day_pairs": len(self.gap_viol_vars),
                "penalty_terms": len(getattr(self, "penalty_terms", [])),
            }
        )
        return stats
