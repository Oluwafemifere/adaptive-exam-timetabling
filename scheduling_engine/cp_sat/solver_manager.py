# scheduling_engine/cp_sat/solver_manager.py

"""
Solves the CP-SAT model and returns the extracted solution.
"""

import logging
import sys
from typing import Optional, Dict, Any, Tuple, cast

from ortools.sat.python import cp_model

from scheduling_engine.core.solution import TimetableSolution
from scheduling_engine.cp_sat.solution_extractor import SolutionExtractor
from scheduling_engine.data_flow_tracker import track_data_flow

logger = logging.getLogger(__name__)


class CPSATSolverManager:
    """Solver manager for the pure CP-SAT approach."""

    def __init__(self, problem):
        self.problem = problem
        self.model: Optional[cp_model.CpModel] = None
        self.shared_vars = None
        self.solver = cp_model.CpSolver()
        logger.info("Initialized CPSATSolverManager for a pure CP-SAT solve.")

    @track_data_flow("solve_model", include_stats=True)
    def solve(self) -> Tuple[int, TimetableSolution]:
        """Build model, configure solver, run Solve, and return (status, solution)."""
        from scheduling_engine.cp_sat.model_builder import CPSATModelBuilder

        logger.info("Starting CP-SAT solve process...")

        # Build the CP-SAT model
        builder = CPSATModelBuilder(problem=self.problem)
        # Configure with a complete set of constraints, including soft ones for optimization
        builder.configure("COMPLETE")
        self.model, self.shared_vars = builder.build()

        self._configure_solver_parameters()

        # Callback to log progress
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

        logger.info("Running CP-SAT solver...")
        # FIX: Use `cast` to inform the type checker that the status enum can be treated as an int.
        # This has no runtime effect but satisfies Pylance.
        raw_status = self.solver.Solve(self.model, callback)
        status = cast(int, raw_status)

        return self._process_solve_results(status, callback.solution_count)

    def _configure_solver_parameters(self) -> None:
        """Configure standard solver parameters for a good quality solution."""
        logger.info("Configuring CP-SAT solver parameters.")
        params = self.solver.parameters
        params.enumerate_all_solutions = False  # We want the best one found
        params.log_search_progress = True
        params.max_time_in_seconds = 300.0  # 5-minute timeout
        params.num_workers = 8  # Use multiple cores if available
        logger.info(f"Solver time limit set to {params.max_time_in_seconds}s.")

    def _process_solve_results(
        self, status: int, solution_count: int
    ) -> Tuple[int, TimetableSolution]:
        """Interpret solver status, log stats, and extract solution."""
        # The keys are enum members that behave like integers.
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

        # Compare the integer status directly with the enum members.
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            logger.error(
                f"No solution found. The problem may be infeasible or too complex for the time limit. Status: {status_name}"
            )
            # Return a default, empty solution
            return status, TimetableSolution(self.problem)

        try:
            # ---> START OF FIX <---
            solution_objective_value = self.solver.ObjectiveValue()
            logger.info(f"Best solution objective value: {solution_objective_value}")
        except Exception:
            solution_objective_value = 0.0  # Fallback if no objective is present
            logger.info("Solution found but no objective value is available.")

        logger.info("Extracting best solution found...")
        extractor = SolutionExtractor(self.problem, self.shared_vars, self.solver)
        solution = extractor.extract()
        solution.objective_value = (
            solution_objective_value  # Assign the extracted value
        )
        # ---> END OF FIX <---
        logger.info("Solution extraction complete.")

        return status, solution

    def get_solver_statistics(self) -> Dict[str, Any]:
        """Return runtime solver statistics."""
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
