# scheduling_engine/cp_sat/model_builder.py
"""
REFACTORED Model Builder for Two-Phase Decomposition.
Orchestrates model creation by delegating to the appropriate phase-specific
methods in the Constraint Manager and Encoder.
"""

import logging
import time
import traceback
from typing import Any, Optional, Tuple, TYPE_CHECKING, List, Dict
from ortools.sat.python import cp_model

from scheduling_engine.data_flow_tracker import track_data_flow
from scheduling_engine.cp_sat.constraint_encoder import ConstraintEncoder
from scheduling_engine.constraints.constraint_manager import CPSATConstraintManager
from scheduling_engine.core.constraint_types import ConstraintType

# --- START OF MODIFICATION ---
from backend.app.utils.celery_task_utils import task_progress_tracker

# --- END OF MODIFICATION ---


if TYPE_CHECKING:
    from .constraint_encoder import SharedVariables
    from scheduling_engine.core.problem_model import ExamSchedulingProblem, Exam


logger = logging.getLogger(__name__)


class CPSATModelBuilder:
    """Builds the CP-SAT model by orchestrating the encoder and constraint manager."""

    def __init__(self, problem: "ExamSchedulingProblem"):
        self.problem = problem
        self.model = cp_model.CpModel()
        self.shared_variables: Optional["SharedVariables"] = None
        self.encoder: Optional[ConstraintEncoder] = None
        self.build_duration = 0.0
        # --- START OF MODIFICATION ---
        self.task_context: Optional[Any] = None
        # --- END OF MODIFICATION ---
        logger.info(f"Initialized CPSATModelBuilder for problem {problem.id}")

    @track_data_flow("build_phase1_model", include_stats=True)
    @task_progress_tracker(
        start_progress=25,
        end_progress=35,
        phase="building_phase_1_model",
        message="Building timetabling model...",
    )
    async def build_phase1(self) -> Tuple[cp_model.CpModel, "SharedVariables"]:
        """Builds the Phase 1 (Timetabling) model."""
        build_start_time = time.time()
        try:
            logger.info("========================================")
            logger.info("===   STARTING PHASE 1 MODEL BUILD   ===")
            logger.info("========================================")
            self._validate_problem_data()
            self.model = cp_model.CpModel()  # Reset model
            logger.info("Model object reset.")

            logger.info("Step 1: Encoding variables for Phase 1...")
            self.encoder = ConstraintEncoder(problem=self.problem, model=self.model)
            self.shared_variables = self.encoder.encode_phase1()
            logger.info("Variable encoding for Phase 1 complete.")

            # --- START OF NEW VALIDATION LOGIC ---
            logger.info("Performing pre-constraint validation on variables...")
            x_vars_by_exam = {exam_id: [] for exam_id in self.problem.exams}
            for (exam_id, slot_id), x_var in self.shared_variables.x_vars.items():
                x_vars_by_exam[exam_id].append(x_var)

            problematic_exams = []
            for exam_id, var_list in x_vars_by_exam.items():
                if not var_list:
                    exam = self.problem.exams.get(exam_id)
                    problematic_exams.append(
                        f"Exam ID: {exam_id} (Duration: {exam.duration_minutes} mins)"  # type: ignore
                    )

            if problematic_exams:
                error_message = (
                    "CRITICAL INFEASIBILITY DETECTED: The following exams have ZERO valid start slots. "
                    "This is a fundamental issue, likely because their duration exceeds any available "
                    "continuous time block on any single day. The problem cannot be solved."
                )
                logger.critical(error_message)
                for exam_str in problematic_exams:
                    logger.critical(f"  -> {exam_str}")
                raise ValueError(f"{error_message}: {', '.join(problematic_exams)}")
            else:
                logger.info(
                    "Pre-constraint validation passed: All exams have at least one potential start slot."
                )
            # --- END OF NEW VALIDATION LOGIC ---

            logger.info("Step 2: Building constraints for Phase 1...")
            constraint_manager = CPSATConstraintManager(problem=self.problem)
            # --- START OF FIX ---
            await constraint_manager.build_phase1_model(
                self.model, self.shared_variables
            )
            # --- END OF FIX ---
            logger.info("Constraint building for Phase 1 complete.")

            logger.info("Step 3: Adding objective function...")
            self._add_objective_function(constraint_manager)

            self.build_duration = time.time() - build_start_time
            logger.info(f"Phase 1 model build SUCCESS after {self.build_duration:.2f}s")
            return self.model, self.shared_variables

        except Exception as e:
            logger.critical(f"Phase 1 model building FAILED: {e}", exc_info=True)
            raise RuntimeError(f"Phase 1 model building failed: {e}") from e

    @track_data_flow("build_phase2_model", include_stats=True)
    @task_progress_tracker(
        start_progress=55,
        end_progress=65,
        phase="building_phase_2_model",
        message="Building room and invigilator model...",
    )
    async def build_phase2_full_model(
        self, phase1_results: Dict
    ) -> Tuple[cp_model.CpModel, "SharedVariables"]:
        """Builds the full Phase 2 (Packing) model based on Phase 1 results."""
        build_start_time = time.time()
        try:
            logger.info("========================================")
            logger.info("===   STARTING PHASE 2 MODEL BUILD   ===")
            logger.info("========================================")
            self.model = cp_model.CpModel()  # Reset model
            logger.info("Model object reset.")

            logger.info("Step 1: Encoding variables for Phase 2...")
            self.encoder = ConstraintEncoder(problem=self.problem, model=self.model)
            self.shared_variables = self.encoder.encode_phase2_full(phase1_results)
            logger.info("Variable encoding for Phase 2 complete.")

            logger.info("Step 2: Building constraints for Phase 2...")
            constraint_manager = CPSATConstraintManager(problem=self.problem)
            # --- START OF FIX ---
            await constraint_manager.build_phase2_model(
                self.model, self.shared_variables
            )
            # --- END OF FIX ---
            logger.info("Constraint building for Phase 2 complete.")

            logger.info("Step 3: Adding objective function...")
            self._add_objective_function(constraint_manager)

            self.build_duration = time.time() - build_start_time
            logger.info(
                f"Full Phase 2 model build SUCCESS after {self.build_duration:.2f}s"
            )
            return self.model, self.shared_variables

        except Exception as e:
            logger.critical(f"Full Phase 2 model building FAILED: {e}", exc_info=True)
            raise RuntimeError(f"Full Phase 2 model building failed: {e}") from e

    def _add_objective_function(self, constraint_manager: CPSATConstraintManager):
        """Adds minimization objective from soft constraint penalty terms."""
        all_penalty_terms = []
        for instance in constraint_manager.get_constraint_instances():
            if instance.definition.constraint_type == ConstraintType.SOFT:
                all_penalty_terms.extend(instance.get_penalty_terms())

        if all_penalty_terms:
            objective_expr = sum(int(weight) * var for weight, var in all_penalty_terms)
            self.model.Minimize(objective_expr)
            logger.info(
                f"Objective function set with {len(all_penalty_terms)} penalty terms from soft constraints."
            )
        else:
            logger.info(
                "No soft constraints with penalty terms found; no objective function set."
            )

    def _validate_problem_data(self) -> None:
        """Validates that the problem model contains the necessary data."""
        logger.info("Validating presence of core problem data (exams, slots, rooms)...")
        if not self.problem.exams:
            raise ValueError("Validation failed: No exams defined in the problem.")
        if not self.problem.timeslots:
            raise ValueError("Validation failed: No time slots defined in the problem.")
        if not self.problem.rooms:
            raise ValueError("Validation failed: No rooms defined in the problem.")
        logger.info("Core problem data validation passed.")
