# scheduling_engine/cp_sat/solver_manager.py

"""
Solves the CP-SAT model and returns the extracted solution.
"""

import logging
import sys
from ortools.sat.python import cp_model
from scheduling_engine.core.solution import TimetableSolution
from scheduling_engine.cp_sat.solution_extractor import SolutionExtractor

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,  # Changed to INFO to reduce verbose debug logs
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("constraint_solver_test.log", mode="w"),
    ],
)

logger = logging.getLogger(__name__)


class CPSATSolverManager:
    def __init__(self, problem):
        self.problem = problem
        self.model = None
        self.shared_vars = None
        self.solver = cp_model.CpSolver()

    def solve(self):
        from scheduling_engine.cp_sat.model_builder import CPSATModelBuilder

        # Build model and shared variables
        builder = CPSATModelBuilder(self.problem)
        self.model, self.shared_vars = builder.build()

        # Configure solver parameters for detailed logging
        self.solver.parameters.enumerate_all_solutions = False
        self.solver.parameters.cp_model_probing_level = 2
        self.solver.parameters.linearization_level = 2
        self.solver.parameters.max_time_in_seconds = 1800
        self.solver.parameters.log_search_progress = True  # Enable solver logging

        # Add solution callback for better debugging
        class SolutionCallback(cp_model.CpSolverSolutionCallback):
            def __init__(self):
                cp_model.CpSolverSolutionCallback.__init__(self)
                self.solution_count = 0

            def on_solution_callback(self):
                self.solution_count += 1
                logger.info(f"Found solution #{self.solution_count}")

        callback = SolutionCallback()

        # Solve the model (single call with callback)
        status = self.solver.Solve(self.model, callback)

        if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            logger.error(f"No solution found. Status: {status}")
            return status, TimetableSolution(self.problem)

        # Add status interpretation
        status_name = "UNKNOWN"
        if status == cp_model.OPTIMAL:
            status_name = "OPTIMAL"
        elif status == cp_model.FEASIBLE:
            status_name = "FEASIBLE"
        elif status == cp_model.INFEASIBLE:
            status_name = "INFEASIBLE"
        elif status == cp_model.MODEL_INVALID:
            status_name = "MODEL_INVALID"

        logger.info(f"Solver finished with status: {status_name}")

        # Log solver statistics
        logger.info(f"Solution objective value: {self.solver.ObjectiveValue()}")
        logger.info(f"Conflicts: {self.solver.NumConflicts()}")
        logger.info(f"Branches: {self.solver.NumBranches()}")

        # Extract solution
        extractor = SolutionExtractor(self.problem, self.shared_vars, self.solver)
        solution = extractor.extract()

        return status, solution
