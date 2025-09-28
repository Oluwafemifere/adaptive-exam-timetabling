"""

DEAP-Integrated Evolution Manager for constraint-aware genetic algorithm.

FIXED: Resolved DEAP fitness.valid property issue and -inf fitness values

"""

import logging
import sys
import time
from typing import Dict, List, Optional, Any, Tuple, Callable, Union
from dataclasses import dataclass
import random
import numpy as np

from deap import base
from .chromosome import DEAPIndividual, ChromosomeEncoder, ChromosomeDecoder
from .population import DEAPPopulation, DEAPPopulationManager
from .operators import (
    ConstraintAwareCrossover,
    ConstraintAwareMutation,
    ConstraintAwareSelection,
    create_constraint_aware_toolbox,
    create_conservative_operators,
    create_explorative_operators,
    create_balanced_operators,
)
from .fitness import create_single_objective_evaluator, create_multi_objective_evaluator
from .types import safe_fitness_value

logger = logging.getLogger(__name__)


@dataclass
class ConstraintAwareGAParameters:
    population_size: int = 50
    max_generations: int = 100
    pruning_aggressiveness: float = 0.2
    constraint_pressure: float = 0.3
    min_feasible_ratio: float = 0.3
    critical_constraint_weight: float = 0.3
    selection_method: str = "constraint_aware"
    tournament_size: int = 3
    elite_ratio: float = 0.1
    crossover_method: str = "constraint_aware"
    crossover_prob: float = 0.8
    crossover_alpha: float = 0.3
    mutation_method: str = "constraint_aware"
    mutation_prob: float = 0.2
    mutation_sigma: float = 0.1
    multi_objective: bool = False
    use_nsga2: bool = False
    adaptive_operators: bool = True
    convergence_threshold: float = 0.001
    diversity_threshold: float = 0.1
    constraint_violation_tolerance: int = 5
    critical_constraint_tolerance: int = 0
    feasibility_pressure_adaptation: bool = True
    safe_pruning_ratio: float = 0.3


@dataclass
class ConstraintAwareEvolutionReport:
    success: bool = False
    best_individual: Optional[DEAPIndividual] = None
    final_population: Optional[DEAPPopulation] = None
    generations_run: int = 0
    total_evaluations: int = 0
    total_time: float = 0.0
    convergence_generation: Optional[int] = None
    best_fitness: float = 0.0
    average_fitness: float = 0.0
    fitness_improvement: float = 0.0
    final_constraint_violations: int = 0
    final_critical_violations: int = 0
    final_feasibility_rate: float = 0.0
    constraint_satisfaction_rate: float = 0.0
    feasible_solutions_found: int = 0
    variables_pruned: int = 0
    pruning_efficiency: float = 0.0
    search_hints_generated: int = 0
    hint_quality_score: float = 0.0
    pareto_front_size: int = 0
    hypervolume: float = 0.0
    error_message: Optional[str] = None


def ensure_list(obj: Any) -> List[Any]:
    """Safely convert any object to a list."""
    if obj is None:
        return []
    if isinstance(obj, list):
        return obj

    try:
        if hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes)):
            return list(obj)
        else:
            return [obj]
    except Exception:
        return [obj]


def iter_individuals(pop: Any) -> List[DEAPIndividual]:
    """Safely extract individuals from population-like objects."""
    if pop is None:
        return []

    # Try to get individuals attribute first
    inds = getattr(pop, "individuals", None)
    if inds is not None:
        try:
            result = list(inds) if not isinstance(inds, list) else inds
            return [ind for ind in result if isinstance(ind, DEAPIndividual)]
        except Exception:
            return []

    # Try direct iteration if it's iterable and not a string/bytes
    try:
        if hasattr(pop, "__iter__") and not isinstance(pop, (str, bytes)):
            result = list(pop)
            return [ind for ind in result if isinstance(ind, DEAPIndividual)]
    except Exception:
        pass

    # If it's a single individual, wrap in list
    if isinstance(pop, DEAPIndividual):
        return [pop]

    return []


def safe_extract_fitness_value(fitness_values: Any) -> float:
    """FIXED: Safely extract a single fitness value from various types."""
    if fitness_values is None:
        return 0.0  # CRITICAL FIX: Changed from float("-inf") to 0.0

    try:
        if isinstance(fitness_values, (tuple, list)):
            if len(fitness_values) > 0:
                first_val = fitness_values[0]
                if isinstance(first_val, (int, float, np.number)):
                    return float(first_val)
                else:
                    return float(first_val)  # Try conversion
            else:
                return 0.0  # FIXED: Changed from float("-inf")
        elif isinstance(fitness_values, (int, float, np.number)):
            return float(fitness_values)
        else:
            return float(fitness_values)
    except (TypeError, ValueError):
        return 0.0  # CRITICAL FIX: Changed from float("-inf") to 0.0


class DEAPConstraintAwareEvolutionManager:
    def __init__(
        self, problem, constraint_encoder, parameters: ConstraintAwareGAParameters
    ):
        self.problem = problem
        self.constraint_encoder = constraint_encoder
        self.parameters = parameters

        self.chromosome_encoder = ChromosomeEncoder(problem, constraint_encoder)
        self.chromosome_decoder = ChromosomeDecoder(problem, constraint_encoder)
        self.population_manager = DEAPPopulationManager(
            population_size=parameters.population_size, encoder=self.chromosome_encoder
        )

        if parameters.multi_objective:
            self.fitness_evaluator = create_multi_objective_evaluator(
                problem,
                constraint_encoder,
                constraint_weights={
                    "constraint_priority": parameters.critical_constraint_weight
                },
            )
        else:
            self.fitness_evaluator = create_single_objective_evaluator(
                problem,
                constraint_encoder,
                constraint_weights={
                    "constraint_priority": parameters.critical_constraint_weight
                },
            )

        # FIX: Initialize private attribute BEFORE setting up toolbox
        self._current_operator_strategy = "balanced"  # Critical: Initialize first
        self.toolbox: Any = self.setup_deap_toolbox()

        self.current_generation = 0
        self.evolution_history: List[Dict[str, Any]] = []
        self.best_individual_ever: Optional[DEAPIndividual] = None
        self.constraint_satisfaction_history: List[float] = []
        self.operator_performance = {
            "conservative": [],
            "explorative": [],
            "balanced": [],
        }

        # Now safe to set the operator strategy
        self.current_operator_strategy = "balanced"

        logger.info(
            f"Initialized DEAP Constraint-Aware Evolution Manager with {parameters.population_size} individuals"
        )

    def setup_deap_toolbox(self) -> Any:
        """Setup DEAP toolbox with constraint-aware operators."""
        raw_toolbox = create_constraint_aware_toolbox(
            self.problem, self.constraint_encoder
        )
        toolbox_any = raw_toolbox

        if self.parameters.multi_objective:
            eval_fn: Callable = (
                lambda ind: self.fitness_evaluator.evaluate_multi_objective(ind)
            )
        else:
            eval_fn = lambda ind: self.fitness_evaluator.evaluate_single_objective(ind)

        register_fn = getattr(toolbox_any, "register", None)
        if callable(register_fn):
            register_fn("evaluate", eval_fn)
        else:
            setattr(toolbox_any, "evaluate", eval_fn)

        # FIXED: Use private attribute to avoid recursion
        self.update_toolbox_operators(toolbox_any, self._current_operator_strategy)

        return toolbox_any

    @property
    def current_operator_strategy(self) -> str:
        """Get the current operator strategy."""
        return self._current_operator_strategy

    @current_operator_strategy.setter
    def current_operator_strategy(self, value: str) -> None:
        """Set the current operator strategy."""
        self._current_operator_strategy = value
        if hasattr(self, "toolbox") and self.toolbox is not None:
            self.update_toolbox_operators(self.toolbox, value)

    def update_toolbox_operators(self, toolbox: Any, strategy: str) -> None:
        """Update toolbox operators based on strategy."""
        if strategy == "conservative":
            operators = create_conservative_operators()
        elif strategy == "explorative":
            operators = create_explorative_operators()
        else:
            operators = create_balanced_operators()

        crossover_fn = operators.get("crossover")
        mutation_fn = operators.get("mutation")
        selection_fn = operators.get("selection")

        register_fn = getattr(toolbox, "register", None)
        if callable(register_fn):
            if crossover_fn:
                register_fn("mate", crossover_fn)
            if mutation_fn:
                register_fn("mutate", mutation_fn)
            if selection_fn:
                register_fn("select", selection_fn)
        else:
            # FIX: Use the private attribute that was properly initialized
            if crossover_fn:
                setattr(toolbox, "mate", crossover_fn)
            if mutation_fn:
                setattr(toolbox, "mutate", mutation_fn)
            if selection_fn:
                setattr(toolbox, "select", selection_fn)

    def solve(
        self, max_generations: Optional[int] = None
    ) -> ConstraintAwareEvolutionReport:
        """Solve with recursion limit protection."""
        old_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(5000)
        start_time = time.time()
        max_gen = max_generations or self.parameters.max_generations

        try:
            population = self.initialize_constraint_aware_population()
            convergence_gen = None
            best_generation_fitness = 0.0  # FIXED: Changed from float("-inf")

            for generation in range(max_gen):
                self.current_generation = generation

                # Evaluate population
                self.evaluate_population_constraint_aware(population)

                # Update evolution tracking
                self.update_evolution_tracking(population)

                # Check convergence
                if self.check_constraint_aware_convergence(population):
                    convergence_gen = generation
                    break

                # Adapt operators
                if self.parameters.adaptive_operators:
                    self.adapt_operators_based_on_constraints(population, generation)

                # Create new generation
                parents = self.select_parents_constraint_aware(population)
                parents = ensure_list(parents)
                offspring = self.reproduce_constraint_aware(parents)
                offspring = ensure_list(offspring)

                # Replace population
                population = self.replace_population_constraint_aware(
                    population, offspring
                )

                # Diversity maintenance
                if generation % 5 == 0:
                    population = (
                        self.population_manager.maintain_constraint_aware_diversity(
                            population, self.parameters.diversity_threshold
                        )
                    )

                # Log statistics
                self.log_constraint_aware_statistics(population, generation)

                current_best = max(
                    [safe_fitness_value(ind) for ind in iter_individuals(population)],
                    default=0.0,  # FIXED: Changed from float("-inf")
                )

                if current_best > best_generation_fitness:
                    best_generation_fitness = current_best

            total_time = time.time() - start_time

            report = self.generate_constraint_aware_report(
                population, max_gen, total_time, convergence_gen
            )

            return report

        except RecursionError as e:
            logger.error(f"Recursion error in GA evolution: {e}")
            return ConstraintAwareEvolutionReport(
                success=False,
                error_message=f"Recursion error: {str(e)}",
                total_time=time.time() - start_time,
            )
        except Exception as e:
            logger.exception("Evolution failed")
            return ConstraintAwareEvolutionReport(
                success=False, error_message=str(e), total_time=time.time() - start_time
            )
        finally:
            sys.setrecursionlimit(old_limit)

    def initialize_constraint_aware_population(self) -> DEAPPopulation:
        population = self.population_manager.create_population(
            random_ratio=0.3, constraint_aware_ratio=0.5
        )

        for individual in iter_individuals(population):
            setattr(individual, "generation_created", 0)

        return population

    def evaluate_population_constraint_aware(self, population: DEAPPopulation):
        toolbox_any = getattr(self, "toolbox", None)
        evaluate_fn = getattr(toolbox_any, "evaluate", None)

        invalid_ind = [
            ind
            for ind in iter_individuals(population)
            if not getattr(ind, "fitness", None) or not ind.fitness.valid
        ]

        if callable(evaluate_fn):
            fitnesses = [evaluate_fn(ind) for ind in invalid_ind]
            for ind, fit in zip(invalid_ind, fitnesses):
                self.safe_assign_fitness_values(ind, fit)
        else:
            try:
                individuals_list = list(iter_individuals(population))
                self.fitness_evaluator.evaluate_population(individuals_list)
            except Exception:
                pass

        try:
            population.update_hall_of_fame(k=10)
        except Exception:
            pass

        feasible_individuals = ensure_list(
            getattr(population, "get_feasible", lambda: [])()
        )

        if feasible_individuals:
            best_feasible = max(feasible_individuals, key=safe_fitness_value)
            update_best = False

            if self.best_individual_ever is None:
                update_best = True
            else:
                best_ever_val = safe_fitness_value(self.best_individual_ever)
                best_feasible_val = safe_fitness_value(best_feasible)

                best_ever_float = safe_extract_fitness_value(best_ever_val)
                best_feasible_float = safe_extract_fitness_value(best_feasible_val)

                if (
                    getattr(
                        self.best_individual_ever, "critical_constraint_violations", 1
                    )
                    > 0
                ):
                    update_best = True
                elif best_feasible_float > best_ever_float:
                    update_best = True

            if update_best:
                try:
                    self.best_individual_ever = best_feasible.copy()
                except Exception:
                    self.best_individual_ever = best_feasible

        elif not self.best_individual_ever:
            try:
                best_in_pop = ensure_list(
                    getattr(population, "get_best", lambda n=1: [])()
                )
                if best_in_pop:
                    self.best_individual_ever = best_in_pop[0].copy()
            except Exception:
                pass

    @staticmethod
    def safe_assign_fitness_values(
        individual: DEAPIndividual, fitness_values: Any
    ) -> None:
        """FIXED: Safely assign fitness values with proper type conversion."""
        if individual is None:
            return

        try:
            if isinstance(fitness_values, (tuple, list)):
                # FIXED: Convert all values to floats and create a tuple
                float_values = tuple(
                    safe_extract_fitness_value(x) for x in fitness_values
                )
                individual.fitness.values = float_values
                # FIXED: Remove manual setting of valid - DEAP manages this automatically
            else:
                # Handle single value
                float_value = safe_extract_fitness_value(fitness_values)
                individual.fitness.values = (float_value,)
                # FIXED: Remove manual setting of valid - DEAP manages this automatically

        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to assign fitness values: {e}")
            individual.fitness.values = (0.0,)  # FIXED: Changed from -inf
            # FIXED: Remove manual setting of valid - DEAP manages this automatically

    def select_parents_constraint_aware(
        self, population: DEAPPopulation
    ) -> List[DEAPIndividual]:
        toolbox_any = getattr(self, "toolbox", None)
        select_fn = getattr(toolbox_any, "select", None)

        individuals = list(iter_individuals(population))

        if callable(select_fn):
            selected = select_fn(individuals, self.parameters.population_size)
        else:
            constraint_selection = ConstraintAwareSelection(
                constraint_pressure=self.parameters.constraint_pressure
            )
            selected = constraint_selection(
                individuals, self.parameters.population_size
            )

        return ensure_list(selected)

    def reproduce_constraint_aware(
        self, parents: List[DEAPIndividual]
    ) -> List[DEAPIndividual]:
        offspring: List[DEAPIndividual] = []
        random.shuffle(parents)

        toolbox_any = getattr(self, "toolbox", None)
        mate_fn = getattr(toolbox_any, "mate", None)
        mutate_fn = getattr(toolbox_any, "mutate", None)

        for i in range(0, max(0, len(parents) - 1), 2):
            parent1 = parents[i]
            parent2 = parents[i + 1] if i + 1 < len(parents) else parents[0]

            if random.random() < self.parameters.crossover_prob:
                if callable(mate_fn):
                    child1, child2 = mate_fn(
                        parent1, parent2
                    )  # pyright: ignore[reportGeneralTypeIssues]
                else:
                    crossover = ConstraintAwareCrossover()
                    child1, child2 = crossover(parent1, parent2)
            else:
                child1, child2 = parent1.copy(), parent2.copy()

            # FIXED: Reset fitness for children - DEAP way
            del child1.fitness.values
            del child2.fitness.values

            if random.random() < self.parameters.mutation_prob:
                if callable(mutate_fn):
                    mutated = mutate_fn(child1)
                    child1 = (
                        mutated[0]
                        if isinstance(mutated, (tuple, list)) and len(mutated) > 0
                        else child1
                    )
                else:
                    mutation = ConstraintAwareMutation()
                    mutated = mutation(child1)
                    child1 = (
                        mutated[0]
                        if isinstance(mutated, (tuple, list)) and len(mutated) > 0
                        else child1
                    )

            if random.random() < self.parameters.mutation_prob:
                if callable(mutate_fn):
                    mutated = mutate_fn(child2)
                    child2 = (
                        mutated[0]
                        if isinstance(mutated, (tuple, list)) and len(mutated) > 0
                        else child2
                    )
                else:
                    mutation = ConstraintAwareMutation()
                    mutated = mutation(child2)
                    child2 = (
                        mutated[0]
                        if isinstance(mutated, (tuple, list)) and len(mutated) > 0
                        else child2
                    )

            setattr(child1, "generation_created", self.current_generation + 1)
            setattr(child2, "generation_created", self.current_generation + 1)

            offspring.extend([child1, child2])

        return offspring

    def replace_population_constraint_aware(
        self, current_population: DEAPPopulation, offspring: List[DEAPIndividual]
    ) -> DEAPPopulation:
        # Filter offspring to ensure they are DEAPIndividual instances
        valid_offspring = [
            ind
            for ind in offspring
            if isinstance(ind, DEAPIndividual) and hasattr(ind, "fitness")
        ]

        if len(valid_offspring) < len(offspring):
            logger.warning(
                f"Filtered {len(offspring) - len(valid_offspring)} invalid individuals from offspring"
            )

        return self.population_manager.replace_population_constraint_aware(
            current_population, valid_offspring, strategy="constraint_elitist"
        )

    def check_constraint_aware_convergence(self, population: DEAPPopulation) -> bool:
        return self.population_manager.detect_constraint_aware_convergence(
            population, self.parameters.convergence_threshold, generations_to_check=10
        )

    def adapt_operators_based_on_constraints(
        self, population: DEAPPopulation, generation: int
    ):
        if not self.parameters.adaptive_operators:
            return

        stats = population.calculate_statistics()
        constraint_trends = population.get_constraint_trends()

        if stats.constraint_satisfaction_rate < 0.5:
            new_strategy = "conservative"
        elif stats.feasibility_rate > 0.8 and stats.average_diversity < 0.1:
            new_strategy = "explorative"
        elif constraint_trends.get("violation_trend", 0) > 0:
            new_strategy = "conservative"
        else:
            new_strategy = "balanced"

        if new_strategy != self.current_operator_strategy:
            self.current_operator_strategy = new_strategy

            self.operator_performance.setdefault(new_strategy, []).append(
                getattr(stats, "best_fitness", 0.0)
            )

    def update_evolution_tracking(self, population: DEAPPopulation):
        stats = population.calculate_statistics()

        generation_record = {
            "generation": self.current_generation,
            "best_fitness": stats.best_fitness,
            "average_fitness": stats.average_fitness,
            "worst_fitness": stats.worst_fitness,
            "diversity": stats.average_diversity,
            "feasibility_rate": stats.feasibility_rate,
            "constraint_satisfaction_rate": stats.constraint_satisfaction_rate,
            "constraint_violations": stats.constraint_violations,
            "critical_constraint_violations": stats.critical_constraint_violations,
            "pruning_efficiency": getattr(stats, "pruning_efficiency", 0.0),
            "convergence_metric": getattr(stats, "convergence_metric", 0.0),
        }

        self.evolution_history.append(generation_record)
        self.constraint_satisfaction_history.append(stats.constraint_satisfaction_rate)

        try:
            self.population_manager.update_generation_history(population)
        except Exception:
            pass

    def log_constraint_aware_statistics(
        self, population: DEAPPopulation, generation: int
    ):
        stats = population.calculate_statistics()

        # CRITICAL FIX: Ensure no -inf values in logging
        best_fitness = (
            max(0.0, stats.best_fitness) if stats.best_fitness != float("-inf") else 0.0
        )

        logger.info(
            f"Gen {generation + 1} | Fitness={best_fitness:.4f}, "
            f"Feasibility={stats.feasibility_rate:.1%}, "
            f"ConstraintSat={stats.constraint_satisfaction_rate:.1%}, "
            f"Violations={stats.constraint_violations}, "
            f"Critical={stats.critical_constraint_violations}, "
            f"Diversity={stats.average_diversity:.3f}"
        )

        if (generation + 1) % 10 == 0:
            eval_stats = self.fitness_evaluator.get_evaluation_statistics()
            constraint_insights = self.population_manager.get_constraint_insights()

            logger.info(
                f"Evaluation stats: {eval_stats.get('total_evaluations', 0)} evals, "
                f"avg_time={eval_stats.get('average_time_per_evaluation', 0.0):.2f}s"
            )

            logger.info(
                f"Constraint insights: trend={constraint_insights.get('constraint_satisfaction_trend', 0):.3f}, "
                f"best_feasibility={constraint_insights.get('best_feasibility_rate', 0):.1%}"
            )

    def generate_constraint_aware_report(
        self,
        final_population: DEAPPopulation,
        generations_run: int,
        total_time: float,
        convergence_generation: Optional[int],
    ) -> ConstraintAwareEvolutionReport:
        feasible_individuals = ensure_list(
            getattr(final_population, "get_feasible", lambda: [])()
        )

        if feasible_individuals:
            best_individual = max(feasible_individuals, key=safe_fitness_value)
        else:
            try:
                best_candidates = ensure_list(
                    getattr(final_population, "get_best", lambda n=1: [])()
                )
                best_individual = best_candidates[0] if best_candidates else None
            except Exception:
                best_individual = None

        if self.best_individual_ever and best_individual:
            best_now_val = safe_fitness_value(best_individual)
            best_ever_val = safe_fitness_value(self.best_individual_ever)

            best_now_float = safe_extract_fitness_value(best_now_val)
            best_ever_float = safe_extract_fitness_value(best_ever_val)

            if (
                getattr(best_individual, "critical_constraint_violations", 1) == 0
                or best_ever_float < best_now_float
            ):
                best_individual = self.best_individual_ever

        initial_fitness = (
            self.evolution_history[0]["best_fitness"] if self.evolution_history else 0.0
        )

        final_fitness = safe_fitness_value(best_individual)
        final_fitness_float = safe_extract_fitness_value(final_fitness)

        fitness_improvement = final_fitness_float - initial_fitness

        final_stats = (
            final_population.calculate_statistics() if final_population else None
        )

        feasible_solutions_found = sum(
            1
            for record in self.evolution_history
            if record.get("feasibility_rate", 0) > 0
        )

        search_hints = []
        variables_pruned = 0
        hint_quality = 0.0

        if best_individual:
            try:
                hints_result = self.chromosome_decoder.decode_to_search_hints(
                    best_individual
                )

                if hints_result is None:
                    search_hints = []
                elif hasattr(hints_result, "__iter__") and not isinstance(
                    hints_result, (str, bytes)
                ):
                    search_hints = list(hints_result)
                else:
                    search_hints = [hints_result]
            except Exception:
                search_hints = []

            pruning_decisions = getattr(best_individual, "pruning_decisions", None)
            if pruning_decisions and hasattr(pruning_decisions, "get_total_pruned"):
                try:
                    variables_pruned = pruning_decisions.get_total_pruned()
                except Exception:
                    variables_pruned = 0

            hint_quality = self.calculate_hint_quality(search_hints)

        eval_stats = self.fitness_evaluator.get_evaluation_statistics()

        report = ConstraintAwareEvolutionReport(
            success=True,
            best_individual=best_individual,
            final_population=final_population,
            generations_run=generations_run,
            total_evaluations=eval_stats.get("total_evaluations", 0),
            total_time=total_time,
            convergence_generation=convergence_generation,
            best_fitness=final_fitness_float,
            average_fitness=final_stats.average_fitness if final_stats else 0.0,
            fitness_improvement=fitness_improvement,
            final_constraint_violations=(
                final_stats.constraint_violations if final_stats else 0
            ),
            final_critical_violations=(
                final_stats.critical_constraint_violations if final_stats else 0
            ),
            final_feasibility_rate=final_stats.feasibility_rate if final_stats else 0.0,
            constraint_satisfaction_rate=(
                final_stats.constraint_satisfaction_rate if final_stats else 0.0
            ),
            feasible_solutions_found=feasible_solutions_found,
            variables_pruned=variables_pruned,
            pruning_efficiency=(
                getattr(best_individual, "pruning_efficiency", 0.0)
                if best_individual
                else 0.0
            ),
            search_hints_generated=len(search_hints),
            hint_quality_score=hint_quality,
            pareto_front_size=0,
            hypervolume=0.0,
        )

        return report

    def calculate_hint_quality(self, search_hints: List[Any]) -> float:
        if not search_hints:
            return 0.0

        confidences = []
        for hint in search_hints:
            if isinstance(hint, (list, tuple)) and len(hint) >= 3:
                confidence = hint[2]
                if isinstance(confidence, (int, float)):
                    confidences.append(confidence)

        if not confidences:
            return 0.0

        avg_confidence = np.mean(confidences)
        high_conf_ratio = len([c for c in confidences if c > 0.7]) / len(confidences)

        return float(0.6 * avg_confidence + 0.4 * high_conf_ratio)

    def get_constraint_aware_solver_hints(self) -> List[Tuple[Any, int, float]]:
        """Get search hints from best individual for CP-SAT solver."""
        if not self.best_individual_ever:
            logger.warning("No best individual available for hint generation")
            return []

        try:
            hints_result = self.chromosome_decoder.decode_to_search_hints(
                self.best_individual_ever
            )

            if hints_result is None:
                hints = []
            elif hasattr(hints_result, "__iter__") and not isinstance(
                hints_result, (str, bytes)
            ):
                hints = list(hints_result)
            else:
                hints = [hints_result]

            formatted_hints = []
            for hint in hints[:50]:  # Top 50 hints
                if isinstance(hint, (list, tuple)) and len(hint) >= 3:
                    var_key, value, confidence = hint[0], hint[1], hint[2]

                    bool_value = (
                        1 if value > 0.5 else 0  # pyright: ignore[reportOperatorIssue]
                    )  # pyright: ignore[reportOperatorIssue]

                    formatted_hints.append(
                        (
                            var_key,
                            bool_value,
                            float(confidence),  # pyright: ignore[reportArgumentType]
                        )  # pyright: ignore[reportArgumentType]
                    )  # pyright: ignore[reportArgumentType] # pyright: ignore[reportArgumentType]

            logger.info(
                f"Generated {len(formatted_hints)} formatted search hints for CP-SAT"
            )

            return formatted_hints

        except Exception as e:
            logger.error(f"Error generating search hints: {e}")
            return []

    def get_constraint_aware_pruning_decisions(self) -> Optional[Any]:
        """Get constraint-aware pruning decisions from best individual."""
        if not self.best_individual_ever:
            logger.warning("No best individual available for pruning decisions")
            return None

        pruning = getattr(
            self.chromosome_decoder, "decode_to_pruning_decisions", lambda x: None
        )(self.best_individual_ever)

        if pruning and hasattr(pruning, "get_total_pruned"):
            try:
                total = pruning.get_total_pruned()
            except Exception:
                total = None
        else:
            total = None

        logger.info(
            f"Generated constraint-aware pruning decisions: {total} variables to prune safely"
        )

        return pruning

    def get_constraint_performance_metrics(self) -> Dict[str, Any]:
        eval_stats = self.fitness_evaluator.get_evaluation_statistics()
        constraint_insights = self.population_manager.get_constraint_insights()

        metrics = {
            "evolution_history": self.evolution_history,
            "evaluation_statistics": eval_stats,
            "constraint_satisfaction_history": self.constraint_satisfaction_history,
            "constraint_insights": constraint_insights,
            "best_individual_fitness": safe_fitness_value(self.best_individual_ever),
            "best_individual_violations": (
                getattr(self.best_individual_ever, "constraint_violations", 0)
                if self.best_individual_ever
                else 0
            ),
            "best_individual_critical_violations": (
                getattr(self.best_individual_ever, "critical_constraint_violations", 0)
                if self.best_individual_ever
                else 0
            ),
            "operator_performance": self.operator_performance,
            "total_generations_run": self.current_generation,
        }

        return metrics


def create_constraint_aware_ga(
    problem, constraint_encoder, **kwargs
) -> DEAPConstraintAwareEvolutionManager:
    default_params = {
        "population_size": 50,
        "max_generations": 100,
        "pruning_aggressiveness": 0.2,
        "constraint_pressure": 0.3,
        "min_feasible_ratio": 0.3,
        "critical_constraint_weight": 0.3,
        "adaptive_operators": True,
        "multi_objective": False,
        "constraint_violation_tolerance": 5,
        "critical_constraint_tolerance": 0,
        "feasibility_pressure_adaptation": True,
    }

    default_params.update(kwargs)
    parameters = ConstraintAwareGAParameters(**default_params)

    ga = DEAPConstraintAwareEvolutionManager(problem, constraint_encoder, parameters)

    return ga
