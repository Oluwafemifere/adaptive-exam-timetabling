# scheduling_engine/cp_sat/model_builder.py
"""
REFACTORED Model Builder - Orchestrates model creation and delegates to the Constraint Manager.
"""

import logging
import time
import traceback
from typing import Optional, Tuple, TYPE_CHECKING
from ortools.sat.python import cp_model

from scheduling_engine.data_flow_tracker import track_data_flow
from scheduling_engine.cp_sat.constraint_encoder import ConstraintEncoder
from scheduling_engine.constraints.constraint_manager import CPSATConstraintManager
from scheduling_engine.core.constraint_types import ConstraintType

if TYPE_CHECKING:
    from .constraint_encoder import SharedVariables
    from scheduling_engine.core.problem_model import ExamSchedulingProblem


logger = logging.getLogger(__name__)


class CPSATModelBuilder:
    """Builds the CP-SAT model by orchestrating the encoder and constraint manager."""

    def __init__(self, problem: "ExamSchedulingProblem"):
        self.problem = problem
        self.model = cp_model.CpModel()
        self.shared_variables: Optional["SharedVariables"] = None
        self.build_duration = 0.0
        logger.info(f"Initialized CPSATModelBuilder for problem {problem.id}")

    @track_data_flow("build_cp_sat_model", include_stats=True)
    def build(self) -> Tuple[cp_model.CpModel, "SharedVariables"]:
        """Builds the full model by encoding variables and applying constraints."""
        build_start_time = time.time()
        try:
            logger.info("Starting CP-SAT model build process...")
            self._validate_problem_data()

            logger.info("Encoding variables...")
            encoder = ConstraintEncoder(problem=self.problem, model=self.model)
            self.shared_variables = encoder.encode()

            logger.info("Applying constraints via ConstraintManager...")
            constraint_manager = CPSATConstraintManager(problem=self.problem)
            build_stats = constraint_manager.build_model(
                self.model, self.shared_variables
            )

            # --- START OF FIX: Add objective function from penalty terms ---
            all_penalty_terms = []
            for instance in constraint_manager.get_constraint_instances():
                if instance.definition.constraint_type == ConstraintType.SOFT:
                    all_penalty_terms.extend(instance.get_penalty_terms())

            if all_penalty_terms:
                objective_expr = sum(
                    int(weight) * var for weight, var in all_penalty_terms
                )
                self.model.Minimize(objective_expr)
                logger.info(
                    f"Objective function set with {len(all_penalty_terms)} penalty terms."
                )
            else:
                logger.info(
                    "No penalty terms found; not setting an objective function."
                )
            if not build_stats.get("build_successful"):
                error_details = build_stats.get("error", "Unknown error")
                raise RuntimeError(
                    f"Constraint manager failed to build model. Error: {error_details}"
                )

            self._validate_final_model()
            self.build_duration = time.time() - build_start_time
            logger.info(f"Model build SUCCESS after {self.build_duration:.2f}s")

            return self.model, self.shared_variables

        except Exception as e:
            self.build_duration = time.time() - build_start_time
            error_msg = f"Model building failed: {e}"
            logger.error(
                f"Model build FAILED after {self.build_duration:.2f}s: {error_msg}"
            )
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise RuntimeError(error_msg) from e

    def _validate_problem_data(self) -> None:
        """Validates that the problem model contains the necessary data."""
        if not self.problem.exams:
            raise ValueError("No exams defined.")
        if not self.problem.timeslots:
            raise ValueError("No time slots defined.")
        if not self.problem.rooms:
            raise ValueError("No rooms defined.")
        if not self.problem.days:
            raise ValueError("No days defined.")

    def _validate_final_model(self) -> None:
        """Validates the final constructed CP-SAT model."""
        try:
            proto = self.model.Proto()
            num_vars = len(proto.variables)
            num_constraints = len(proto.constraints)
            logger.info(
                f"Final Model Stats: {num_vars} variables, {num_constraints} constraints."
            )
            if num_vars == 0:
                raise RuntimeError("Model was built with no variables.")
            if num_constraints == 0:
                logger.warning("Model has no constraints.")
        except Exception as e:
            logger.warning(f"Could not extract final model statistics: {e}")
