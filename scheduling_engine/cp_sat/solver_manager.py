# scheduling_engine/cp_sat/solver_manager.py
"""
CP-SAT Solver Manager for exam scheduling.
Manages solver execution, configuration, and result collection.
Based on the research paper's CP-SAT solving approach.
"""

from typing import Dict, List, Optional, Any, Callable, TYPE_CHECKING
import time
import threading
import os
from uuid import UUID
from ortools.sat.python import cp_model

# psutil is optional at runtime. handle missing import gracefully for dev environments.
if TYPE_CHECKING:
    import psutil
else:
    try:
        import psutil
    except ImportError:
        psutil = None

from ..config import get_logger, CPSATConfig
from ..core.problem_model import ExamSchedulingProblem
from ..core.solution import SolutionStatus
from .solution_extractor import SolutionExtractor, ExtractionContext

logger = get_logger("cp_sat.solver_manager")


class SolverCallback(cp_model.CpSolverSolutionCallback):
    """Callback for tracking solver progress"""

    def __init__(
        self, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> None:
        super().__init__()
        self.progress_callback = progress_callback
        self.solution_count = 0
        self.start_time = time.time()
        self.best_objective = float("inf")

    def on_solution_callback(self) -> None:
        """Called when solver finds a new solution"""
        self.solution_count += 1
        current_time = time.time()
        elapsed = current_time - self.start_time

        # Get current objective value if available
        try:
            current_objective = self.ObjectiveValue()
            if current_objective < self.best_objective:
                self.best_objective = current_objective
        except Exception:
            current_objective = 0

        progress_info = {
            "solution_count": self.solution_count,
            "elapsed_time": elapsed,
            "current_objective": current_objective,
            "best_objective": self.best_objective,
            "solver_phase": "cp_sat",
        }

        if self.progress_callback:
            try:
                self.progress_callback(progress_info)
            except Exception as e:
                logger.debug(f"Progress callback raised: {e}")

        logger.debug(
            f"Solution {self.solution_count} found with objective {current_objective}"
        )


class CPSATSolverManager:
    """
    Manages CP-SAT solver execution and configuration.
    Handles the constraint programming phase of the hybrid approach.
    """

    def __init__(self, config: Optional[CPSATConfig] = None) -> None:
        self.config = config or CPSATConfig()
        self.solver = cp_model.CpSolver()
        self.solution_extractor = SolutionExtractor()

        # Configure solver
        self._configure_solver()

        # Tracking variables
        self.solving_statistics: Dict[str, Any] = {}
        self.memory_monitor: Optional[threading.Thread] = None
        self.peak_memory_mb: float = 0.0
        self._monitor_memory: bool = False

        logger.debug("CPSATSolverManager initialized")

    def _configure_solver(self) -> None:
        """Configure CP-SAT solver parameters"""
        # Time limit
        try:
            self.solver.parameters.max_time_in_seconds = self.config.time_limit_seconds
        except Exception:
            # Some parameter names may vary across OR-Tools versions.
            pass

        # Number of workers (parallel search)
        try:
            self.solver.parameters.num_search_workers = self.config.num_workers
        except Exception:
            pass

        # Search strategy parameters - guarded in case of API differences
        try:
            self.solver.parameters.cp_model_presolve = True
            self.solver.parameters.cp_model_probing_level = 2
        except Exception:
            pass

        # Logging
        try:
            if self.config.log_search_progress:
                self.solver.parameters.log_search_progress = True
                self.solver.parameters.log_to_stdout = False
        except Exception:
            pass

        # Variable selection strategy (may be overridden by variable selector)
        try:
            self.solver.parameters.search_branching = cp_model.PORTFOLIO_SEARCH
        except Exception:
            # ignore if constant is unavailable
            pass

        logger.debug("CP-SAT solver configured")

    def solve(
        self,
        model: cp_model.CpModel,
        problem: ExamSchedulingProblem,
        variables: Dict[str, Any],
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        variable_selector: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Solve the CP-SAT model.
        Returns a results dictionary.
        """
        logger.info("Starting CP-SAT solving")
        start_time = time.time()

        # Start memory monitoring
        self._start_memory_monitoring()

        try:
            # Set up callback
            callback = SolverCallback(progress_callback) if progress_callback else None

            # Apply variable selector if provided (from GA evolution)
            if variable_selector:
                self._apply_variable_selector(model, variable_selector, problem)

            # Solve the model. Do not coerce solver status to int. Keep raw status.
            if callback:
                raw_status = self.solver.SolveWithSolutionCallback(model, callback)
            else:
                raw_status = self.solver.Solve(model)

            status = raw_status  # keep original type (int or CpSolverStatus-like)

            # Stop memory monitoring
            self._stop_memory_monitoring()

            # Calculate runtime
            runtime = time.time() - start_time

            # Collect results
            results = self._collect_solving_results(
                status, model, problem, variables, runtime, callback
            )

            logger.info(
                f"CP-SAT solving completed in {runtime:.2f}s with status {status}"
            )
            return results

        except Exception as e:
            self._stop_memory_monitoring()
            logger.error(f"Error during CP-SAT solving: {e}")
            return {
                "status": "ERROR",
                "error": str(e),
                "runtime": time.time() - start_time,
                "solution": None,
            }

    def _apply_variable_selector(
        self,
        model: cp_model.CpModel,
        variable_selector: Callable,
        problem: ExamSchedulingProblem,
    ) -> None:
        """
        Apply evolved variable selector to guide CP-SAT search.
        This is the key integration point with the GA evolution.
        """
        logger.debug("Applying evolved variable selector")

        try:
            # Attempt to set fixed search mode; ignore if unavailable
            try:
                self.solver.parameters.search_branching = cp_model.FIXED_SEARCH
            except Exception:
                # Fall back to default strategy
                pass
        except Exception as e:
            logger.warning(f"Failed to apply variable selector: {e}")
            # Fall back to default strategy
            try:
                self.solver.parameters.search_branching = cp_model.PORTFOLIO_SEARCH
            except Exception:
                pass

    def _collect_solving_results(
        self,
        status: Any,
        model: cp_model.CpModel,
        problem: ExamSchedulingProblem,
        variables: Dict[str, Any],
        runtime: float,
        callback: Optional[SolverCallback],
    ) -> Dict[str, Any]:
        """Collect comprehensive solving results"""

        # Map status constants to readable string using OR-Tools constants
        status_map = {
            cp_model.OPTIMAL: "OPTIMAL",
            cp_model.FEASIBLE: "FEASIBLE",
            cp_model.INFEASIBLE: "INFEASIBLE",
            cp_model.UNKNOWN: "UNKNOWN",
            cp_model.MODEL_INVALID: "MODEL_INVALID",
        }

        # Try to resolve mapping value. If not found fall back to str(status).
        status_str = status_map.get(status, "UNKNOWN")

        results: Dict[str, Any] = {
            "status": status_str,
            "runtime": runtime,
            "objective_value": None,
            "solution": None,
            "statistics": self._get_solver_statistics(),
            "memory_usage": {
                "peak_memory_mb": self.peak_memory_mb,
                "final_memory_mb": self._get_current_memory_mb(),
            },
        }

        # Extract solution if found
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            try:
                # Create extraction context
                context = ExtractionContext(
                    solver=self.solver,
                    model=model,
                    variables=variables,
                    problem=problem,
                    solver_status=status,
                    solve_time_seconds=runtime,
                )

                extraction_result = self.solution_extractor.extract_solution(context)

                if extraction_result and extraction_result.solution:
                    results["solution"] = extraction_result.solution
                    # support solution object carrying objective_value
                    results["objective_value"] = getattr(
                        extraction_result.solution, "objective_value", None
                    )

                    # Update solution status
                    try:
                        extraction_result.solution.status = (
                            SolutionStatus.OPTIMAL
                            if status == cp_model.OPTIMAL
                            else SolutionStatus.FEASIBLE
                        )
                        extraction_result.solution.solver_phase = "cp_sat"
                    except Exception:
                        # If solution object is missing attributes ignore
                        pass

            except Exception as e:
                logger.error(f"Error extracting solution: {e}")
                results["solution"] = None

        # Add callback statistics if available
        if callback:
            results["callback_statistics"] = {
                "solution_count": callback.solution_count,
                "best_objective": callback.best_objective,
            }

        # Store last solving statistics for external inspection
        try:
            self.solving_statistics = results.get("statistics", {})
        except Exception:
            pass

        return results

    def _get_solver_statistics(self) -> Dict[str, Any]:
        """Get detailed solver statistics"""
        stats: Dict[str, Any] = {}
        try:
            stats = {
                "num_booleans": self.solver.NumBooleans(),
                "num_conflicts": self.solver.NumConflicts(),
                "num_branches": self.solver.NumBranches(),
                "wall_time": self.solver.WallTime(),
                "user_time": self.solver.UserTime(),
            }
        except Exception:
            # If introspection fails return minimal stats
            return stats

        # Optional oracles that may not exist in all OR-Tools versions
        for attr_name in ("DeterministicTime", "NumRestarts", "NumImplications"):
            fn = getattr(self.solver, attr_name, None)
            if callable(fn):
                try:
                    stats[attr_name.lower()] = fn()
                except Exception:
                    pass

        return stats

    def _start_memory_monitoring(self) -> None:
        """Start monitoring memory usage"""
        self.peak_memory_mb = 0.0
        self._monitor_memory = True

        def monitor() -> None:
            while getattr(self, "_monitor_memory", False):
                current_memory = self._get_current_memory_mb()
                if current_memory > self.peak_memory_mb:
                    self.peak_memory_mb = current_memory
                time.sleep(0.1)  # Check every 100ms

        self.memory_monitor = threading.Thread(target=monitor, daemon=True)
        self.memory_monitor.start()

    def _stop_memory_monitoring(self) -> None:
        """Stop monitoring memory usage"""
        self._monitor_memory = False
        if self.memory_monitor and self.memory_monitor.is_alive():
            self.memory_monitor.join(timeout=1.0)

    def _get_current_memory_mb(self) -> float:
        """Get current memory usage in MB"""
        try:
            if psutil is None:
                return 0.0
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except Exception:
            return 0.0

    def solve_with_time_limit(
        self,
        model: cp_model.CpModel,
        problem: ExamSchedulingProblem,
        variables: Dict[str, Any],
        time_limit_seconds: int,
        progress_callback: Optional[Callable] = None,
        variable_selector: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Solve with specific time limit"""
        original_time_limit = None
        try:
            original_time_limit = getattr(
                self.solver.parameters, "max_time_in_seconds", None
            )
            try:
                self.solver.parameters.max_time_in_seconds = time_limit_seconds
            except Exception:
                pass

            results = self.solve(
                model=model,
                problem=problem,
                variables=variables,
                progress_callback=progress_callback,
                variable_selector=variable_selector,
            )
            return results
        finally:
            # Restore original time limit if we could capture it
            if original_time_limit is not None:
                try:
                    self.solver.parameters.max_time_in_seconds = original_time_limit
                except Exception:
                    pass

    def solve_for_feasibility(
        self,
        model: cp_model.CpModel,
        problem: ExamSchedulingProblem,
        variables: Dict[str, Any],
        max_time_seconds: int = 300,
    ) -> Dict[str, Any]:
        """
        Solve specifically for feasibility (first phase of hybrid approach).
        Based on research paper's two-phase strategy.
        """
        logger.info("Solving for feasibility (CP-SAT phase)")

        # Configure for feasibility search
        original_params = self._backup_solver_parameters()

        try:
            # Set parameters optimized for finding feasible solutions quickly
            try:
                self.solver.parameters.max_time_in_seconds = max_time_seconds
            except Exception:
                pass
            try:
                self.solver.parameters.cp_model_presolve = True
            except Exception:
                pass
            try:
                self.solver.parameters.num_search_workers = min(
                    4, self.config.num_workers
                )
            except Exception:
                pass

            # Focus on finding any feasible solution
            try:
                self.solver.parameters.optimize_with_core = False
            except Exception:
                pass
            try:
                self.solver.parameters.search_branching = cp_model.AUTOMATIC_SEARCH
            except Exception:
                pass

            results = self.solve(model, problem, variables)

            # Mark as feasibility-focused result
            results["solving_phase"] = "feasibility"
            results["is_feasibility_search"] = True

            return results

        finally:
            self._restore_solver_parameters(original_params)

    def _backup_solver_parameters(self) -> Dict[str, Any]:
        """Backup current solver parameters"""
        p = self.solver.parameters
        return {
            "max_time_in_seconds": getattr(p, "max_time_in_seconds", None),
            "num_search_workers": getattr(p, "num_search_workers", None),
            "cp_model_presolve": getattr(p, "cp_model_presolve", None),
            "optimize_with_core": getattr(p, "optimize_with_core", None),
            "search_branching": getattr(p, "search_branching", None),
        }

    def _restore_solver_parameters(self, params: Dict[str, Any]) -> None:
        """Restore solver parameters from backup"""
        p = self.solver.parameters
        for param_name, value in params.items():
            try:
                if value is None:
                    continue
                setattr(p, param_name, value)
            except Exception:
                pass

    def validate_model_before_solving(
        self, model: cp_model.CpModel
    ) -> Dict[str, List[str]]:
        """Validate model before attempting to solve"""
        errors: List[str] = []
        warnings: List[str] = []

        # Check model validity
        if model is None:
            errors.append("Model is None")
            return {"errors": errors, "warnings": warnings}

        # Check for variables
        try:
            proto = model.Proto()
            if not proto.variables:
                errors.append("Model has no variables")
            if not proto.constraints:
                warnings.append("Model has no constraints")
        except Exception:
            # If introspection on model fails just return the minimal checks
            pass

        # Check time limit
        try:
            if getattr(self.solver.parameters, "max_time_in_seconds", 0) <= 0:
                warnings.append("Time limit is not set or invalid")
        except Exception:
            pass

        return {"errors": errors, "warnings": warnings}

    def get_solving_statistics(self) -> Dict[str, Any]:
        """Get comprehensive solving statistics"""
        return {
            "solver_version": "OR-Tools CP-SAT",
            "configuration": {
                "time_limit_seconds": self.config.time_limit_seconds,
                "num_workers": self.config.num_workers,
                "log_search_progress": self.config.log_search_progress,
            },
            "last_solve_statistics": self.solving_statistics,
            "peak_memory_mb": self.peak_memory_mb,
        }

    def solve_with_variable_ordering(
        self,
        problem: ExamSchedulingProblem,
        variable_ordering: Dict[UUID, float],
        max_time_seconds: int = 30,
    ) -> Dict[str, Any]:
        """Solve using a specific variable ordering from genetic algorithm"""
        from ..cp_sat.model_builder import CPSATModelBuilder

        # Build the model
        model_builder = CPSATModelBuilder(self.config)
        model = model_builder.build_model(problem)
        variables = model_builder.get_variables()

        # Create a variable selector function from the ordering
        def variable_selector():
            return variable_ordering

        # Solve with time limit and variable selector
        return self.solve_with_time_limit(
            model,
            problem,
            variables,  # type: ignore
            max_time_seconds,
            variable_selector=variable_selector,
        )
