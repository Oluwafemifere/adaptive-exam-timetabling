# scheduling_engine/cp_sat/solver_manager.py

"""
REFACTORED - Solves the CP-SAT model and returns the extracted solution.
This version aligns with the dynamic model builder and supports parameterized solver settings.
"""

import logging
from typing import Optional, Dict, Any, Tuple, cast
from datetime import datetime

from ortools.sat.python import cp_model

from scheduling_engine.core.solution import SolutionStatus, TimetableSolution
from scheduling_engine.cp_sat.solution_extractor import SolutionExtractor
from scheduling_engine.data_flow_tracker import track_data_flow
from scheduling_engine.cp_sat.model_builder import CPSATModelBuilder

logger = logging.getLogger(__name__)


class CPSATSolverManager:
    """Solver manager that orchestrates the build and solve process for the CP-SAT model."""

    def __init__(self, problem):
        self.problem = problem
        self.model: Optional[cp_model.CpModel] = None
        self.shared_vars = None
        self.solver = cp_model.CpSolver()
        logger.info("Initialized CPSATSolverManager.")

    @track_data_flow("solve_model", include_stats=True)
    def solve(self) -> Tuple[int, TimetableSolution]:
        """Builds the model, configures the solver, runs the solve process, and returns the solution."""
        logger.info("Starting CP-SAT solve process...")

        # 1. Build the CP-SAT model using the refactored builder
        builder = CPSATModelBuilder(problem=self.problem)
        # The 'configure' call is no longer needed; the builder uses the active constraints
        # already present in the problem's constraint registry.
        self.model, self.shared_vars = builder.build()

        # 2. Configure solver runtime parameters (now parameterized)
        self._configure_solver_parameters()

        # 3. Set up a callback to log progress during the solve
        class SolutionCallback(cp_model.CpSolverSolutionCallback):
            def __init__(self):
                super().__init__()
                self._solution_count = 0

            def on_solution_callback(self):
                self._solution_count += 1
                logger.info(
                    f"Found solution #{self._solution_count}, Objective: {self.ObjectiveValue()}"
                )

            @property
            def solution_count(self):
                return self._solution_count

        callback = SolutionCallback()

        # 4. Run the solver
        logger.info("Running CP-SAT solver...")
        raw_status = self.solver.Solve(self.model, callback)
        status = cast(int, raw_status)

        # 5. Process the results and return the solution
        return self._process_solve_results(status, callback.solution_count)

    def _configure_solver_parameters(self) -> None:
        """Configures solver parameters, sourcing values from the problem model for HITL configurability."""
        logger.info("Configuring CP-SAT solver parameters from problem definition.")
        params = self.solver.parameters

        # --- Standard Parameters ---
        params.enumerate_all_solutions = False
        params.log_search_progress = True

        # --- Parameterized from UI/Config ---
        # Get time limit from the problem object, with a safe default
        time_limit = getattr(self.problem, "solver_time_limit_seconds", 300.0)
        params.max_time_in_seconds = float(time_limit)

        # Get worker count from the problem object, with a safe default
        num_workers = getattr(self.problem, "solver_num_workers", 8)
        params.num_workers = int(num_workers)

        logger.info(
            f"Solver configured: TimeLimit={params.max_time_in_seconds}s, Workers={params.num_workers}"
        )

    def _process_solve_results(
        self, status: int, solution_count: int
    ) -> Tuple[int, TimetableSolution]:
        """Interprets solver status, logs statistics, and extracts the final solution."""
        status_map: Dict[int, str] = {
            cp_model.OPTIMAL: "OPTIMAL",
            cp_model.FEASIBLE: "FEASIBLE",
            cp_model.INFEASIBLE: "INFEASIBLE",
            cp_model.MODEL_INVALID: "MODEL_INVALID",
            cp_model.UNKNOWN: "UNKNOWN",
        }
        status_name = status_map.get(status, f"STATUS_{status}")
        logger.info(f"Solver finished with status: {status_name}")

        logger.info(
            "Solver Stats: Solutions Found=%d, Conflicts=%d, Branches=%d, WallTime=%.2fs",
            solution_count,
            self.solver.NumConflicts(),
            self.solver.NumBranches(),
            self.solver.WallTime(),
        )

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            logger.error(
                f"No solution found. Status: {status_name}. The problem may be infeasible or too complex for the time limit."
            )
            return status, TimetableSolution(self.problem)

        try:
            solution_objective_value = self.solver.ObjectiveValue()
            logger.info(f"Best solution objective value: {solution_objective_value}")
        except Exception:
            solution_objective_value = 0.0
            logger.warning("Solution found but no objective value is available.")

        logger.info("Extracting best solution found...")
        extractor = SolutionExtractor(self.problem, self.shared_vars, self.solver)
        solution = extractor.extract()
        solution.objective_value = solution_objective_value

        # --- START OF FIX ---
        # Update the solution's status based on the solver's result before returning.
        if status == cp_model.OPTIMAL:
            solution.status = SolutionStatus.OPTIMAL
        elif status == cp_model.FEASIBLE:
            solution.status = SolutionStatus.FEASIBLE
        # --- END OF FIX ---

        logger.info("Solution extraction complete.")

        return status, solution

    def get_solver_statistics(self) -> Dict[str, Any]:
        """Returns runtime solver statistics after a solve is complete."""
        stats = {
            "wall_time": self.solver.WallTime(),
            "user_time": self.solver.UserTime(),
            "num_conflicts": self.solver.NumConflicts(),
            "num_branches": self.solver.NumBranches(),
        }
        try:
            stats["objective_value"] = self.solver.ObjectiveValue()
        except Exception:
            stats["objective_value"] = None
        return stats
