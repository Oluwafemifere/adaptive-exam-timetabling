# scheduling_engine/cp_sat/model_builder.py
from collections import defaultdict
import logging
import time
import traceback
from typing import Optional, Dict, Any, Tuple, TYPE_CHECKING
from uuid import UUID
from ortools.sat.python import cp_model

from scheduling_engine.data_flow_tracker import track_data_flow

# TITLE: FIXED MODEL BUILDER - Pure CP-SAT Implementation

if TYPE_CHECKING:
    from .constraint_encoder import SharedVariables
    from scheduling_engine.core.problem_model import ExamSchedulingProblem

logger = logging.getLogger(__name__)


class CPSATModelBuilder:
    """FIXED: CP-SAT model builder for a pure constraint programming approach."""

    def __init__(self, problem: "ExamSchedulingProblem"):
        self.problem = problem
        self.model = cp_model.CpModel()
        self.shared_variables: Optional["SharedVariables"] = None
        self.build_start_time = 0.0
        self.build_duration = 0.0
        logger.info(f"Initialized CPSATModelBuilder for problem {problem.id}")

    def configure(self, configuration: str) -> None:
        """Configure the model builder with specific constraint sets"""
        logger.info(f"Configuring model builder with {configuration}")
        # Ensure soft constraints are included for a complete model
        if configuration == "COMPLETE":
            self.problem.constraint_registry.configure_complete()
        elif configuration == "MINIMAL":
            self.problem.constraint_registry.configure_minimal()
        elif configuration == "BASIC":
            self.problem.constraint_registry.configure_basic()
        elif configuration == "WITH_RESOURCES":
            self.problem.constraint_registry.configure_with_resources()
        else:
            logger.warning(
                f"Unknown configuration: {configuration}, using COMPLETE WITH SOFT."
            )
            self.problem.constraint_registry.configure_complete_with_soft()

    @track_data_flow("build_cp_sat_model", include_stats=True)
    def build(self) -> Tuple[cp_model.CpModel, "SharedVariables"]:
        """FIXED: Build process for a pure CP-SAT model."""
        self.build_start_time = time.time()
        try:
            logger.info("Starting CP-SAT model build process...")
            self._validate_problem_data_enhanced()

            logger.info("Creating constraint encoder and variables...")
            shared_variables = self._create_shared_variables()

            logger.info("Registering and applying constraints...")
            self._register_constraints(shared_variables)

            self._validate_final_model()
            self.build_duration = time.time() - self.build_start_time
            logger.info(f"Model build SUCCESS after {self.build_duration:.2f}s")

            self.shared_variables = shared_variables
            return self.model, shared_variables

        except Exception as e:
            self.build_duration = time.time() - self.build_start_time
            error_msg = f"Model building failed: {e}"
            logger.error(
                f"Model build FAILED after {self.build_duration:.2f}s: {error_msg}"
            )
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise RuntimeError(error_msg) from e

    def _create_shared_variables(self) -> "SharedVariables":
        """Creates shared variables using the constraint encoder."""
        from .constraint_encoder import ConstraintEncoder

        encoder = ConstraintEncoder(problem=self.problem, model=self.model)
        return encoder.encode()

    def _register_constraints(self, shared_variables: "SharedVariables") -> None:
        """Registers all active constraints from the problem's registry."""
        logger.info("--- Starting Constraint Registration ---")
        active_constraints = (
            self.problem.constraint_registry.get_active_constraint_classes()
        )
        logger.info(f"Found {len(active_constraints)} active constraints to apply.")

        for constraint_id, constraint_info in active_constraints.items():
            try:
                logger.debug(f"Applying constraint: {constraint_id}")
                constraint_class = constraint_info["class"]
                constraint_instance = constraint_class(
                    constraint_id=constraint_id,
                    problem=self.problem,
                    shared_vars=shared_variables,
                    model=self.model,
                )
                constraint_instance.add_constraints()
            except Exception as e:
                logger.error(
                    f"Failed to apply constraint {constraint_id}: {e}", exc_info=True
                )
                # Depending on severity, you might want to raise the exception
                # For now, we log it and continue to see if other constraints can be added.
                # raise e # Uncomment to fail fast

        logger.info("--- Finished Constraint Registration ---")

    def _validate_problem_data_enhanced(self) -> None:
        """Validates that the problem model contains the necessary data to build a CP model."""
        logger.info("Performing pre-build validation of problem data...")
        if not self.problem.exams:
            raise ValueError("No exams defined - cannot build model.")
        if not self.problem.timeslots:
            raise ValueError("No time slots defined - cannot build model.")
        if not self.problem.rooms:
            raise ValueError("No rooms defined - cannot build model.")
        if not self.problem.days:
            raise ValueError("No days defined - cannot build model.")

        total_timeslots = sum(len(day.timeslots) for day in self.problem.days.values())
        logger.info(
            f"Problem Dimensions: {len(self.problem.exams)} Exams, {total_timeslots} Timeslots, {len(self.problem.rooms)} Rooms."
        )

        student_registrations = sum(
            len(courses) for courses in self.problem._student_courses.values()
        )
        if student_registrations == 0:
            logger.warning(
                "No student course data found. Student conflict constraints will be ineffective."
            )

    def _validate_final_model(self) -> None:
        """Validates the final constructed CP-SAT model."""
        logger.info("Performing final model validation...")
        if not hasattr(self.model, "Proto"):
            raise RuntimeError("Invalid CP-SAT model created - missing Proto method.")

        try:
            proto = self.model.Proto()
            num_variables = len(proto.variables)
            num_constraints = len(proto.constraints)

            logger.info(
                f"Final Model Stats: {num_variables} variables, {num_constraints} constraints."
            )
            if num_variables == 0:
                raise RuntimeError("Model was built with no variables.")
            if num_constraints == 0:
                logger.warning(
                    "Model has no constraints. This may be intentional but is unusual."
                )
        except Exception as e:
            logger.warning(f"Could not extract final model statistics: {e}")

    def get_build_statistics(self) -> Dict[str, Any]:
        """Returns statistics about the model build process."""
        stats = {
            "build_duration": self.build_duration,
            "problem_entities": {
                "exams": len(self.problem.exams),
                "timeslots": len(self.problem.timeslots),
                "rooms": len(self.problem.rooms),
                "students": len(self.problem.students),
            },
            "active_constraints": len(
                self.problem.constraint_registry.get_active_constraints()
            ),
        }
        if self.shared_variables:
            stats["variable_counts"] = {
                "x_vars": len(self.shared_variables.x_vars),
                "y_vars": len(self.shared_variables.y_vars),
                "z_vars": len(self.shared_variables.z_vars),
                "u_vars": len(self.shared_variables.u_vars),
            }
        return stats
