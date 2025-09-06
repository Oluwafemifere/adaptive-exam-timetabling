# scheduling_engine/hybrid/coordinator.py

"""
Hybrid Coordinator - Main orchestrator for CP-SAT + GA pipeline.
Implements the hybrid genetic-based constraint programming approach from the research paper.
"""

from typing import Dict, List, Optional, Any, Callable
from uuid import uuid4
from datetime import datetime
import time
from dataclasses import dataclass
from enum import Enum

from ..config import get_logger, SchedulingEngineConfig
from ..core.problem_model import ExamSchedulingProblem
from ..core.solution import TimetableSolution, SolutionStatus
from ..core.metrics import SolutionMetrics, QualityScore
from ..core.constraint_registry import ConstraintRegistry

from ..cp_sat.model_builder import CPSATModelBuilder
from ..cp_sat.solver_manager import CPSATSolverManager
from ..genetic_algorithm.chromosome import VariableSelectorChromosome
from ..genetic_algorithm.population import Population
from ..genetic_algorithm.evolution_manager import EvolutionManager, EvolutionConfig

logger = get_logger("hybrid.coordinator")


class OptimizationPhase(Enum):
    """Phases in the hybrid optimization process"""

    INITIALIZATION = "initialization"
    CP_SAT_FEASIBILITY = "cp_sat_feasibility"
    GA_EVOLUTION = "ga_evolution"
    SOLUTION_REFINEMENT = "solution_refinement"
    FINALIZATION = "finalization"


@dataclass
class OptimizationResults:
    """Results from hybrid optimization process"""

    # Best solution found
    best_solution: Optional[TimetableSolution] = None
    best_chromosome: Optional[VariableSelectorChromosome] = None

    # Solution progression
    cp_sat_solution: Optional[TimetableSolution] = None
    ga_solution: Optional[TimetableSolution] = None

    # Performance metrics
    total_runtime: float = 0.0
    cp_sat_runtime: float = 0.0
    ga_runtime: float = 0.0

    # Quality metrics
    final_objective_value: float = float("inf")
    final_fitness_score: float = 0.0
    solution_quality: Optional[QualityScore] = None

    # Evolution statistics
    generations_executed: int = 0
    solutions_evaluated: int = 0

    # Success indicators
    is_feasible: bool = False
    is_optimal: bool = False
    terminated_early: bool = False
    termination_reason: str = ""


class HybridCoordinator:
    """
    Main coordinator for the hybrid genetic-based constraint programming approach.

    Implements the two-phase optimization strategy from the research paper:
    1. CP-SAT phase: Find feasible solutions quickly
    2. GA phase: Evolve variable selectors to improve solution quality
    """

    def __init__(self, config: Optional[SchedulingEngineConfig] = None):
        self.config = config or SchedulingEngineConfig()

        # Core components
        self.cp_sat_builder = CPSATModelBuilder(self.config.cp_sat)
        self.cp_sat_solver = CPSATSolverManager(self.config.cp_sat)
        self.evolution_manager: Optional[EvolutionManager] = None
        self.constraint_registry = ConstraintRegistry()
        self.metrics = SolutionMetrics()

        # State tracking
        self.current_phase = OptimizationPhase.INITIALIZATION
        self.problem: Optional[ExamSchedulingProblem] = None
        self.optimization_id = uuid4()

        # Results tracking
        self.results = OptimizationResults()
        self.progress_callbacks: List[Callable[[Dict[str, Any]], None]] = []

        logger.info("HybridCoordinator initialized with hybrid GP-CP approach")

    def add_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Add callback for progress updates"""
        self.progress_callbacks.append(callback)

    def _notify_progress(self, progress_info: Dict[str, Any]) -> None:
        """Notify all progress callbacks"""
        progress_info["optimization_id"] = str(self.optimization_id)
        progress_info["phase"] = self.current_phase.value
        progress_info["timestamp"] = datetime.now().isoformat()

        for callback in self.progress_callbacks:
            try:
                callback(progress_info)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

    async def optimize_schedule(
        self, problem: ExamSchedulingProblem, time_limit_seconds: Optional[int] = None
    ) -> OptimizationResults:
        """
        Main optimization method implementing the hybrid approach.

        Args:
            problem: The exam scheduling problem to solve
            time_limit_seconds: Optional total time limit for optimization

        Returns:
            Optimization results with best solution found
        """
        logger.info(f"Starting hybrid optimization for {len(problem.exams)} exams")
        start_time = time.time()
        self.problem = problem
        self.optimization_id = uuid4()

        # Initialize evolution manager with problem
        evolution_config = EvolutionConfig()
        self.evolution_manager = EvolutionManager(problem, evolution_config)

        try:
            # Phase 1: CP-SAT for feasibility
            await self._execute_cp_sat_phase()

            # Phase 2: GA for optimization (if feasible solution found)
            if (
                self.results.cp_sat_solution is not None
                and self.results.cp_sat_solution.is_feasible()
            ):
                await self._execute_ga_phase()

            # Phase 3: Finalization
            await self._finalize_optimization()

            # Calculate total runtime
            self.results.total_runtime = time.time() - start_time

            logger.info(
                f"Hybrid optimization completed in {self.results.total_runtime:.2f}s"
            )
            return self.results

        except Exception as e:
            logger.error(f"Error during hybrid optimization: {e}")
            self.results.terminated_early = True
            self.results.termination_reason = str(e)
            self.results.total_runtime = time.time() - start_time
            return self.results

    async def _execute_cp_sat_phase(self) -> None:
        """
        Execute CP-SAT phase for finding feasible solutions.
        Implements the first phase from the research paper.
        """
        if not self.problem:
            raise ValueError("Problem not set for CP-SAT phase")

        logger.info("Executing CP-SAT phase for feasibility")
        self.current_phase = OptimizationPhase.CP_SAT_FEASIBILITY

        self._notify_progress({"message": "Building CP-SAT model...", "progress": 0.1})

        cp_sat_start = time.time()

        try:
            # Build CP-SAT model
            model = self.cp_sat_builder.build_model(self.problem)
            variables = self.cp_sat_builder.variables

            self._notify_progress(
                {"message": "Solving for feasibility with CP-SAT...", "progress": 0.2}
            )

            # Solve for feasibility
            solve_results = self.cp_sat_solver.solve_for_feasibility(
                model,
                self.problem,
                variables,
                max_time_seconds=self.config.cp_sat.time_limit_seconds,
            )

            self.results.cp_sat_runtime = time.time() - cp_sat_start

            # Process results
            if solve_results["status"] in ["OPTIMAL", "FEASIBLE"]:
                self.results.cp_sat_solution = solve_results["solution"]
                self.results.is_feasible = True

                objective_value = solve_results.get("objective_value", float("inf"))
                logger.info(
                    f"CP-SAT found feasible solution with objective {objective_value}"
                )

                self._notify_progress(
                    {
                        "message": f"Feasible solution found (objective: {objective_value:.2f})",
                        "progress": 0.4,
                        "cp_sat_objective": objective_value,
                        "cp_sat_runtime": self.results.cp_sat_runtime,
                    }
                )

            else:
                logger.warning(
                    f"CP-SAT failed to find feasible solution: {solve_results['status']}"
                )
                self.results.is_feasible = False
                self.results.termination_reason = (
                    f"CP-SAT infeasible: {solve_results['status']}"
                )

                self._notify_progress(
                    {
                        "message": f"No feasible solution found: {solve_results['status']}",
                        "progress": 0.4,
                        "error": True,
                    }
                )

        except Exception as e:
            logger.error(f"Error in CP-SAT phase: {e}")
            self.results.cp_sat_runtime = time.time() - cp_sat_start
            self.results.is_feasible = False
            self.results.termination_reason = f"CP-SAT error: {str(e)}"
            raise

    async def _execute_ga_phase(self) -> None:
        """
        Execute GA phase for evolving variable selectors.
        Implements the second phase from the research paper.
        """
        if not self.evolution_manager or not self.problem:
            raise ValueError("Evolution manager or problem not set for GA phase")

        logger.info("Executing GA phase for variable selector evolution")
        self.current_phase = OptimizationPhase.GA_EVOLUTION

        self._notify_progress(
            {"message": "Initializing genetic algorithm population...", "progress": 0.5}
        )

        ga_start = time.time()

        try:
            # Initialize evolution manager with CP-SAT solution
            assert self.results.cp_sat_solution is not None
            await self.evolution_manager.initialize(
                cp_sat_solution=self.results.cp_sat_solution
            )

            self._notify_progress(
                {"message": "Evolving variable selectors...", "progress": 0.6}
            )

            # Run evolution
            evolution_result = await self.evolution_manager.evolve()

            # Update results
            self.results.best_solution = evolution_result.best_solution
            self.results.best_chromosome = evolution_result.best_chromosome
            self.results.generations_executed = evolution_result.total_generations
            self.results.ga_solution = evolution_result.best_solution
            self.results.ga_runtime = time.time() - ga_start

            logger.info(
                f"GA phase completed with {evolution_result.total_generations} generations"
            )

        except Exception as e:
            logger.error(f"Error in GA phase: {e}")
            self.results.ga_runtime = time.time() - ga_start
            raise

    def _create_initial_population(self) -> Population:
        """
        Create initial population for GA.
        Seeds population with information from CP-SAT solution.
        """
        population_size = self.config.genetic_algorithm.population_size
        population = Population(max_size=population_size)

        # Create diverse initial population
        for i in range(population_size):
            if i == 0 and self.results.cp_sat_solution and self.problem:
                # First individual based on CP-SAT solution success patterns
                chromosome = self._create_chromosome_from_solution(
                    self.results.cp_sat_solution
                )
            else:
                # Random individuals
                assert self.problem is not None
                chromosome = VariableSelectorChromosome.create_random(
                    self.problem,
                    max_tree_depth=self.config.genetic_algorithm.max_tree_depth,
                )

            population.add_individual(chromosome)

        logger.debug(f"Created initial population of {population_size} individuals")
        return population

    def _create_chromosome_from_solution(
        self, solution: TimetableSolution
    ) -> VariableSelectorChromosome:
        """Create chromosome that favors patterns from successful CP-SAT solution"""
        # This would analyze the CP-SAT solution to create biased initial chromosomes
        # For now, create a random chromosome (full implementation would be more sophisticated)
        assert self.problem is not None
        return VariableSelectorChromosome.create_random(
            self.problem, max_tree_depth=self.config.genetic_algorithm.max_tree_depth
        )

    async def _finalize_optimization(self) -> None:
        """Finalize optimization and prepare results"""
        if not self.problem:
            raise ValueError("Problem not set for finalization")

        logger.info("Finalizing optimization results")
        self.current_phase = OptimizationPhase.FINALIZATION

        # Determine best solution
        if not self.results.best_solution:
            self.results.best_solution = self.results.cp_sat_solution

        # Calculate final metrics
        if self.results.best_solution:
            quality_score = self.metrics.evaluate_solution_quality(
                self.problem, self.results.best_solution
            )
            self.results.solution_quality = quality_score
            self.results.final_objective_value = (
                self.results.best_solution.objective_value
            )
            self.results.final_fitness_score = self.results.best_solution.fitness_score

            # Update solution status
            if self.results.best_solution.is_feasible():
                if self.results.best_solution == self.results.cp_sat_solution:
                    self.results.best_solution.status = SolutionStatus.FEASIBLE
                else:
                    self.results.best_solution.status = SolutionStatus.OPTIMAL

        self._notify_progress(
            {
                "message": "Optimization completed",
                "progress": 1.0,
                "final_objective": self.results.final_objective_value,
                "total_runtime": self.results.total_runtime,
                "is_feasible": self.results.is_feasible,
            }
        )

        logger.info(
            f"Optimization finalized - Objective: {self.results.final_objective_value}"
        )

    def get_optimization_statistics(self) -> Dict[str, Any]:
        """Get comprehensive optimization statistics"""
        return {
            "optimization_id": str(self.optimization_id),
            "problem_size": {
                "exams": len(self.problem.exams) if self.problem else 0,
                "rooms": len(self.problem.rooms) if self.problem else 0,
                "time_slots": len(self.problem.time_slots) if self.problem else 0,
            },
            "performance": {
                "total_runtime": self.results.total_runtime,
                "cp_sat_runtime": self.results.cp_sat_runtime,
                "ga_runtime": self.results.ga_runtime,
                "phases_completed": self.current_phase.value,
            },
            "solution_quality": {
                "final_objective": self.results.final_objective_value,
                "final_fitness": self.results.final_fitness_score,
                "is_feasible": self.results.is_feasible,
                "is_optimal": self.results.is_optimal,
            },
            "evolution_statistics": {
                "generations_executed": self.results.generations_executed,
                "solutions_evaluated": self.results.solutions_evaluated,
            },
            "termination": {
                "terminated_early": self.results.terminated_early,
                "termination_reason": self.results.termination_reason,
            },
        }

    def export_best_variable_selector(self) -> Optional[Dict[str, Any]]:
        """Export the best evolved variable selector for reuse"""
        if not self.results.best_chromosome:
            return None

        return {
            "chromosome_id": str(self.results.best_chromosome.id),
            "fitness": self.results.best_chromosome.fitness,
            "objective_value": self.results.best_chromosome.objective_value,
            "tree_representation": self.results.best_chromosome.to_dict(),
            "optimization_context": {
                "problem_size": len(self.problem.exams) if self.problem else 0,
                "generation": self.results.best_chromosome.generation,
                "evolution_runtime": self.results.ga_runtime,
            },
        }

    async def apply_manual_edit(
        self, edit_request: Dict[str, Any]
    ) -> OptimizationResults:
        """
        Apply manual edit to solution and re-optimize locally.
        Implements incremental optimization capability.
        """
        logger.info("Applying manual edit and re-optimizing")

        if not self.results.best_solution:
            raise ValueError("No solution available for editing")

        # Apply edit to current best solution - this is a placeholder
        # In a real implementation, you would modify the solution based on the edit_request
        _ = self.results.best_solution.copy()

        # Re-run local optimization around the edit
        # This might use a limited CP-SAT solve or local GA search

        # For now, return current results (full implementation would be more complex)
        return self.results

    def validate_problem_for_optimization(
        self, problem: ExamSchedulingProblem
    ) -> Dict[str, List[str]]:
        """Validate problem instance before optimization"""
        errors = []
        warnings = []

        # Basic problem validation
        # Removed call to non-existent validate_problem_instance method

        # Optimization-specific validation
        if len(problem.exams) > 1000:
            warnings.append("Large problem size may require extended runtime")

        if len(problem.time_slots) < len(problem.exams) / 10:
            warnings.append("Limited time slots may make problem difficult to solve")

        # Check for GP terminal availability
        sample_exam = next(iter(problem.exams.values())) if problem.exams else None
        if sample_exam:
            try:
                terminals = problem.extract_gp_terminals(sample_exam.id)
                if not terminals:
                    errors.append("Cannot extract GP terminals for exams")
            except Exception as e:
                errors.append(f"GP terminal extraction failed: {e}")

        return {"errors": errors, "warnings": warnings}


# Factory function for easy instantiation
def create_hybrid_coordinator(
    config: Optional[SchedulingEngineConfig] = None,
) -> HybridCoordinator:
    """Create and configure a hybrid coordinator instance"""
    return HybridCoordinator(config)
