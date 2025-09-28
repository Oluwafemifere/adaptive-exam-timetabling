# scheduling_engine/cp_sat/solver_manager.py

"""
Solves the CP-SAT model with optional GA integration and returns the extracted solution.
"""

import logging
import sys
from typing import Optional, Dict, Any, Tuple, Union, cast

from ortools.sat.python import cp_model

from scheduling_engine.core.solution import TimetableSolution
from scheduling_engine.cp_sat.solution_extractor import SolutionExtractor
from scheduling_engine.data_flow_tracker import track_data_flow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("constraint_solver_test.log", mode="w"),
    ],
)

logger = logging.getLogger(__name__)


class CPSATSolverManager:
    """Solver manager with optional GA integration."""

    def __init__(
        self,
        problem,
        enable_ga_integration: bool = True,
        ga_parameters: Optional[Dict[str, Any]] = None,
    ):
        self.problem = problem
        self.model = None
        self.shared_vars = None
        self.solver = cp_model.CpSolver()
        self.enable_ga_integration = enable_ga_integration
        self.ga_parameters: Dict[str, Any] = ga_parameters or {
            "population_size": 50,
            "max_generations": 20,
            "pruning_aggressiveness": 0.2,
        }

        logger.info(
            "Initialized CPSATSolverManager. GA integration: %s", enable_ga_integration
        )

    @track_data_flow("solve_model", include_stats=True)
    def solve(self) -> Tuple[int, TimetableSolution]:
        """Build model, configure solver, run Solve, and return (status, solution)."""
        from scheduling_engine.cp_sat.model_builder import CPSATModelBuilder

        logger.info("Starting solve process")

        # Build model (builder may attach GA hints/stats to model/shared_vars)
        builder = CPSATModelBuilder(
            problem=self.problem,
            enable_ga_integration=self.enable_ga_integration,
            ga_parameters=self.ga_parameters,
        )

        self.model, self.shared_vars = builder.build()
        self._configure_solver_parameters()
        self._apply_ga_search_hints()

        # Solution callback for counting/logging found solutions
        class SolutionCallback(cp_model.CpSolverSolutionCallback):
            def __init__(self):
                super().__init__()
                self.solution_count = 0

            def on_solution_callback(self):
                self.solution_count += 1
                logger.info("Found solution #%d", self.solution_count)

        callback = SolutionCallback()

        logger.info("Running CP-SAT solver")
        status = cast(
            int, self.solver.Solve(self.model, callback)
        )  # Use enum value instead of int(status_enum)

        # callback.solution_count is available after Solve
        solution_count = getattr(callback, "solution_count", 0)

        return self._process_solve_results(status, solution_count)

    def _configure_solver_parameters(self) -> None:
        """Configure solver parameters depending on GA integration and model hints."""
        logger.info("Configuring CP-SAT parameters")

        params = self.solver.parameters
        params.enumerate_all_solutions = False
        params.cp_model_probing_level = 2
        params.linearization_level = 2
        params.log_search_progress = True

        params.max_time_in_seconds = 1800
        logger.info("Using standard time limit: 1800s")

        # Choose branching strategy when GA hints exist on model
        ga_hints = getattr(self.model, "_ga_search_hints", None)
        if ga_hints:
            params.search_branching = cp_model.PORTFOLIO_SEARCH
            logger.info("Using hint-guided search strategy (PORTFOLIO_SEARCH)")
        else:
            params.search_branching = cp_model.AUTOMATIC_SEARCH
            logger.info("Using automatic search strategy")

    def _apply_ga_search_hints(self) -> None:
        """Apply GA-generated search hints to CP-SAT model."""
        ga_hints = getattr(self.model, "gasearchhints", None)
        if not ga_hints:
            logger.debug("No GA search hints available")
            return

        logger.info(
            f"Applying {len(ga_hints)} GA-generated search hints to CP-SAT model"
        )

        hints_applied = 0
        for hint in ga_hints:
            try:
                if len(hint) >= 3:
                    var_key, var_value, confidence = hint[0], hint[1], hint[2]
                    cpsat_var = self._find_cpsat_variable(var_key)
                    if cpsat_var is not None:
                        # Add the hint to the MODEL, not the solver
                        assert self.model
                        self.model.AddHint(cpsat_var, int(var_value))
                        hints_applied += 1
            except Exception as e:
                logger.debug(f"Failed to apply hint {hint}: {e}")
                continue

        logger.info(f"Successfully applied {hints_applied} search hints to the model")

    def _find_cpsat_variable(self, var_key):
        """Find CP-SAT variable from variable key."""
        if not hasattr(self, "shared_vars") or not self.shared_vars:
            return None

        # Try different variable types
        if len(var_key) == 2:  # X or Z variable (exam_id, slot_id)
            return self.shared_vars.x_vars.get(var_key) or self.shared_vars.z_vars.get(
                var_key
            )
        elif len(var_key) == 3:  # Y variable (exam_id, room_id, slot_id)
            return self.shared_vars.y_vars.get(var_key)
        elif len(var_key) == 4:  # U variable (inv_id, exam_id, room_id, slot_id)
            return self.shared_vars.u_vars.get(var_key)

        return None

    def _process_solve_results(
        self, status: int, solution_count: int
    ) -> Tuple[int, TimetableSolution]:
        """Interpret solver status, log stats, and extract solution if any."""
        # Convert status constants to integers for comparison
        OPTIMAL = int(cp_model.OPTIMAL)
        FEASIBLE = int(cp_model.FEASIBLE)
        INFEASIBLE = int(cp_model.INFEASIBLE)
        MODEL_INVALID = int(cp_model.MODEL_INVALID)
        UNKNOWN = int(cp_model.UNKNOWN)

        status_map = {
            OPTIMAL: "OPTIMAL",
            FEASIBLE: "FEASIBLE",
            INFEASIBLE: "INFEASIBLE",
            MODEL_INVALID: "MODEL_INVALID",
            UNKNOWN: "UNKNOWN",
        }

        status_name = status_map.get(status, f"STATUS_{status}")
        logger.info("Solver finished with status: %s", status_name)

        if status not in (OPTIMAL, FEASIBLE):
            logger.error("No solution found. Status: %s", status_name)

            # Provide GA context when available
            if self.enable_ga_integration and self.shared_vars is not None:
                ga_stats = getattr(self.shared_vars, "ga_integration_stats", None)
                if ga_stats is not None:
                    total_pruned = getattr(ga_stats, "total_variables_pruned", None)
                    hints_applied = getattr(ga_stats, "ga_search_hints_applied", None)

                    logger.info(
                        "GA context - Variables pruned: %s, Hints applied: %s",
                        total_pruned,
                        hints_applied,
                    )

                    if total_pruned and total_pruned > 0:
                        logger.warning("Consider reducing GA pruning aggressiveness")

            return status, TimetableSolution(self.problem)

        # Successful or feasible solution: log solver stats
        try:
            obj_value = self.solver.ObjectiveValue()
            logger.info("Solution objective value: %s", obj_value)
        except Exception:
            logger.info("Solution found but no objective value available")

        logger.info(
            "Solver statistics: solutions=%d, conflicts=%d, branches=%d, wall_time=%.2fs",
            solution_count,
            self.solver.NumConflicts(),
            self.solver.NumBranches(),
            self.solver.WallTime(),
        )

        # GA integration reporting
        if self.enable_ga_integration and self.shared_vars is not None:
            ga_stats = getattr(self.shared_vars, "ga_integration_stats", None)
            if ga_stats is not None:
                logger.info(
                    "GA integration impact: pruned=%s, efficiency=%s, hints_applied=%s",
                    getattr(ga_stats, "total_variables_pruned", None),
                    getattr(ga_stats, "pruning_efficiency", None),
                    getattr(ga_stats, "ga_search_hints_applied", None),
                )

        # Extract solution
        logger.info("Extracting solution")
        extractor = SolutionExtractor(self.problem, self.shared_vars, self.solver)
        solution = extractor.extract()
        logger.info("Solution extraction completed")

        return status, solution

    def get_solver_statistics(self) -> Dict[str, Any]:
        """Return runtime solver statistics and optional GA metrics."""
        stats: Dict[str, Any] = {
            "solver_status": "initialized" if self.model is None else "completed",
            "wall_time": self.solver.WallTime(),
            "user_time": self.solver.UserTime(),
            "num_conflicts": self.solver.NumConflicts(),
            "num_branches": self.solver.NumBranches(),
            "ga_integration_enabled": self.enable_ga_integration,
        }

        if self.enable_ga_integration and self.shared_vars is not None:
            ga_stats = getattr(self.shared_vars, "ga_integration_stats", None)
            if ga_stats is not None:
                stats["ga_integration_stats"] = {
                    "variables_pruned": getattr(
                        ga_stats, "total_variables_pruned", None
                    ),
                    "pruning_efficiency": getattr(ga_stats, "pruning_efficiency", None),
                    "search_hints_applied": getattr(
                        ga_stats, "ga_search_hints_applied", None
                    ),
                    "constraint_relaxations": getattr(
                        ga_stats, "constraint_relaxations_applied", None
                    ),
                }

        try:
            stats["objective_value"] = self.solver.ObjectiveValue()
        except Exception:
            stats["objective_value"] = None

        return stats

    def configure_for_quick_solve(self) -> None:
        """Configure GA params for a faster, lower-quality run."""
        self.ga_parameters = {
            "population_size": 30,
            "max_generations": 10,
            "pruning_aggressiveness": self.ga_parameters.get(
                "pruning_aggressiveness", 0.2
            ),
        }
        logger.info("Configured for quick solving")

    def configure_for_quality_solve(self) -> None:
        """Configure GA params for a higher-quality run."""
        self.ga_parameters = {
            "population_size": 100,
            "max_generations": 50,
            "pruning_aggressiveness": self.ga_parameters.get(
                "pruning_aggressiveness", 0.2
            ),
        }
        logger.info("Configured for quality solving")
