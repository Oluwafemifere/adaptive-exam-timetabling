# scheduling_engine/genetic_algorithm/operators/selection.py

"""
Selection Operators for Genetic Algorithm.

Implements tournament selection and other selection strategies for exam scheduling optimization.
Based on Nguyen et al. 2024 research paper with tournament selection size of 5.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import random
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
import math

from ...core.problem_model import ExamSchedulingProblem
from ..chromosome import VariableSelectorChromosome as Chromosome

logger = logging.getLogger(__name__)


@dataclass
class SelectionConfig:
    """Configuration for selection operations"""

    tournament_size: int = 5  # As specified in research paper
    elite_proportion: float = 0.1
    diversity_preservation: bool = True
    fitness_sharing: bool = True
    pressure_factor: float = 1.2
    selection_strategy: str = "tournament"


class SelectionOperator(ABC):
    """Abstract base class for selection operators"""

    def __init__(self, config: SelectionConfig):
        self.config = config
        self.generation_count = 0
        self.selection_statistics: Dict[str, List[Any]] = defaultdict(list)

    @abstractmethod
    def select(
        self,
        population: List[Chromosome],
        num_parents: int,
        problem: ExamSchedulingProblem,
    ) -> List[Chromosome]:
        """Select parents from population"""
        raise NotImplementedError

    def survivor_selection(
        self,
        current_population: List[Chromosome],
        offspring: List[Chromosome],
        target_size: int,
        problem: ExamSchedulingProblem,
    ) -> List[Chromosome]:
        """Select survivors for next generation"""
        try:
            combined_population = current_population + offspring

            # Ensure all chromosomes have fitness calculated
            for chromosome in combined_population:
                if chromosome.fitness is None:
                    # fitness should be calculated elsewhere before selection
                    # keep as-is to avoid silent calculation here
                    chromosome.fitness = 0.0

            # Sort by fitness (higher is better)
            combined_population.sort(key=lambda c: c.fitness or 0.0, reverse=True)

            # Elite selection
            elite_count = int(target_size * self.config.elite_proportion)
            survivors: List[Chromosome] = combined_population[:elite_count]

            # Simple selection for remaining slots
            remaining_slots = target_size - elite_count
            if remaining_slots > 0:
                remaining_candidates = combined_population[elite_count:]
                survivors.extend(remaining_candidates[:remaining_slots])

            logger.debug(
                f"Survivor selection: {len(survivors)} selected from {len(combined_population)}"
            )
            return survivors[:target_size]

        except Exception as e:
            logger.error(f"Error in survivor selection: {e}")
            return current_population[:target_size]


class TournamentSelection(SelectionOperator):
    """
    Tournament selection operator.

    Implements tournament selection with configurable tournament size
    as specified in Nguyen et al. 2024 research paper (size = 5).
    """

    def select(
        self,
        population: List[Chromosome],
        num_parents: int,
        problem: ExamSchedulingProblem,
    ) -> List[Chromosome]:
        """Select parents using tournament selection"""
        try:
            if not population:
                return []

            parents: List[Chromosome] = []

            for _ in range(num_parents):
                # Select tournament participants
                tournament_size = min(self.config.tournament_size, len(population))
                tournament_participants = random.sample(population, tournament_size)

                # Find best participant in tournament
                best_participant = max(
                    tournament_participants,
                    key=lambda c: self._calculate_selection_fitness(c, problem),
                )

                parents.append(best_participant.copy())

            logger.debug(
                f"Tournament selection completed: {num_parents} parents selected"
            )
            return parents

        except Exception as e:
            logger.error(f"Tournament selection failed: {e}")
            return population[:num_parents] if population else []

    def _calculate_selection_fitness(
        self, chromosome: Chromosome, problem: ExamSchedulingProblem
    ) -> float:
        """Calculate fitness for selection purposes"""
        try:
            base_fitness = float(chromosome.fitness or 0.0)

            # Apply pressure factor
            adjusted_fitness = base_fitness * float(self.config.pressure_factor)

            return adjusted_fitness

        except Exception as e:
            logger.error(f"Error calculating selection fitness: {e}")
            return 0.0


class RouletteWheelSelection(SelectionOperator):
    """
    Roulette wheel (fitness proportional) selection operator.

    Selects individuals with probability proportional to their fitness.
    """

    def select(
        self,
        population: List[Chromosome],
        num_parents: int,
        problem: ExamSchedulingProblem,
    ) -> List[Chromosome]:
        """Select parents using roulette wheel selection"""
        try:
            if not population:
                return []

            # Calculate selection probabilities
            fitness_values = [float(c.fitness or 0.0) for c in population]
            min_fitness = min(fitness_values) if fitness_values else 0.0

            # Shift fitness values to be positive
            adjusted_fitness = [f - min_fitness + 0.1 for f in fitness_values]
            total_fitness = sum(adjusted_fitness)

            if total_fitness == 0:
                # Fallback to uniform selection
                k = min(num_parents, len(population))
                return [chrom.copy() for chrom in random.sample(population, k)]

            probabilities = [f / total_fitness for f in adjusted_fitness]

            # Select parents
            parents: List[Chromosome] = []
            for _ in range(num_parents):
                # Roulette wheel spin
                spin = random.random()
                cumulative_probability = 0.0

                for i, prob in enumerate(probabilities):
                    cumulative_probability += prob
                    if spin <= cumulative_probability:
                        parents.append(population[i].copy())
                        break
                else:
                    # Fallback if floating point errors occur
                    parents.append(random.choice(population).copy())

            logger.debug(
                f"Roulette wheel selection completed: {num_parents} parents selected"
            )
            return parents

        except Exception as e:
            logger.error(f"Roulette wheel selection failed: {e}")
            return population[:num_parents] if population else []


class RankSelection(SelectionOperator):
    """
    Rank-based selection operator.

    Selects individuals based on their rank in the population
    rather than absolute fitness values.
    """

    def __init__(self, config: SelectionConfig, pressure: float = 1.5):
        super().__init__(config)
        self.pressure = pressure  # Selection pressure (1.0-2.0)

    def select(
        self,
        population: List[Chromosome],
        num_parents: int,
        problem: ExamSchedulingProblem,
    ) -> List[Chromosome]:
        """Select parents using rank-based selection"""
        try:
            if not population:
                return []

            # Sort population by fitness (ascending for ranking)
            sorted_population = sorted(
                population, key=lambda c: float(c.fitness or 0.0)
            )

            # Calculate rank-based probabilities
            n = len(sorted_population)
            probabilities: List[float] = []

            for rank in range(n):
                # Linear ranking selection probability
                if n == 1:
                    prob = 1.0
                else:
                    prob = (
                        2 - self.pressure + 2 * (self.pressure - 1) * rank / (n - 1)
                    ) / n
                probabilities.append(prob)

            # Select parents
            parents: List[Chromosome] = []
            for _ in range(num_parents):
                # Random selection based on rank probabilities
                rand = random.random()
                cumulative_prob = 0.0

                for i, prob in enumerate(probabilities):
                    cumulative_prob += prob
                    if rand <= cumulative_prob:
                        parents.append(sorted_population[i].copy())
                        break
                else:
                    # Fallback
                    parents.append(random.choice(sorted_population).copy())

            logger.debug(f"Rank selection completed: {num_parents} parents selected")
            return parents

        except Exception as e:
            logger.error(f"Rank selection failed: {e}")
            return population[:num_parents] if population else []


class StochasticUniversalSampling(SelectionOperator):
    """
    Stochastic Universal Sampling (SUS) selection operator.

    Provides more uniform sampling compared to roulette wheel selection
    by using evenly spaced pointers.
    """

    def select(
        self,
        population: List[Chromosome],
        num_parents: int,
        problem: ExamSchedulingProblem,
    ) -> List[Chromosome]:
        """Select parents using stochastic universal sampling"""
        try:
            if not population:
                return []

            # Calculate fitness values
            fitness_values = [float(c.fitness or 0.0) for c in population]
            min_fitness = min(fitness_values) if fitness_values else 0.0

            # Shift to positive values
            adjusted_fitness = [f - min_fitness + 0.1 for f in fitness_values]
            total_fitness = sum(adjusted_fitness)

            if total_fitness == 0:
                k = min(num_parents, len(population))
                return [chrom.copy() for chrom in random.sample(population, k)]

            # Calculate pointer spacing
            pointer_distance = total_fitness / num_parents
            start_point = random.uniform(0, pointer_distance)

            # Generate pointers
            pointers = [start_point + i * pointer_distance for i in range(num_parents)]

            # Select individuals
            parents: List[Chromosome] = []
            cumulative_fitness = 0.0
            population_index = 0

            for pointer in pointers:
                # Find individual at pointer position
                while (
                    population_index < len(population)
                    and cumulative_fitness + adjusted_fitness[population_index]
                    < pointer
                ):
                    cumulative_fitness += adjusted_fitness[population_index]
                    population_index += 1

                selected_index = min(population_index, len(population) - 1)
                parents.append(population[selected_index].copy())

            logger.debug(f"SUS selection completed: {len(parents)} parents selected")
            return parents

        except Exception as e:
            logger.error(f"SUS selection failed: {e}")
            return population[:num_parents] if population else []


class EliteSelection(SelectionOperator):
    """
    Elite selection operator.

    Always selects the best individuals from the population
    based on fitness values.
    """

    def select(
        self,
        population: List[Chromosome],
        num_parents: int,
        problem: ExamSchedulingProblem,
    ) -> List[Chromosome]:
        """Select parents using elite selection"""
        try:
            if not population:
                return []

            # Sort by fitness (descending)
            sorted_population = sorted(
                population, key=lambda c: float(c.fitness or 0.0), reverse=True
            )

            # Select top individuals
            selected_count = min(num_parents, len(sorted_population))
            parents = [chrom.copy() for chrom in sorted_population[:selected_count]]

            logger.debug(
                f"Elite selection completed: {selected_count} parents selected"
            )
            return parents

        except Exception as e:
            logger.error(f"Elite selection failed: {e}")
            return population[:num_parents] if population else []


class FitnessProportionalSelection(SelectionOperator):
    """
    Fitness proportional selection operator.

    Enhanced roulette wheel selection with windowing and scaling.
    """

    def __init__(self, config: SelectionConfig, scaling_method: str = "linear"):
        super().__init__(config)
        self.scaling_method = scaling_method

    def select(
        self,
        population: List[Chromosome],
        num_parents: int,
        problem: ExamSchedulingProblem,
    ) -> List[Chromosome]:
        """Select parents using fitness proportional selection"""
        try:
            if not population:
                return []

            # Apply fitness scaling
            scaled_fitness = self._scale_fitness_values(population)

            # Perform selection
            parents: List[Chromosome] = []
            for _ in range(num_parents):
                selected = self._weighted_random_selection(population, scaled_fitness)
                parents.append(selected.copy())

            logger.debug(
                f"Fitness proportional selection completed: {len(parents)} parents selected"
            )
            return parents

        except Exception as e:
            logger.error(f"Fitness proportional selection failed: {e}")
            return population[:num_parents] if population else []

    def _scale_fitness_values(self, population: List[Chromosome]) -> List[float]:
        """Scale fitness values using specified scaling method"""
        try:
            raw_fitness = [float(c.fitness or 0.0) for c in population]

            if self.scaling_method == "linear":
                # Linear scaling
                min_fit = min(raw_fitness) if raw_fitness else 0.0
                max_fit = max(raw_fitness) if raw_fitness else 0.0

                if max_fit == min_fit:
                    return [1.0] * len(raw_fitness)

                # Scale to [0.5, 2.0] range
                scaled: List[float] = []
                for f in raw_fitness:
                    scaled_f = 0.5 + 1.5 * (f - min_fit) / (max_fit - min_fit)
                    scaled.append(scaled_f)

                return scaled

            elif self.scaling_method == "exponential":
                # Exponential scaling
                return [math.exp(f) for f in raw_fitness]

            elif self.scaling_method == "power":
                # Power scaling
                power = 2.0
                return [f**power for f in raw_fitness]

            else:
                # No scaling
                return raw_fitness

        except Exception as e:
            logger.error(f"Error scaling fitness values: {e}")
            return [1.0] * len(population)

    def _weighted_random_selection(
        self, population: List[Chromosome], weights: List[float]
    ) -> Chromosome:
        """Perform weighted random selection"""
        try:
            total_weight = sum(weights)

            if total_weight == 0:
                return random.choice(population)

            # Normalize weights
            probabilities = [w / total_weight for w in weights]

            # Random selection
            rand = random.random()
            cumulative_prob = 0.0

            for i, prob in enumerate(probabilities):
                cumulative_prob += prob
                if rand <= cumulative_prob:
                    return population[i]

            # Fallback
            return population[-1]

        except Exception as e:
            logger.error(f"Error in weighted random selection: {e}")
            return random.choice(population)


class AdaptiveSelection(SelectionOperator):
    """
    Adaptive selection operator.

    Dynamically selects appropriate selection strategy based on
    population characteristics and evolutionary progress.
    """

    def __init__(self, config: SelectionConfig):
        super().__init__(config)
        self.tournament_selection = TournamentSelection(config)
        self.roulette_selection = RouletteWheelSelection(config)
        self.rank_selection = RankSelection(config)
        self.elite_selection = EliteSelection(config)

        # Adaptive tracking
        self.strategy_performance: Dict[str, List[float]] = defaultdict(list)
        self.population_diversity_history: List[float] = []

    def select(
        self,
        population: List[Chromosome],
        num_parents: int,
        problem: ExamSchedulingProblem,
    ) -> List[Chromosome]:
        """Perform adaptive selection"""
        try:
            if not population:
                return []

            # Simple default strategy for now
            strategy = "tournament"

            # Apply selected strategy
            if strategy == "tournament":
                parents = self.tournament_selection.select(
                    population, num_parents, problem
                )
            elif strategy == "roulette":
                parents = self.roulette_selection.select(
                    population, num_parents, problem
                )
            elif strategy == "rank":
                parents = self.rank_selection.select(population, num_parents, problem)
            elif strategy == "elite":
                parents = self.elite_selection.select(population, num_parents, problem)
            else:
                # Default to tournament
                parents = self.tournament_selection.select(
                    population, num_parents, problem
                )

            logger.debug(f"Adaptive selection used strategy: {strategy}")
            return parents

        except Exception as e:
            logger.error(f"Adaptive selection failed: {e}")
            return population[:num_parents] if population else []


class MultiObjectiveSelection(SelectionOperator):
    """
    Multi-objective selection operator.

    Considers multiple objectives (fitness, constraint violations, diversity)
    in selection decisions using weighted aggregation or Pareto ranking.
    """

    def __init__(
        self,
        config: SelectionConfig,
        objective_weights: Optional[Dict[str, float]] = None,
    ):
        super().__init__(config)
        self.objective_weights = objective_weights or {"fitness": 0.6, "diversity": 0.1}

    def select(
        self,
        population: List[Chromosome],
        num_parents: int,
        problem: ExamSchedulingProblem,
    ) -> List[Chromosome]:
        """Select parents using multi-objective selection"""
        try:
            if not population:
                return []

            # Calculate multi-objective scores
            multi_objective_scores: List[tuple] = []

            for chromosome in population:
                # Calculate multi-objective score
                score = self._calculate_multi_objective_score(
                    chromosome, population, problem
                )
                multi_objective_scores.append((score, chromosome))

            # Sort by multi-objective score
            multi_objective_scores.sort(key=lambda x: x[0], reverse=True)

            # Select top individuals
            selected_count = min(num_parents, len(multi_objective_scores))
            parents = [
                chrom.copy() for score, chrom in multi_objective_scores[:selected_count]
            ]

            logger.debug(
                f"Multi-objective selection completed: {selected_count} parents selected"
            )
            return parents

        except Exception as e:
            logger.error(f"Multi-objective selection failed: {e}")
            return population[:num_parents] if population else []

    def _calculate_multi_objective_score(
        self,
        chromosome: Chromosome,
        population: List[Chromosome],
        problem: ExamSchedulingProblem,
    ) -> float:
        """Calculate multi-objective score for chromosome"""
        try:
            # Fitness component
            fitness_component = float(
                chromosome.fitness or 0.0
            ) * self.objective_weights.get("fitness", 0.6)

            # Diversity component
            diversity_score = 0.5  # Placeholder
            diversity_component = diversity_score * self.objective_weights.get(
                "diversity", 0.1
            )

            # Combined score
            total_score = fitness_component + diversity_component

            return total_score

        except Exception as e:
            logger.error(f"Error calculating multi-objective score: {e}")
            return 0.0


class HybridSelection(SelectionOperator):
    """
    Hybrid selection operator.

    Combines multiple selection strategies to leverage benefits of each approach.
    Uses tournament selection for exploitation and roulette wheel for exploration.
    """

    def __init__(self, config: SelectionConfig, exploration_ratio: float = 0.3):
        super().__init__(config)
        self.exploration_ratio = exploration_ratio
        self.tournament_selection = TournamentSelection(config)
        self.roulette_selection = RouletteWheelSelection(config)
        self.elite_selection = EliteSelection(config)

    def select(
        self,
        population: List[Chromosome],
        num_parents: int,
        problem: ExamSchedulingProblem,
    ) -> List[Chromosome]:
        """Select parents using hybrid selection"""
        try:
            if not population:
                return []

            parents: List[Chromosome] = []

            # Elite selection for top performers
            elite_count = max(1, int(num_parents * 0.1))
            elite_parents = self.elite_selection.select(
                population, elite_count, problem
            )
            parents.extend(elite_parents)

            # Tournament selection for exploitation
            exploitation_count = int(
                (num_parents - elite_count) * (1 - self.exploration_ratio)
            )
            if exploitation_count > 0:
                tournament_parents = self.tournament_selection.select(
                    population, exploitation_count, problem
                )
                parents.extend(tournament_parents)

            # Roulette wheel selection for exploration
            exploration_count = num_parents - len(parents)
            if exploration_count > 0:
                exploration_parents = self.roulette_selection.select(
                    population, exploration_count, problem
                )
                parents.extend(exploration_parents)

            # Shuffle to avoid bias in genetic operations
            random.shuffle(parents)

            logger.debug(
                f"Hybrid selection: {elite_count} elite, {exploitation_count} exploitation, {exploration_count} exploration"
            )
            return parents[:num_parents]

        except Exception as e:
            logger.error(f"Hybrid selection failed: {e}")
            return population[:num_parents] if population else []


# Selection operator factory
class SelectionOperatorFactory:
    """Factory for creating selection operators"""

    @staticmethod
    def create_operator(
        operator_type: str, config: SelectionConfig, **kwargs
    ) -> SelectionOperator:
        """Create selection operator of specified type"""
        operators = {
            "tournament": TournamentSelection,
            "roulette": RouletteWheelSelection,
            "rank": RankSelection,
            "sus": StochasticUniversalSampling,
            "elite": EliteSelection,
            "fitness_proportional": FitnessProportionalSelection,
            "multi_objective": MultiObjectiveSelection,
            "adaptive": AdaptiveSelection,
            "hybrid": HybridSelection,
        }

        operator_class = operators.get(operator_type)
        if operator_class:
            return operator_class(config, **kwargs)
        else:
            logger.warning(
                f"Unknown selection operator: {operator_type}, using tournament"
            )
            return TournamentSelection(config)

    @staticmethod
    def get_recommended_operator(
        population_diversity: float,
        fitness_variance: float,
        constraint_violations: int,
        generation_number: int = 0,
    ) -> str:
        """Get recommended selection operator based on current state"""
        try:
            # Placeholder heuristic; can be extended with performance history
            if constraint_violations > 0:
                return "fitness_proportional"
            if population_diversity < 0.1:
                return "reservoir" if False else "rank"
            if fitness_variance > 1.0:
                return "tournament"
            return "tournament"

        except Exception as e:
            logger.error(f"Error getting recommended selection operator: {e}")
            return "tournament"


# Utility functions for selection operations
class SelectionUtils:
    """Utility functions for selection operations"""

    @staticmethod
    def calculate_selection_pressure(
        population: List[Chromosome],
        selected: List[Chromosome],
        problem: ExamSchedulingProblem,
    ) -> float:
        """Calculate selection pressure"""
        try:
            # Calculate mean fitness of population vs selected
            pop_fitness = [float(c.fitness or 0.0) for c in population]
            sel_fitness = [float(c.fitness or 0.0) for c in selected]

            if not pop_fitness or not sel_fitness:
                return 1.0

            pop_mean = sum(pop_fitness) / len(pop_fitness)
            sel_mean = sum(sel_fitness) / len(sel_fitness)

            if pop_mean == 0:
                return 1.0

            pressure = sel_mean / pop_mean
            return pressure

        except Exception as e:
            logger.error(f"Error calculating selection pressure: {e}")
            return 1.0

    @staticmethod
    def validate_selection_quality(
        population: List[Chromosome],
        selected: List[Chromosome],
        problem: ExamSchedulingProblem,
    ) -> Dict[str, Any]:
        """Validate quality of selection"""
        try:
            warnings: List[str] = []
            metrics: Dict[str, Any] = {}
            validation: Dict[str, Any] = {
                "is_valid": True,
                "warnings": warnings,
                "metrics": metrics,
                "quality_maintained": True,
            }

            # Check that selected individuals exist in population
            population_ids = {id(c) for c in population}

            valid_selection = all(id(c) in population_ids for c in selected)
            validation["is_valid"] = valid_selection

            if not valid_selection:
                warnings.append("Some selected individuals not from population")

            # Calculate selection pressure
            pressure = SelectionUtils.calculate_selection_pressure(
                population, selected, problem
            )
            metrics["selection_pressure"] = pressure

            if pressure > 3.0:
                warnings.append("Very high selection pressure detected")
            elif pressure < 0.5:
                warnings.append("Very low selection pressure detected")

            return validation

        except Exception as e:
            logger.error(f"Error validating selection quality: {e}")
            return {"is_valid": False, "warnings": [f"Validation error: {str(e)}"]}
