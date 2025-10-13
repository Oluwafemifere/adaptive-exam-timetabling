# scheduling_engine/constraints/hard_constraints/invigilator_requirement.py
"""
REVISED Foundational Constraint - InvigilatorRequirementConstraint

This constraint now serves a dual purpose:
1. HARD Constraint: Ensures the MINIMUM number of invigilators is met for all exams in a room.
2. SOFT Penalty: Penalizes assigning MORE invigilators than are required, promoting efficiency.
"""
from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
from scheduling_engine.core.constraint_types import ConstraintDefinition
import logging
import math
from backend.app.utils.celery_task_utils import task_progress_tracker

logger = logging.getLogger(__name__)


class InvigilatorRequirementConstraint(CPSATBaseConstraint):
    """
    Ensures invigilator requirements are met and penalizes over-assignment.
    """

    dependencies = ["RoomAssignmentConsistencyConstraint"]

    def __init__(self, definition: ConstraintDefinition, problem, shared_vars, model):
        super().__init__(definition, problem, shared_vars, model)
        # Define a weight for the soft penalty part of this constraint.
        self.surplus_penalty_weight = 1000

    def initialize_variables(self):
        """Initialize surplus variables for the penalty component."""
        self.surplus_invigilator_vars = []

    @task_progress_tracker(
        start_progress=58,
        end_progress=60,
        phase="building_phase_2_model",
        message="Applying invigilator requirements...",
    )
    async def add_constraints(self):
        """Links room assignments (y) to invigilator requirements (w)."""
        constraints_added = 0
        if not self.y or not self.w:
            logger.info(
                f"{self.constraint_id}: No room (y) or invigilator (w) assignment variables, skipping."
            )
            return

        spi = getattr(self.problem, "max_students_per_invigilator", 50)
        if spi <= 0:
            spi = 50
            logger.warning(
                f"{self.constraint_id}: max_students_per_invigilator is invalid, using default of 50."
            )

        all_slots = {key[2] for key in self.y.keys()}

        for slot_id in all_slots:
            for room_id, room in self.problem.rooms.items():

                # --- Sum of Assigned Invigilators ---
                assigned_invigilators_sum = sum(
                    self.w[w_key]
                    for inv_id in self.problem.invigilators
                    if (w_key := (inv_id, room_id, slot_id)) in self.w
                )

                # --- Calculation of Required Invigilators ---
                total_students_in_room_var = self.model.NewIntVar(
                    0, room.exam_capacity, f"total_students_{room_id}_{slot_id}"
                )
                student_load_terms = [
                    exam.expected_students * self.y[y_key]
                    for exam_id, exam in self.problem.exams.items()
                    if (y_key := (exam_id, room_id, slot_id)) in self.y
                ]
                if student_load_terms:
                    self.model.Add(
                        total_students_in_room_var == sum(student_load_terms)
                    )
                else:
                    self.model.Add(total_students_in_room_var == 0)

                # Integer division equivalent to ceil(total_students / spi)
                required_invigilators_var = self.model.NewIntVar(
                    0, len(self.problem.invigilators), f"req_inv_{room_id}_{slot_id}"
                )
                self.model.AddDivisionEquality(
                    required_invigilators_var, total_students_in_room_var + spi - 1, spi
                )

                # --- HARD CONSTRAINT: Meet the Minimum Requirement ---
                self.model.Add(assigned_invigilators_sum >= required_invigilators_var)
                constraints_added += 1

                # --- SOFT CONSTRAINT: Penalize Surplus ---
                surplus_var = self.model.NewIntVar(
                    0,
                    len(self.problem.invigilators),
                    f"surplus_inv_{room_id}_{slot_id}",
                )

                # surplus_var >= assigned_invigilators_sum - required_invigilators_var
                self.model.Add(
                    surplus_var >= assigned_invigilators_sum - required_invigilators_var
                )

                self.surplus_invigilator_vars.append(surplus_var)
                constraints_added += 1

        # Add penalty terms to the main objective function
        if self.surplus_invigilator_vars:
            self.penalty_terms.extend(
                (self.surplus_penalty_weight, var)
                for var in self.surplus_invigilator_vars
            )

        self.constraint_count = constraints_added
        logger.info(
            f"{self.constraint_id}: Added {constraints_added} constraints for invigilator requirements and surplus penalties."
        )
