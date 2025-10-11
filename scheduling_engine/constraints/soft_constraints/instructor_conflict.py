# File: scheduling_engine/constraints/soft_constraints/instructor_conflict.py

"""
REWRITTEN - InstructorConflictConstraint (Simplified Model)

This constraint penalizes an assignment if an instructor for a course is
assigned to invigilate in a room where that course's exam is taking place.
"""
from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
from scheduling_engine.core.constraint_types import ConstraintDefinition
import logging

logger = logging.getLogger(__name__)


class InstructorConflictConstraint(CPSATBaseConstraint):
    """S-Type: Penalize instructors invigilating their own exam."""

    dependencies = []

    def __init__(self, definition: ConstraintDefinition, problem, shared_vars, model):
        super().__init__(definition, problem, shared_vars, model)
        self.penalty_weight = self.definition.weight
        logger.info(
            f"🟡 Initializing SOFT constraint {self.constraint_id} with weight {self.penalty_weight}"
        )

    def initialize_variables(self):
        """No additional variables needed."""
        pass

    async def add_constraints(self):
        """Add penalties for instructors invigilating their own courses."""
        constraints_added = 0

        if not getattr(self, "w", None) or not getattr(self, "y", None):
            logger.info(
                f"{self.constraint_id}: No invigilator (w) or room (y) assignment variables, skipping."
            )
            self.constraint_count = 0
            return

        # Phase 2 subproblems are for a single slot, find which one.
        try:
            slot_id = next(iter(self.y.keys()))[2]
        except StopIteration:
            logger.info(f"{self.constraint_id}: No y_vars to process, skipping.")
            return

        for exam_id, exam in self.problem.exams.items():
            # Check only exams relevant to this subproblem
            if not any(k[0] == exam_id for k in self.y.keys()):
                continue

            for instructor_id in exam.instructor_ids:
                # Skip if instructor not a valid invigilator
                if instructor_id not in self.problem.invigilators:
                    continue

                for room_id in self.problem.rooms:
                    w_key = (instructor_id, room_id, slot_id)
                    y_key = (exam_id, room_id, slot_id)

                    w_var = self.w.get(w_key, None)
                    y_var = self.y.get(y_key, None)

                    # Both must exist (not None)
                    if w_var is None or y_var is None:
                        continue

                    conflict_var = self.model.NewBoolVar(
                        f"instr_conflict_{instructor_id}_{exam_id}_{room_id}"
                    )

                    # conflict_var true iff both w_var and y_var are true
                    self.model.AddBoolAnd([w_var, y_var]).OnlyEnforceIf(conflict_var)
                    self.model.AddBoolOr([w_var.Not(), y_var.Not()]).OnlyEnforceIf(
                        conflict_var.Not()
                    )

                    self.penalty_terms.append((self.penalty_weight, conflict_var))
                    constraints_added += 2

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added penalty logic for {constraints_added} potential instructor conflict assignments."
        )
