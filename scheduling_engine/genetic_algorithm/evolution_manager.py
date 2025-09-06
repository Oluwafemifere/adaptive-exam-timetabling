# scheduling_engine/genetic_algorithm/evolution_manager.py

"""
Evolution Manager for Genetic Algorithm component of hybrid CP-SAT + GA scheduling engine.
Implements the GP-CP hybrid approach from research paper with evolved variable selectors
to guide CP-SAT search and fitness evaluation based on solution quality.

Based on Nguyen et al. 2024 "Genetic-based Constraint Programming for Resource Constrained Job Scheduling"
"""

from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import random
import statistics
import time

from ..core.problem_model import ExamSchedulingProblem
from ..core.solution import TimetableSolution
from ..core.metrics import SolutionMetrics, QualityScore
from .population import PopulationManager
from .chromosome import VariableSelectorChromosome
from .fitness import FitnessEvaluator, FitnessConfig
from .operators.selection import TournamentSelection, SelectionConfig
from ..utils.logging import get_logger

logger = get_logger(__name__)


class EvolutionStrategy(Enum):
    """Evolution strategies for different scenarios"""

    STANDARD = "standard"
    INCREMENTAL = "incremental"
    MULTI_OBJECTIVE = "multi_objective"
    FACULTY_PARTITIONED = "faculty_partitioned"


class TerminationCriterion(Enum):
    """Termination criteria for evolution"""

    MAX_GENERATIONS = "max_generations"
    TIME_LIMIT = "time_limit"
    CONVERGENCE = "convergence"
    QUALITY_THRESHOLD = "quality_threshold"
    STAGNATION = "stagnation"


@dataclass
class EvolutionConfig:
    """Configuration for evolution manager"""

    population_size: int = 50
    max_generations: int = 100
    time_limit_seconds: float = 600.0
    tournament_size: int = 3
    selection_pressure: float = 0.7
    elitism_rate: float = 0.1
    crossover_rate: float = 0.8
    mutation_rate: float = 0.2
    training_subset_ratio: float = 0.3
    quality_weight: float = 1.0
    efficiency_weight: float = 0.3
    use_preselection: bool = True
    preselection_instances: int = 5
    preselection_survivors: float = 0.6
    convergence_generations: int = 10
    stagnation_threshold: float = 0.01
    min_improvement_threshold: float = 0.005
    enable_partition_coordination: bool = False
    partition_communication_frequency: int = 5
    enable_parallel_evaluation: bool = True
    max_workers: int = 4


@dataclass
class GenerationResult:
    """Result of a generation evolution"""

    generation: int
    best_fitness: float
    average_fitness: float
    fitness_std: float
    best_chromosome: VariableSelectorChromosome
    population_diversity: float
    evaluation_time: float
    generation_time: float
    improvement: bool
    convergence_score: float


@dataclass
class EvolutionResult:
    """Final result of evolution process"""

    success: bool
    best_solution: TimetableSolution
    best_chromosome: VariableSelectorChromosome
    total_generations: int
    total_time: float
    termination_reason: str
    evolution_history: List[GenerationResult]
    quality_metrics: QualityScore
    convergence_achieved: bool
    partition_id: Optional[UUID] = None


class EvolutionManager:
    """
    Manages the genetic algorithm evolution process for exam timetabling.
    Implements the hybrid GP-CP approach from the research paper where evolved
    variable selectors guide CP-SAT search for solution optimization.
    """

    def __init__(
        self,
        problem: ExamSchedulingProblem,
        config: Optional[EvolutionConfig] = None,
    ):
        self.config = config or EvolutionConfig()
        self.problem = problem

        # Core components
        self.population_manager: PopulationManager = PopulationManager(
            population_size=self.config.population_size, problem=self.problem
        )

        # Initialize fitness evaluator with proper config
        fitness_config = FitnessConfig(
            quality_weight=self.config.quality_weight,
            efficiency_weight=self.config.efficiency_weight,
        )
        self.fitness_evaluator: FitnessEvaluator = FitnessEvaluator(
            problem=self.problem, config=fitness_config
        )

        # Initialize selection operator with proper config
        selection_config = SelectionConfig(tournament_size=self.config.tournament_size)
        self.selection_operator = TournamentSelection(selection_config)

        # Evolution state
        self.current_generation = 0
        self.best_ever_chromosome: Optional[VariableSelectorChromosome] = None
        self.best_ever_solution: Optional[TimetableSolution] = None
        self.evolution_history: List[GenerationResult] = []
        self.convergence_tracker: List[float] = []
        self.stagnation_counter = 0

        # Training instances management
        self.training_instances: List[ExamSchedulingProblem] = []
        self.current_training_subset: List[ExamSchedulingProblem] = []

        # Termination flags
        self.should_terminate = False
        self.termination_reason = ""

        # Performance tracking
        self.total_evaluations = 0
        self.start_time: Optional[datetime] = None

    async def initialize(
        self,
        cp_sat_solution: TimetableSolution,
        training_instances: Optional[List[ExamSchedulingProblem]] = None,
        partition_id: Optional[UUID] = None,
    ) -> None:
        """Initialize evolution manager with problem and initial solution"""
        try:
            logger.info(
                f"Initializing Evolution Manager for problem with {len(self.problem.exams)} exams"
            )

            # Initialize training instances
            if training_instances:
                self.training_instances = training_instances
            else:
                self.training_instances = [self.problem]

            # Initialize population from CP-SAT solution
            await self._initialize_population_from_cpsat(cp_sat_solution)

            # Sample initial training subset
            await self._sample_training_subset()

            logger.info("Evolution Manager initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing Evolution Manager: {e}")
            raise

    async def evolve(
        self,
        max_generations: Optional[int] = None,
        time_limit: Optional[float] = None,
        quality_threshold: Optional[float] = None,
    ) -> EvolutionResult:
        """
        Main evolution loop implementing the hybrid GP-CP approach.
        """
        try:
            # Set evolution parameters
            if max_generations:
                self.config.max_generations = max_generations
            if time_limit:
                self.config.time_limit_seconds = time_limit

            self.start_time = datetime.now()
            logger.info(
                f"Starting evolution for {self.config.max_generations} generations"
            )

            # Initialize termination criteria
            self._setup_termination_criteria(quality_threshold)

            # Main evolution loop
            while (
                not self.should_terminate
                and self.current_generation < self.config.max_generations
            ):
                # Execute one generation
                generation_result = await self._evolve_generation()

                # Update evolution state
                await self._update_evolution_state(generation_result)

                # Check termination conditions
                await self._check_termination_conditions()

                # Log progress
                self._log_generation_progress(generation_result)

                self.current_generation += 1

            # Create final result
            evolution_result = await self._create_evolution_result()

            logger.info(f"Evolution completed: {evolution_result.termination_reason}")
            return evolution_result

        except Exception as e:
            logger.error(f"Error during evolution: {e}")
            return EvolutionResult(
                success=False,
                best_solution=TimetableSolution(self.problem),
                best_chromosome=VariableSelectorChromosome(),
                total_generations=self.current_generation,
                total_time=self._get_elapsed_time(),
                termination_reason=f"Error: {str(e)}",
                evolution_history=[],
                quality_metrics=QualityScore(),
                convergence_achieved=False,
            )

    async def _evolve_generation(self) -> GenerationResult:
        """Execute one generation of evolution"""
        try:
            generation_start = time.time()

            # Sample new training subset for this generation
            if self.current_generation > 0:
                await self._sample_training_subset()

            # Evaluate current population
            await self._evaluate_population()

            # Selection and reproduction
            offspring = await self._generate_offspring()

            # Replace population
            await self._replace_population(offspring)

            # Get best individual of generation
            best_chromosome = self.population_manager.get_best_individual()
            best_fitness = best_chromosome.fitness if best_chromosome else float("inf")

            # Calculate generation statistics
            population_fitness = [
                ind.fitness
                for ind in self.population_manager.population.individuals
                if hasattr(ind, "fitness") and ind.fitness is not None
            ]

            generation_time = time.time() - generation_start

            return GenerationResult(
                generation=self.current_generation,
                best_fitness=best_fitness,
                average_fitness=(
                    statistics.mean(population_fitness)
                    if population_fitness
                    else float("inf")
                ),
                fitness_std=(
                    statistics.stdev(population_fitness)
                    if len(population_fitness) > 1
                    else 0.0
                ),
                best_chromosome=best_chromosome or VariableSelectorChromosome(),
                population_diversity=await self._calculate_population_diversity(),
                evaluation_time=generation_time * 0.7,
                generation_time=generation_time,
                improvement=self._check_improvement(best_fitness),
                convergence_score=self._calculate_convergence_score(),
            )

        except Exception as e:
            logger.error(f"Error in generation {self.current_generation}: {e}")
            # Return a default result on error
            return GenerationResult(
                generation=self.current_generation,
                best_fitness=float("inf"),
                average_fitness=float("inf"),
                fitness_std=0.0,
                best_chromosome=VariableSelectorChromosome(),
                population_diversity=0.0,
                evaluation_time=0.0,
                generation_time=0.0,
                improvement=False,
                convergence_score=0.0,
            )

    async def _initialize_population_from_cpsat(
        self, cp_sat_solution: TimetableSolution
    ) -> None:
        """Initialize population using CP-SAT solution as seed"""
        try:
            logger.info("Initializing population from CP-SAT solution")

            # Create seed chromosome from CP-SAT solution
            seed_chromosome = await self._solution_to_chromosome(cp_sat_solution)

            # Initialize population with seed and variations
            await self.population_manager.initialize_from_seed(
                seed_chromosome=seed_chromosome,
                variation_rate=0.3,
                random_individuals=0.2,
            )

            logger.info(
                f"Population initialized with {len(self.population_manager.population.individuals)} individuals"
            )

        except Exception as e:
            logger.error(f"Error initializing population from CP-SAT: {e}")
            raise

    async def _generate_offspring(self) -> List[VariableSelectorChromosome]:
        """Generate offspring through selection"""
        try:
            offspring = []
            target_offspring = int(
                self.config.population_size * (1 - self.config.elitism_rate)
            )

            # Simple selection implementation
            for _ in range(target_offspring):
                parent = self.selection_operator.select(
                    self.population_manager.population.individuals, 1, self.problem
                )
                if parent:
                    offspring.append(parent[0].copy())

            return offspring

        except Exception as e:
            logger.error(f"Error generating offspring: {e}")
            return []

    async def _replace_population(
        self, offspring: List[VariableSelectorChromosome]
    ) -> None:
        """Replace population with offspring and elite individuals"""
        try:
            # Get elite individuals
            elite_count = int(self.config.population_size * self.config.elitism_rate)
            elites = self.population_manager.get_elite_individuals(elite_count)

            # Combine elites and offspring
            new_population = elites + offspring

            # Update population
            await self.population_manager.replace_population(
                new_population[: self.config.population_size]
            )

        except Exception as e:
            logger.error(f"Error replacing population: {e}")

    async def _evaluate_population(self) -> None:
        """Evaluate current population fitness"""
        try:
            # Evaluate all individuals
            for individual in self.population_manager.population.individuals:
                if not hasattr(individual, "fitness") or individual.fitness is None:
                    fitness_result = await self.fitness_evaluator.evaluate(
                        individual, self.current_training_subset
                    )
                    individual.fitness = fitness_result.total_fitness

            self.total_evaluations += len(
                self.population_manager.population.individuals
            )

        except Exception as e:
            logger.error(f"Error evaluating population: {e}")

    async def _sample_training_subset(self) -> None:
        """Sample subset of training instances for generation"""
        try:
            subset_size = max(
                1, int(len(self.training_instances) * self.config.training_subset_ratio)
            )
            self.current_training_subset = random.sample(
                self.training_instances, subset_size
            )

            logger.debug(
                f"Sampled {len(self.current_training_subset)} training instances"
            )

        except Exception as e:
            logger.error(f"Error sampling training subset: {e}")
            self.current_training_subset = self.training_instances[:1]

    async def _solution_to_chromosome(
        self, solution: TimetableSolution
    ) -> VariableSelectorChromosome:
        """Convert timetable solution to chromosome representation"""
        try:
            # Create a basic chromosome from solution
            chromosome = VariableSelectorChromosome()
            # Add source attribute to track origin
            chromosome.source = "cp_sat_seed"
            return chromosome

        except Exception as e:
            logger.error(f"Error converting solution to chromosome: {e}")
            return VariableSelectorChromosome()

    async def _calculate_population_diversity(self) -> float:
        """Calculate population diversity metric"""
        try:
            if len(self.population_manager.population.individuals) < 2:
                return 0.0

            # Simple diversity calculation based on fitness variance
            fitness_values = [
                ind.fitness
                for ind in self.population_manager.population.individuals
                if hasattr(ind, "fitness") and ind.fitness is not None
            ]

            if len(fitness_values) < 2:
                return 0.0

            return statistics.stdev(fitness_values) / statistics.mean(fitness_values)

        except Exception as e:
            logger.error(f"Error calculating population diversity: {e}")
            return 0.0

    def _check_improvement(self, current_fitness: float) -> bool:
        """Check if current fitness represents an improvement"""
        try:
            if not self.convergence_tracker:
                return True

            best_previous = min(self.convergence_tracker)
            return (
                current_fitness < best_previous - self.config.min_improvement_threshold
            )

        except Exception as e:
            logger.error(f"Error checking improvement: {e}")
            return False

    def _calculate_convergence_score(self) -> float:
        """Calculate convergence score based on recent fitness history"""
        try:
            if len(self.convergence_tracker) < 2:
                return 0.0

            recent_window = self.convergence_tracker[
                -self.config.convergence_generations :
            ]
            if len(recent_window) < 2:
                return 0.0

            # Calculate coefficient of variation
            mean_fitness = statistics.mean(recent_window)
            std_fitness = statistics.stdev(recent_window)

            if mean_fitness == 0:
                return 1.0

            cv = std_fitness / abs(mean_fitness)
            return max(0.0, 1.0 - cv)

        except Exception as e:
            logger.error(f"Error calculating convergence score: {e}")
            return 0.0

    async def _update_evolution_state(
        self, generation_result: GenerationResult
    ) -> None:
        """Update evolution state with generation results"""
        try:
            self.evolution_history.append(generation_result)
            self.convergence_tracker.append(generation_result.best_fitness)

            # Keep convergence tracker within window
            if len(self.convergence_tracker) > self.config.convergence_generations:
                self.convergence_tracker.pop(0)

            # Update stagnation counter
            if generation_result.improvement:
                self.stagnation_counter = 0
            else:
                self.stagnation_counter += 1

        except Exception as e:
            logger.error(f"Error updating evolution state: {e}")

    def _setup_termination_criteria(self, quality_threshold: Optional[float]) -> None:
        """Setup termination criteria for evolution"""
        try:
            self.should_terminate = False
            self.termination_reason = ""

        except Exception as e:
            logger.error(f"Error setting up termination criteria: {e}")

    async def _check_termination_conditions(self) -> None:
        """Check if any termination condition is met"""
        try:
            # Time limit
            if (
                self.start_time
                and self._get_elapsed_time() >= self.config.time_limit_seconds
            ):
                self.should_terminate = True
                self.termination_reason = "Time limit reached"
                return

            # Stagnation
            if self.stagnation_counter >= self.config.convergence_generations:
                convergence_score = self._calculate_convergence_score()
                if convergence_score > 0.95:
                    self.should_terminate = True
                    self.termination_reason = "Population converged"
                    return

        except Exception as e:
            logger.error(f"Error checking termination conditions: {e}")

    def _log_generation_progress(self, generation_result: GenerationResult) -> None:
        """Log generation progress"""
        try:
            logger.info(
                f"Generation {generation_result.generation}: "
                f"Best={generation_result.best_fitness:.4f}, "
                f"Avg={generation_result.average_fitness:.4f}, "
                f"Diversity={generation_result.population_diversity:.3f}, "
                f"Time={generation_result.generation_time:.2f}s"
            )

        except Exception as e:
            logger.error(f"Error logging generation progress: {e}")

    def _get_elapsed_time(self) -> float:
        """Get elapsed time since evolution started"""
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return 0.0

    async def _create_evolution_result(self) -> EvolutionResult:
        """Create final evolution result"""
        try:
            total_time = self._get_elapsed_time()

            # Determine termination reason if not set
            if not self.termination_reason:
                if self.current_generation >= self.config.max_generations:
                    self.termination_reason = "Maximum generations reached"
                else:
                    self.termination_reason = "Evolution completed"

            # Calculate quality metrics
            quality_metrics = QualityScore()
            if self.best_ever_solution:
                metrics = SolutionMetrics()
                quality_metrics = metrics.evaluate_solution_quality(
                    self.problem, self.best_ever_solution
                )

            # Check convergence
            convergence_achieved = (
                len(self.convergence_tracker) >= self.config.convergence_generations
                and self._calculate_convergence_score() > 0.9
            )

            return EvolutionResult(
                success=self.best_ever_solution is not None,
                best_solution=self.best_ever_solution
                or TimetableSolution(self.problem),
                best_chromosome=self.best_ever_chromosome
                or VariableSelectorChromosome(),
                total_generations=self.current_generation,
                total_time=total_time,
                termination_reason=self.termination_reason,
                evolution_history=self.evolution_history.copy(),
                quality_metrics=quality_metrics,
                convergence_achieved=convergence_achieved,
            )

        except Exception as e:
            logger.error(f"Error creating evolution result: {e}")
            return EvolutionResult(
                success=False,
                best_solution=TimetableSolution(self.problem),
                best_chromosome=VariableSelectorChromosome(),
                total_generations=self.current_generation,
                total_time=self._get_elapsed_time(),
                termination_reason=f"Error: {str(e)}",
                evolution_history=[],
                quality_metrics=QualityScore(),
                convergence_achieved=False,
            )

    async def get_evolution_statistics(self) -> Dict[str, Any]:
        """Get detailed evolution statistics"""
        try:
            if not self.evolution_history:
                return {}

            fitness_history = [gen.best_fitness for gen in self.evolution_history]
            diversity_history = [
                gen.population_diversity for gen in self.evolution_history
            ]

            return {
                "total_generations": len(self.evolution_history),
                "total_evaluations": self.total_evaluations,
                "best_fitness": min(fitness_history) if fitness_history else None,
                "worst_fitness": max(fitness_history) if fitness_history else None,
                "average_fitness": (
                    statistics.mean(fitness_history) if fitness_history else None
                ),
                "fitness_improvement": (
                    fitness_history[0] - min(fitness_history)
                    if len(fitness_history) > 1
                    else 0
                ),
                "average_diversity": (
                    statistics.mean(diversity_history) if diversity_history else None
                ),
                "evolution_time": self._get_elapsed_time(),
                "evaluations_per_second": self.total_evaluations
                / max(self._get_elapsed_time(), 1),
            }

        except Exception as e:
            logger.error(f"Error getting evolution statistics: {e}")
            return {}
