# scheduling_engine/cp_sat/model_builder.py
"""
REFACTORED Model Builder for Two-Phase Decomposition.
Orchestrates model creation by delegating to the appropriate phase-specific
methods in the Constraint Manager and Encoder.
"""

import logging
import time
import traceback
from typing import Optional, Tuple, TYPE_CHECKING, List, Dict
from ortools.sat.python import cp_model

from scheduling_engine.data_flow_tracker import track_data_flow
from scheduling_engine.cp_sat.constraint_encoder import ConstraintEncoder
from scheduling_engine.constraints.constraint_manager import CPSATConstraintManager
from scheduling_engine.core.constraint_types import ConstraintType

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
        logger.info(f"Initialized CPSATModelBuilder for problem {problem.id}")

    @track_data_flow("build_phase1_model", include_stats=True)
    def build_phase1(self) -> Tuple[cp_model.CpModel, "SharedVariables"]:
        """Builds the Phase 1 (Timetabling) model."""
        build_start_time = time.time()
        try:
            logger.info("Starting Phase 1 model build process...")
            self._validate_problem_data()
            self.model = cp_model.CpModel()  # Reset model

            self.encoder = ConstraintEncoder(problem=self.problem, model=self.model)
            self.shared_variables = self.encoder.encode_phase1()

            constraint_manager = CPSATConstraintManager(problem=self.problem)
            constraint_manager.build_phase1_model(self.model, self.shared_variables)

            self._add_objective_function(constraint_manager)

            self.build_duration = time.time() - build_start_time
            logger.info(f"Phase 1 model build SUCCESS after {self.build_duration:.2f}s")
            return self.model, self.shared_variables

        except Exception as e:
            raise RuntimeError(f"Phase 1 model building failed: {e}") from e

    @track_data_flow("build_phase2_model", include_stats=True)
    def build_phase2_full_model(
        self, phase1_results: Dict
    ) -> Tuple[cp_model.CpModel, "SharedVariables"]:
        """Builds the full Phase 2 (Packing) model based on Phase 1 results."""
        build_start_time = time.time()
        try:
            logger.info("Starting FULL Phase 2 model build process (Packing)...")
            self.model = cp_model.CpModel()  # Reset model

            self.encoder = ConstraintEncoder(problem=self.problem, model=self.model)
            self.shared_variables = self.encoder.encode_phase2_full(phase1_results)

            constraint_manager = CPSATConstraintManager(problem=self.problem)
            constraint_manager.build_phase2_model(self.model, self.shared_variables)

            self._add_objective_function(constraint_manager)

            self.build_duration = time.time() - build_start_time
            logger.info(
                f"Full Phase 2 model build SUCCESS after {self.build_duration:.2f}s"
            )
            return self.model, self.shared_variables

        except Exception as e:
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
                f"Objective function set with {len(all_penalty_terms)} penalty terms."
            )

    def _validate_problem_data(self) -> None:
        """Validates that the problem model contains the necessary data."""
        if not self.problem.exams:
            raise ValueError("No exams defined.")
        if not self.problem.timeslots:
            raise ValueError("No time slots defined.")
        if not self.problem.rooms:
            raise ValueError("No rooms defined.")
