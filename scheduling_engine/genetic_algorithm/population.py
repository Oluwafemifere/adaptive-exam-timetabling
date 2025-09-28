# FIXED Population Module - Statistics Issues Resolved
"""
Safe Population Module - DEAP-Integrated population management without circular imports.
This module fixes circular import issues and implements constraint-aware population
management that works with the safe chromosome and operator implementations.

FIXED Issues:
- Fixed statistics.stdev() error with proper variance calculation
- Safe statistics calculations that work with Python 3.13
- Proper handling of empty fitness lists
"""

import logging
import random
from typing import List, Dict, Optional, Any
import numpy as np
from dataclasses import dataclass
import math  # Use math instead of statistics for better compatibility

# Safe imports - no circular dependencies
from .deap_setup import is_deap_available
from .types import PopulationStatistics, safe_fitness_value

# Import for type checking only
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .chromosome import DEAPIndividual, ChromosomeEncoder

logger = logging.getLogger(__name__)


def safe_std_deviation(values: List[float]) -> float:
    """Calculate standard deviation safely without using statistics.stdev()."""
    if len(values) <= 1:
        return 0.0

    try:
        mean_val = sum(values) / len(values)
        variance = sum((x - mean_val) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)
    except (ZeroDivisionError, ValueError):
        return 0.0


def safe_variance(values: List[float]) -> float:
    """Calculate variance safely without using statistics.variance()."""
    if len(values) <= 1:
        return 0.0

    try:
        mean_val = sum(values) / len(values)
        variance = sum((x - mean_val) ** 2 for x in values) / (len(values) - 1)
        return variance
    except (ZeroDivisionError, ValueError):
        return 0.0


class DEAPPopulation:
    """
    FIXED DEAP-compatible population container with constraint-aware operations.

    Fixes:
    - No circular imports
    - Safe individual management
    - Constraint-aware population operations
    - Memory-efficient processing
    """

    def __init__(self, individuals: Optional[List["DEAPIndividual"]] = None):
        self.individuals = individuals or []
        self.generation = 0
        self.statistics = None

        # DEAP-compatible containers (safe initialization)
        if is_deap_available():
            try:
                from deap import tools

                self.hall_of_fame = tools.HallOfFame(10)
                self.logbook = tools.Logbook()
            except ImportError:
                self.hall_of_fame = None
                self.logbook = None
        else:
            self.hall_of_fame = None
            self.logbook = None

        # Constraint-aware tracking
        self.constraint_history = []
        self.critical_constraint_history = []
        self.feasibility_history = []

    def __len__(self) -> int:
        return len(self.individuals)

    def __iter__(self):
        return iter(self.individuals)

    def __getitem__(self, index):
        return self.individuals[index]

    def __setitem__(self, index, value):
        self.individuals[index] = value

    def append(self, individual: "DEAPIndividual"):
        """Add an individual to the population."""
        self.individuals.append(individual)

    def extend(self, individuals: List["DEAPIndividual"]):
        """Add multiple individuals to the population."""
        self.individuals.extend(individuals)

    def get_best(self, n: int = 1) -> List["DEAPIndividual"]:
        """Get the n best individuals by constraint-aware fitness."""
        if not self.individuals:
            return []

        # Priority: fewer critical violations, fewer regular violations, higher fitness
        def sort_key(x):
            critical_violations = getattr(x, "critical_constraint_violations", 0)
            regular_violations = getattr(x, "constraint_violations", 0)
            fitness_value = safe_fitness_value(x)

            # Sort by constraint priority first, then by fitness
            return (critical_violations, regular_violations, -fitness_value)

        sorted_individuals = sorted(self.individuals, key=sort_key)
        return sorted_individuals[:n]

    def get_feasible(self) -> List["DEAPIndividual"]:
        """Get all feasible individuals (no critical constraint violations)."""
        return [
            ind
            for ind in self.individuals
            if getattr(ind, "critical_constraint_violations", 0) == 0
        ]

    def get_constraint_violators(self) -> List["DEAPIndividual"]:
        """Get individuals with constraint violations."""
        return [
            ind
            for ind in self.individuals
            if getattr(ind, "constraint_violations", 0) > 0
        ]

    def calculate_statistics(self) -> PopulationStatistics:
        """Calculate comprehensive population statistics with constraint awareness."""
        if not self.individuals:
            return PopulationStatistics(
                generation=self.generation,
                size=0,
                best_fitness=0.0,
                average_fitness=0.0,
                worst_fitness=0.0,
                fitness_variance=0.0,
                average_diversity=0.0,
                constraint_violations=0,
                critical_constraint_violations=0,
                feasibility_rate=0.0,
                convergence_metric=0.0,
                constraint_satisfaction_rate=0.0,
                pruning_efficiency=0.0,
            )

        # Extract fitness values and constraint metrics
        fitness_values = []
        total_violations = 0
        total_critical_violations = 0
        feasible_count = 0
        pruning_efficiencies = []

        for ind in self.individuals:
            fitness_val = safe_fitness_value(ind)
            fitness_values.append(fitness_val)

            violations = getattr(ind, "constraint_violations", 0)
            critical_violations = getattr(ind, "critical_constraint_violations", 0)

            total_violations += violations
            total_critical_violations += critical_violations

            if violations == 0:
                feasible_count += 1

            pruning_efficiency = getattr(ind, "pruning_efficiency", 0.0)
            pruning_efficiencies.append(pruning_efficiency)

        if not fitness_values:
            fitness_values = [0.0]

        # Calculate diversity (sample for efficiency)
        diversity_sum = 0.0
        diversity_count = 0
        sample_size = min(20, len(self.individuals))
        if sample_size > 1:
            sample_indices = random.sample(range(len(self.individuals)), sample_size)
            for i in range(sample_size):
                for j in range(i + 1, sample_size):
                    ind1 = self.individuals[sample_indices[i]]
                    ind2 = self.individuals[sample_indices[j]]
                    diversity = self._calculate_diversity_metric(ind1, ind2)
                    diversity_sum += diversity
                    diversity_count += 1

        average_diversity = (
            diversity_sum / diversity_count if diversity_count > 0 else 0.0
        )

        # Calculate convergence metric
        mean_fitness = sum(fitness_values) / len(fitness_values)
        fitness_std = safe_std_deviation(fitness_values)
        convergence_metric = fitness_std / mean_fitness if mean_fitness > 0 else 0.0

        # Constraint satisfaction rate
        total_possible_violations = (
            len(self.individuals) * 20
        )  # Assume 20 constraints per individual
        constraint_satisfaction_rate = max(
            0.0,
            1.0
            - (total_violations + total_critical_violations * 2)
            / max(1, total_possible_violations),
        )

        # Average pruning efficiency
        avg_pruning_efficiency = (
            float(np.mean(pruning_efficiencies)) if pruning_efficiencies else 0.0
        )

        self.statistics = PopulationStatistics(
            generation=self.generation,
            size=len(self.individuals),
            best_fitness=max(fitness_values),
            average_fitness=mean_fitness,
            worst_fitness=min(fitness_values),
            fitness_variance=safe_variance(fitness_values),  # FIX: Use safe variance
            average_diversity=average_diversity,
            constraint_violations=total_violations,
            critical_constraint_violations=total_critical_violations,
            feasibility_rate=feasible_count / len(self.individuals),
            convergence_metric=convergence_metric,
            constraint_satisfaction_rate=constraint_satisfaction_rate,
            pruning_efficiency=avg_pruning_efficiency,
        )

        # Track constraint history
        self.constraint_history.append(total_violations)
        self.critical_constraint_history.append(total_critical_violations)
        self.feasibility_history.append(feasible_count / len(self.individuals))

        return self.statistics

    def _calculate_diversity_metric(
        self, ind1: "DEAPIndividual", ind2: "DEAPIndividual"
    ) -> float:
        """Calculate diversity metric between two individuals."""
        try:
            return ind1.get_diversity_metric(ind2)
        except Exception:
            # Fallback calculation if method not available
            if len(ind1) != len(ind2):
                return 1.0
            try:
                diff = np.array(ind1) - np.array(ind2)
                return float(np.sqrt(np.sum(diff**2)) / len(ind1))
            except Exception:
                return 0.5

    def update_ages(self):
        """Update age of all individuals in population."""
        for individual in self.individuals:
            individual.age += 1

    def sort_by_constraint_aware_fitness(self, descending: bool = True):
        """Sort population by constraint-aware fitness criteria."""

        def sort_key(x):
            if not x.fitness.valid:
                return (
                    float("inf"),
                    float("inf"),
                    float("-inf") if descending else float("inf"),
                )

            critical_violations = getattr(x, "critical_constraint_violations", 0)
            regular_violations = getattr(x, "constraint_violations", 0)
            fitness = safe_fitness_value(x)

            return (
                critical_violations,
                regular_violations,
                -fitness if descending else fitness,
            )

        self.individuals.sort(key=sort_key)

    def update_hall_of_fame(self, k: int = 10):
        """Update hall of fame with best constraint-aware individuals."""
        if not self.hall_of_fame:
            return

        # Prioritize feasible individuals
        feasible_individuals = [
            ind
            for ind in self.individuals
            if getattr(ind, "critical_constraint_violations", 0) == 0
        ]

        if feasible_individuals:
            try:
                for ind in feasible_individuals:
                    self.hall_of_fame.update([ind])
            except Exception as e:
                logger.debug(f"Hall of fame update failed: {e}")
        else:
            # If no feasible individuals, use best available
            try:
                self.hall_of_fame.update(self.individuals)
            except Exception as e:
                logger.debug(f"Hall of fame update failed: {e}")

    def record_statistics(self):
        """Record generation statistics with constraint awareness."""
        if not self.logbook:
            return None

        stats = self.calculate_statistics()

        try:
            record = self.logbook.record(
                gen=self.generation,
                size=stats.size,
                min=stats.worst_fitness,
                avg=stats.average_fitness,
                max=stats.best_fitness,
                std=np.sqrt(stats.fitness_variance),
                feasibility=stats.feasibility_rate,
                diversity=stats.average_diversity,
                convergence=stats.convergence_metric,
                violations=stats.constraint_violations,
                critical_violations=stats.critical_constraint_violations,
                constraint_satisfaction=stats.constraint_satisfaction_rate,
                pruning_efficiency=stats.pruning_efficiency,
            )
            return record
        except Exception as e:
            logger.debug(f"Statistics recording failed: {e}")
            return None

    def get_constraint_trends(self, window: int = 5) -> Dict[str, float]:
        """Get recent trends in constraint satisfaction."""
        if len(self.constraint_history) < window:
            return {
                "violation_trend": 0.0,
                "feasibility_trend": 0.0,
                "critical_trend": 0.0,
            }

        recent_violations = self.constraint_history[-window:]
        recent_critical = self.critical_constraint_history[-window:]
        recent_feasibility = self.feasibility_history[-window:]

        violation_trend = (recent_violations[-1] - recent_violations[0]) / max(
            1, len(recent_violations) - 1
        )
        critical_trend = (recent_critical[-1] - recent_critical[0]) / max(
            1, len(recent_critical) - 1
        )
        feasibility_trend = (recent_feasibility[-1] - recent_feasibility[0]) / max(
            1, len(recent_feasibility) - 1
        )

        return {
            "violation_trend": violation_trend,
            "critical_trend": critical_trend,
            "feasibility_trend": feasibility_trend,
        }


class DEAPPopulationManager:
    """
    FIXED DEAP-integrated population manager with constraint-aware operations.

    Fixes:
    - No circular imports
    - Safe population initialization and management
    - Constraint-aware replacement strategies
    - Memory-efficient operations
    """

    def __init__(self, population_size: int, encoder: "ChromosomeEncoder"):
        self.population_size = population_size
        self.encoder = encoder

        # Constraint-aware parameters
        self.generation_history = []
        self.min_feasible_ratio = 0.3
        self.diversity_threshold = 0.1
        self.constraint_pressure_adaptation = True

    def create_population(
        self,
        random_ratio: float = 0.5,
        constraint_aware_ratio: float = 0.3,
    ) -> DEAPPopulation:
        """Initialize constraint-aware population with diverse strategies."""
        logger.info(
            f"Initializing DEAP constraint-aware population of size {self.population_size}"
        )

        individuals = []
        num_random = int(self.population_size * random_ratio)
        num_constraint_aware = int(self.population_size * constraint_aware_ratio)
        num_heuristic = self.population_size - num_random - num_constraint_aware

        # Create random individuals
        for i in range(num_random):
            individual = self.encoder.create_random_individual()
            individual.generation_created = 0
            individuals.append(individual)

        # Create constraint-priority individuals
        for i in range(num_constraint_aware):
            individual = self.encoder.create_heuristic_individual("constraint_priority")
            individual.generation_created = 0
            individuals.append(individual)

        # Create other heuristic individuals
        heuristic_types = [
            "difficulty_first",
            "capacity_utilization",
            "time_distribution",
        ]
        for i in range(num_heuristic):
            heuristic_type = heuristic_types[i % len(heuristic_types)]
            individual = self.encoder.create_heuristic_individual(heuristic_type)
            individual.generation_created = 0
            individuals.append(individual)

        population = DEAPPopulation(individuals)
        population.generation = 0

        logger.info(
            f"Created constraint-aware DEAP population: {num_random} random, "
            f"{num_constraint_aware} constraint-aware, {num_heuristic} heuristic individuals"
        )

        return population

    def replace_population_constraint_aware(
        self,
        current_population: DEAPPopulation,
        offspring: List["DEAPIndividual"],
        strategy: str = "constraint_elitist",
    ) -> DEAPPopulation:
        """Replace population using constraint-aware strategies."""
        if strategy == "constraint_elitist":
            return self._constraint_elitist_replacement(current_population, offspring)
        elif strategy == "constraint_steady_state":
            return self._constraint_steady_state_replacement(
                current_population, offspring
            )
        elif strategy == "constraint_generational":
            return self._constraint_generational_replacement(
                current_population, offspring
            )
        else:
            logger.warning(f"Unknown strategy {strategy}, using constraint_elitist")
            return self._constraint_elitist_replacement(current_population, offspring)

    def _constraint_elitist_replacement(
        self, current_population: DEAPPopulation, offspring: List["DEAPIndividual"]
    ) -> DEAPPopulation:
        """Constraint-aware elitist replacement preserving best constraint-satisfying individuals."""

        # Separate feasible and infeasible individuals
        current_feasible = [
            ind
            for ind in current_population.individuals
            if getattr(ind, "critical_constraint_violations", 0) == 0
        ]
        current_infeasible = [
            ind
            for ind in current_population.individuals
            if getattr(ind, "critical_constraint_violations", 0) > 0
        ]

        offspring_feasible = [
            ind
            for ind in offspring
            if getattr(ind, "critical_constraint_violations", 0) == 0
        ]
        offspring_infeasible = [
            ind
            for ind in offspring
            if getattr(ind, "critical_constraint_violations", 0) > 0
        ]

        # Sort each group
        all_feasible = current_feasible + offspring_feasible
        all_infeasible = current_infeasible + offspring_infeasible

        all_feasible.sort(key=lambda x: safe_fitness_value(x), reverse=True)

        def infeasible_sort_key(x):
            violations = getattr(x, "constraint_violations", 0)
            fitness = safe_fitness_value(x)
            return (-violations, fitness)  # Fewer violations first, then higher fitness

        all_infeasible.sort(key=infeasible_sort_key, reverse=True)

        # Ensure minimum feasible ratio
        min_feasible_count = max(1, int(self.population_size * self.min_feasible_ratio))
        new_individuals = []

        # Add feasible individuals first
        feasible_to_add = min(len(all_feasible), min_feasible_count)
        new_individuals.extend(all_feasible[:feasible_to_add])

        # Fill remaining slots
        remaining_slots = self.population_size - len(new_individuals)
        if remaining_slots > 0:
            # Add more feasible individuals if available
            if feasible_to_add < len(all_feasible):
                additional_feasible = min(
                    remaining_slots, len(all_feasible) - feasible_to_add
                )
                new_individuals.extend(
                    all_feasible[
                        feasible_to_add : feasible_to_add + additional_feasible
                    ]
                )
                remaining_slots -= additional_feasible

            # Add best infeasible individuals if still needed
            if remaining_slots > 0 and all_infeasible:
                new_individuals.extend(all_infeasible[:remaining_slots])

        new_population = DEAPPopulation(new_individuals[: self.population_size])
        new_population.generation = current_population.generation + 1
        new_population.hall_of_fame = current_population.hall_of_fame
        new_population.logbook = current_population.logbook

        feasible_count = len(
            [
                ind
                for ind in new_individuals
                if getattr(ind, "critical_constraint_violations", 0) == 0
            ]
        )
        violation_count = len(
            [
                ind
                for ind in new_individuals
                if getattr(ind, "constraint_violations", 0) > 0
            ]
        )

        logger.debug(
            f"Constraint elitist replacement: {feasible_count} feasible, "
            f"{violation_count} with violations"
        )

        return new_population

    def _constraint_steady_state_replacement(
        self, current_population: DEAPPopulation, offspring: List["DEAPIndividual"]
    ) -> DEAPPopulation:
        """Steady-state replacement with constraint awareness."""
        combined = list(current_population.individuals) + offspring

        def sort_key(x):
            critical_violations = getattr(x, "critical_constraint_violations", 0)
            regular_violations = getattr(x, "constraint_violations", 0)
            fitness = safe_fitness_value(x)
            return (critical_violations, regular_violations, -fitness)

        combined.sort(key=sort_key)

        new_population = DEAPPopulation(combined[: self.population_size])
        new_population.generation = current_population.generation + 1
        new_population.hall_of_fame = current_population.hall_of_fame
        new_population.logbook = current_population.logbook

        return new_population

    def _constraint_generational_replacement(
        self, current_population: DEAPPopulation, offspring: List["DEAPIndividual"]
    ) -> DEAPPopulation:
        """Generational replacement with constraint-aware elitism."""

        # Keep some of the best constraint-satisfying individuals
        elite_count = max(2, int(self.population_size * 0.1))
        current_feasible = [
            ind
            for ind in current_population.individuals
            if getattr(ind, "critical_constraint_violations", 0) == 0
        ]
        current_feasible.sort(key=lambda x: safe_fitness_value(x), reverse=True)
        elite = current_feasible[: min(elite_count, len(current_feasible))]

        # Fill remaining with best offspring
        remaining_slots = self.population_size - len(elite)

        def offspring_sort_key(x):
            critical_violations = getattr(x, "critical_constraint_violations", 0)
            regular_violations = getattr(x, "constraint_violations", 0)
            fitness = safe_fitness_value(x)
            return (critical_violations, regular_violations, -fitness)

        offspring.sort(key=offspring_sort_key)

        new_individuals = elite + offspring[:remaining_slots]
        new_population = DEAPPopulation(new_individuals)
        new_population.generation = current_population.generation + 1
        new_population.hall_of_fame = current_population.hall_of_fame
        new_population.logbook = current_population.logbook

        return new_population

    def maintain_constraint_aware_diversity(
        self, population: DEAPPopulation, min_diversity: float = 0.1
    ) -> DEAPPopulation:
        """Maintain population diversity while preserving constraint satisfaction."""
        if len(population) < 2:
            return population

        individuals_to_replace = []

        # Check diversity within feasible individuals first
        feasible = [
            ind
            for ind in population.individuals
            if getattr(ind, "critical_constraint_violations", 0) == 0
        ]
        infeasible = [
            ind
            for ind in population.individuals
            if getattr(ind, "critical_constraint_violations", 0) > 0
        ]

        for i in range(len(feasible)):
            for j in range(i + 1, len(feasible)):
                diversity = population._calculate_diversity_metric(
                    feasible[i], feasible[j]
                )
                if diversity < min_diversity:
                    # Keep the better individual
                    if safe_fitness_value(feasible[i]) < safe_fitness_value(
                        feasible[j]
                    ):
                        if j not in individuals_to_replace:
                            individuals_to_replace.append(
                                population.individuals.index(feasible[j])
                            )
                    else:
                        if i not in individuals_to_replace:
                            individuals_to_replace.append(
                                population.individuals.index(feasible[i])
                            )

        # Replace low-diversity individuals, preferring to replace infeasible ones
        if individuals_to_replace:
            infeasible_indices = [
                population.individuals.index(ind) for ind in infeasible
            ]
            for idx in individuals_to_replace[: len(infeasible_indices)]:
                new_individual = self.encoder.create_heuristic_individual(
                    "constraint_priority"
                )
                new_individual.generation_created = population.generation
                population.individuals[idx] = new_individual

            logger.info(
                f"Replaced {len(individuals_to_replace)} individuals for diversity maintenance"
            )

        return population

    def detect_constraint_aware_convergence(
        self,
        population: DEAPPopulation,
        convergence_threshold: float = 0.01,
        generations_to_check: int = 10,
    ) -> bool:
        """Detect convergence with constraint awareness."""
        if len(self.generation_history) < generations_to_check:
            return False

        # Check fitness improvement over recent generations
        recent_best_fitness = [
            stats.best_fitness
            for stats in self.generation_history[-generations_to_check:]
        ]
        recent_feasibility = [
            stats.feasibility_rate
            for stats in self.generation_history[-generations_to_check:]
        ]
        recent_critical_satisfaction = [
            1.0 - (stats.critical_constraint_violations / max(1, stats.size))
            for stats in self.generation_history[-generations_to_check:]
        ]

        # Current population characteristics
        current_stats = population.calculate_statistics()

        # Calculate improvement rates
        fitness_improvement = (recent_best_fitness[-1] - recent_best_fitness[0]) / max(
            1, generations_to_check - 1
        )
        feasibility_improvement = (
            recent_feasibility[-1] - recent_feasibility[0]
        ) / max(1, generations_to_check - 1)
        critical_improvement = (
            recent_critical_satisfaction[-1] - recent_critical_satisfaction[0]
        ) / max(1, generations_to_check - 1)

        # Convergence criteria
        low_fitness_improvement = fitness_improvement < convergence_threshold
        low_feasibility_improvement = feasibility_improvement < 0.05
        low_critical_improvement = critical_improvement < 0.02
        low_diversity = current_stats.average_diversity < 0.05
        high_constraint_satisfaction = current_stats.constraint_satisfaction_rate > 0.9

        # Convergence conditions
        is_converged = (
            low_fitness_improvement and high_constraint_satisfaction and low_diversity
        ) or (
            low_feasibility_improvement and low_critical_improvement and low_diversity
        )

        if is_converged:
            logger.info(
                f"Constraint-aware convergence detected: "
                f"fitness_imp={fitness_improvement:.6f}, "
                f"feasibility_imp={feasibility_improvement:.3f}, "
                f"critical_imp={critical_improvement:.3f}, "
                f"diversity={current_stats.average_diversity:.3f}, "
                f"constraint_satisfaction={current_stats.constraint_satisfaction_rate:.3f}"
            )

        return is_converged

    def update_generation_history(self, population: DEAPPopulation):
        """Update generation history with constraint-aware statistics."""
        stats = population.calculate_statistics()
        self.generation_history.append(stats)

        # Keep history manageable
        if len(self.generation_history) > 100:
            self.generation_history = self.generation_history[-50:]

    def get_constraint_insights(self) -> Dict[str, Any]:
        """Get insights about constraint satisfaction across generations."""
        if not self.generation_history:
            return {}

        recent_stats = (
            self.generation_history[-10:]
            if len(self.generation_history) >= 10
            else self.generation_history
        )

        insights = {
            "constraint_satisfaction_trend": np.mean(
                [s.constraint_satisfaction_rate for s in recent_stats]
            ),
            "feasibility_improvement": (
                (recent_stats[-1].feasibility_rate - recent_stats[0].feasibility_rate)
                if len(recent_stats) > 1
                else 0
            ),
            "critical_violations_trend": np.mean(
                [s.critical_constraint_violations for s in recent_stats]
            ),
            "pruning_efficiency_trend": np.mean(
                [s.pruning_efficiency for s in recent_stats]
            ),
            "best_feasibility_rate": max([s.feasibility_rate for s in recent_stats]),
            "generations_analyzed": len(recent_stats),
        }

        return insights
