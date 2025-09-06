# scheduling_engine/genetic_algorithm/population.py

"""
Population Management for Genetic Algorithm component of hybrid CP-SAT + GA scheduling engine.
Manages the population of chromosomes representing variable selectors for CP-SAT search guidance.

Based on Nguyen et al. 2024 "Genetic-based Constraint Programming for Resource Constrained Job Scheduling"
"""

from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, Counter
import random
import statistics
import math

from ..core.problem_model import ExamSchedulingProblem
from .chromosome import VariableSelectorChromosome as Chromosome
from ..utils.logging import get_logger

logger = get_logger(__name__)


class PopulationInitStrategy(Enum):
    """Population initialization strategies"""

    RANDOM = "random"
    SEEDED = "seeded"
    HYBRID = "hybrid"
    PROBLEM_AWARE = "problem_aware"


class DiversityMeasure(Enum):
    """Diversity measurement methods"""

    GENOTYPIC = "genotypic"  # Based on chromosome structure
    PHENOTYPIC = "phenotypic"  # Based on solution quality
    BEHAVIORAL = "behavioral"  # Based on solution characteristics


@dataclass
class PopulationStatistics:
    """Statistics about the current population"""

    generation: int
    size: int
    best_fitness: float
    worst_fitness: float
    average_fitness: float
    fitness_variance: float
    fitness_std: float
    diversity_score: float
    convergence_measure: float
    unique_individuals: int
    elite_proportion: float
    stagnation_generations: int


@dataclass
class DiversityMetrics:
    """Detailed diversity metrics"""

    genotypic_diversity: float
    phenotypic_diversity: float
    behavioral_diversity: float
    structure_entropy: float
    fitness_entropy: float
    population_spread: float


class Population:
    """
    Represents a population of chromosomes (variable selectors) for the genetic algorithm.
    Maintains diversity, tracks fitness, and supports various population operations.
    """

    def __init__(
        self,
        individuals: Optional[List[Chromosome]] = None,
        max_size: int = 100,
        diversity_threshold: float = 0.1,
    ):
        self.individuals: List[Chromosome] = individuals or []
        self.max_size = max_size
        self.diversity_threshold = diversity_threshold
        self.generation = 0

        # Population tracking
        self.fitness_history: List[List[float]] = []
        self.diversity_history: List[float] = []
        self.best_ever_individual: Optional[Chromosome] = None
        self.best_ever_fitness: float = float("inf")

        # Statistics
        self.last_improvement_generation = 0
        self.stagnation_counter = 0

        # Diversity maintenance
        self.diversity_archive: List[Chromosome] = []
        self.diversity_threshold_adaptive = diversity_threshold

    def __len__(self) -> int:
        return len(self.individuals)

    def __iter__(self):
        return iter(self.individuals)

    def __getitem__(self, index: int) -> Chromosome:
        return self.individuals[index]

    def add_individual(self, individual: Chromosome) -> bool:
        """Add individual to population if there's space and it's diverse enough"""
        try:
            if len(self.individuals) >= self.max_size:
                return False

            # Check diversity
            if self._is_sufficiently_diverse(individual):
                self.individuals.append(individual)
                return True

            return False

        except Exception as e:
            logger.error(f"Error adding individual to population: {e}")
            return False

    def remove_individual(self, index: int) -> Optional[Chromosome]:
        """Remove individual at specified index"""
        try:
            if 0 <= index < len(self.individuals):
                return self.individuals.pop(index)
            return None
        except Exception as e:
            logger.error(f"Error removing individual from population: {e}")
            return None

    def get_best_individual(self) -> Optional[Chromosome]:
        """Get the best individual in current population"""
        try:
            if not self.individuals:
                return None

            evaluated_individuals = [
                ind
                for ind in self.individuals
                if hasattr(ind, "fitness") and ind.fitness is not None
            ]

            if not evaluated_individuals:
                return None

            return min(evaluated_individuals, key=lambda x: x.fitness)

        except Exception as e:
            logger.error(f"Error getting best individual: {e}")
            return None

    def get_worst_individual(self) -> Optional[Chromosome]:
        """Get the worst individual in current population"""
        try:
            if not self.individuals:
                return None

            evaluated_individuals = [
                ind
                for ind in self.individuals
                if hasattr(ind, "fitness") and ind.fitness is not None
            ]

            if not evaluated_individuals:
                return None

            return max(evaluated_individuals, key=lambda x: x.fitness)

        except Exception as e:
            logger.error(f"Error getting worst individual: {e}")
            return None

    def get_elite_individuals(self, count: int) -> List[Chromosome]:
        """Get top N individuals by fitness"""
        try:
            evaluated_individuals = [
                ind
                for ind in self.individuals
                if hasattr(ind, "fitness") and ind.fitness is not None
            ]

            if not evaluated_individuals:
                return []

            # Sort by fitness (lower is better)
            sorted_individuals = sorted(evaluated_individuals, key=lambda x: x.fitness)

            return sorted_individuals[:count]

        except Exception as e:
            logger.error(f"Error getting elite individuals: {e}")
            return []

    def calculate_diversity(
        self, measure: DiversityMeasure = DiversityMeasure.GENOTYPIC
    ) -> float:
        """Calculate population diversity using specified measure"""
        try:
            if len(self.individuals) < 2:
                return 0.0

            if measure == DiversityMeasure.GENOTYPIC:
                return self._calculate_genotypic_diversity()
            elif measure == DiversityMeasure.PHENOTYPIC:
                return self._calculate_phenotypic_diversity()
            elif measure == DiversityMeasure.BEHAVIORAL:
                return self._calculate_behavioral_diversity()
            else:
                return 0.0

        except Exception as e:
            logger.error(f"Error calculating diversity: {e}")
            return 0.0

    def _calculate_genotypic_diversity(self) -> float:
        """Calculate genotypic diversity based on chromosome structure"""
        try:
            total_distance = 0.0
            comparisons = 0

            for i in range(len(self.individuals)):
                for j in range(i + 1, len(self.individuals)):
                    # Placeholder for genetic distance calculation
                    # This should be implemented based on your specific chromosome structure
                    distance = self._calculate_genetic_distance(
                        self.individuals[i], self.individuals[j]
                    )
                    total_distance += distance
                    comparisons += 1

            return total_distance / max(comparisons, 1)

        except Exception as e:
            logger.error(f"Error calculating genotypic diversity: {e}")
            return 0.0

    def _calculate_genetic_distance(
        self, chrom1: Chromosome, chrom2: Chromosome
    ) -> float:
        """Calculate genetic distance between two chromosomes"""
        # Placeholder implementation - should be customized based on your chromosome structure
        try:
            # Simple implementation: compare tree structures
            if len(chrom1.genes) != len(chrom2.genes):
                return 1.0

            similarity = 0
            for gene1, gene2 in zip(chrom1.genes, chrom2.genes):
                if gene1.priority_tree.to_string() == gene2.priority_tree.to_string():
                    similarity += 1

            return 1.0 - (similarity / len(chrom1.genes))
        except Exception as e:
            logger.error(f"Error calculating genetic distance: {e}")
            return 1.0

    def _calculate_phenotypic_diversity(self) -> float:
        """Calculate phenotypic diversity based on fitness values"""
        try:
            fitness_values = [
                ind.fitness
                for ind in self.individuals
                if hasattr(ind, "fitness") and ind.fitness is not None
            ]

            if len(fitness_values) < 2:
                return 0.0

            # Calculate coefficient of variation
            mean_fitness = statistics.mean(fitness_values)
            std_fitness = statistics.stdev(fitness_values)

            if mean_fitness == 0:
                return 0.0

            cv = std_fitness / abs(mean_fitness)
            return min(1.0, cv)  # Normalize to [0, 1]

        except Exception as e:
            logger.error(f"Error calculating phenotypic diversity: {e}")
            return 0.0

    def _calculate_behavioral_diversity(self) -> float:
        """Calculate behavioral diversity based on solution characteristics"""
        # Placeholder implementation - requires solution evaluation
        return 0.5

    def _is_sufficiently_diverse(self, candidate: Chromosome) -> bool:
        """Check if candidate is sufficiently diverse from existing population"""
        try:
            if not self.individuals:
                return True

            # Calculate minimum distance to existing individuals
            min_distance = float("inf")
            for individual in self.individuals:
                distance = self._calculate_genetic_distance(candidate, individual)
                min_distance = min(min_distance, distance)

            return min_distance >= self.diversity_threshold_adaptive

        except Exception as e:
            logger.error(f"Error checking diversity: {e}")
            return True  # Allow by default on error

    def update_diversity_threshold(
        self, generation: int, target_diversity: float
    ) -> None:
        """Adaptively update diversity threshold based on population state"""
        try:
            current_diversity = self.calculate_diversity()

            # Adjust threshold to maintain target diversity
            if current_diversity < target_diversity:
                # Increase threshold to promote more diversity
                self.diversity_threshold_adaptive *= 1.1
            elif current_diversity > target_diversity * 1.5:
                # Decrease threshold to allow more individuals
                self.diversity_threshold_adaptive *= 0.9

            # Keep threshold within reasonable bounds
            self.diversity_threshold_adaptive = max(
                0.01, min(0.5, self.diversity_threshold_adaptive)
            )

        except Exception as e:
            logger.error(f"Error updating diversity threshold: {e}")

    def get_statistics(self) -> PopulationStatistics:
        """Get comprehensive population statistics"""
        try:
            if not self.individuals:
                return PopulationStatistics(
                    generation=self.generation,
                    size=0,
                    best_fitness=float("inf"),
                    worst_fitness=float("inf"),
                    average_fitness=float("inf"),
                    fitness_variance=0.0,
                    fitness_std=0.0,
                    diversity_score=0.0,
                    convergence_measure=0.0,
                    unique_individuals=0,
                    elite_proportion=0.0,
                    stagnation_generations=self.stagnation_counter,
                )

            # Calculate fitness statistics
            fitness_values = [
                ind.fitness
                for ind in self.individuals
                if hasattr(ind, "fitness") and ind.fitness is not None
            ]

            if not fitness_values:
                fitness_values = [float("inf")]

            best_fitness = min(fitness_values)
            worst_fitness = max(fitness_values)
            avg_fitness = statistics.mean(fitness_values)
            fitness_var = (
                statistics.variance(fitness_values) if len(fitness_values) > 1 else 0.0
            )
            fitness_std = (
                statistics.stdev(fitness_values) if len(fitness_values) > 1 else 0.0
            )

            # Calculate diversity
            diversity_score = self.calculate_diversity()

            # Calculate convergence measure
            convergence_measure = self._calculate_convergence_measure()

            # Count unique individuals
            unique_count = self._count_unique_individuals()

            # Calculate elite proportion
            elite_threshold = avg_fitness * 0.9  # Top 10% by fitness
            elite_count = sum(1 for f in fitness_values if f <= elite_threshold)
            elite_proportion = (
                elite_count / len(fitness_values) if fitness_values else 0.0
            )

            return PopulationStatistics(
                generation=self.generation,
                size=len(self.individuals),
                best_fitness=best_fitness,
                worst_fitness=worst_fitness,
                average_fitness=avg_fitness,
                fitness_variance=fitness_var,
                fitness_std=fitness_std,
                diversity_score=diversity_score,
                convergence_measure=convergence_measure,
                unique_individuals=unique_count,
                elite_proportion=elite_proportion,
                stagnation_generations=self.stagnation_counter,
            )

        except Exception as e:
            logger.error(f"Error getting population statistics: {e}")
            return PopulationStatistics(
                generation=self.generation,
                size=len(self.individuals),
                best_fitness=float("inf"),
                worst_fitness=float("inf"),
                average_fitness=float("inf"),
                fitness_variance=0.0,
                fitness_std=0.0,
                diversity_score=0.0,
                convergence_measure=0.0,
                unique_individuals=0,
                elite_proportion=0.0,
                stagnation_generations=self.stagnation_counter,
            )

    def _calculate_convergence_measure(self) -> float:
        """Calculate how converged the population is"""
        try:
            if len(self.fitness_history) < 2:
                return 0.0

            # Look at recent fitness improvements
            recent_generations = min(10, len(self.fitness_history))
            recent_best = [
                min(generation)
                for generation in self.fitness_history[-recent_generations:]
            ]

            if len(recent_best) < 2:
                return 0.0

            # Calculate improvement rate
            first_fitness = recent_best[0]
            last_fitness = recent_best[-1]

            if first_fitness == 0:
                return 1.0 if last_fitness == 0 else 0.0

            improvement_rate = abs(last_fitness - first_fitness) / abs(first_fitness)

            # Convert to convergence measure (less improvement = more converged)
            convergence = max(0.0, 1.0 - improvement_rate * 10)  # Scale factor 10
            return min(1.0, convergence)

        except Exception as e:
            logger.error(f"Error calculating convergence measure: {e}")
            return 0.0

    def _count_unique_individuals(self) -> int:
        """Count unique individuals in population"""
        try:
            unique_hashes = set()
            for individual in self.individuals:
                # Create a simple hash based on chromosome structure
                hash_value = hash(
                    tuple(gene.priority_tree.to_string() for gene in individual.genes)
                )
                unique_hashes.add(hash_value)

            return len(unique_hashes)

        except Exception as e:
            logger.error(f"Error counting unique individuals: {e}")
            return len(self.individuals)

    def advance_generation(self) -> None:
        """Advance to next generation and update tracking"""
        try:
            self.generation += 1

            # Record fitness history
            current_fitness = [
                ind.fitness
                for ind in self.individuals
                if hasattr(ind, "fitness") and ind.fitness is not None
            ]
            self.fitness_history.append(current_fitness)

            # Record diversity history
            diversity = self.calculate_diversity()
            self.diversity_history.append(diversity)

            # Update best ever individual
            best_current = self.get_best_individual()
            if best_current and best_current.fitness < self.best_ever_fitness:
                self.best_ever_individual = best_current
                self.best_ever_fitness = best_current.fitness
                self.last_improvement_generation = self.generation
                self.stagnation_counter = 0
            else:
                self.stagnation_counter += 1

            # Maintain diversity archive
            self._update_diversity_archive()

            # Trim history if too long
            max_history = 100
            if len(self.fitness_history) > max_history:
                self.fitness_history = self.fitness_history[-max_history:]
            if len(self.diversity_history) > max_history:
                self.diversity_history = self.diversity_history[-max_history:]

        except Exception as e:
            logger.error(f"Error advancing generation: {e}")

    def _update_diversity_archive(self) -> None:
        """Update archive of diverse individuals"""
        try:
            archive_size = 20  # Keep top 20 diverse individuals

            # Add current best individuals to archive consideration
            candidates = self.get_elite_individuals(10) + self.diversity_archive

            # Remove duplicates
            unique_candidates = []
            seen_hashes = set()
            for candidate in candidates:
                hash_val = hash(
                    tuple(gene.priority_tree.to_string() for gene in candidate.genes)
                )
                if hash_val not in seen_hashes:
                    unique_candidates.append(candidate)
                    seen_hashes.add(hash_val)

            # Select most diverse individuals for archive
            if len(unique_candidates) <= archive_size:
                self.diversity_archive = unique_candidates
            else:
                # Greedily select diverse individuals
                selected = [unique_candidates[0]]  # Start with first
                remaining = unique_candidates[1:]

                while len(selected) < archive_size and remaining:
                    # Find individual with maximum minimum distance to selected
                    best_candidate = None
                    best_min_distance = -1

                    for candidate in remaining:
                        min_distance = min(
                            self._calculate_genetic_distance(candidate, selected_ind)
                            for selected_ind in selected
                        )
                        if min_distance > best_min_distance:
                            best_min_distance = int(min_distance)
                            best_candidate = candidate

                    if best_candidate:
                        selected.append(best_candidate)
                        remaining.remove(best_candidate)
                    else:
                        break

                self.diversity_archive = selected

        except Exception as e:
            logger.error(f"Error updating diversity archive: {e}")

    def replace_worst_individuals(
        self, new_individuals: List[Chromosome], count: int
    ) -> List[Chromosome]:
        """Replace worst individuals with new ones"""
        try:
            if not self.individuals or count <= 0:
                return []

            # Sort individuals by fitness (worst first)
            evaluated_individuals = [
                (i, ind)
                for i, ind in enumerate(self.individuals)
                if hasattr(ind, "fitness") and ind.fitness is not None
            ]

            if not evaluated_individuals:
                return []

            evaluated_individuals.sort(key=lambda x: x[1].fitness, reverse=True)

            # Replace worst individuals
            replaced = []
            replacement_count = min(
                count, len(new_individuals), len(evaluated_individuals)
            )

            for i in range(replacement_count):
                if i < len(new_individuals):
                    old_index = evaluated_individuals[i][0]
                    old_individual = self.individuals[old_index]
                    self.individuals[old_index] = new_individuals[i]
                    replaced.append(old_individual)

            return replaced

        except Exception as e:
            logger.error(f"Error replacing worst individuals: {e}")
            return []

    def maintain_diversity(self, target_diversity: float = 0.3) -> int:
        """Maintain population diversity by removing similar individuals"""
        try:
            if len(self.individuals) < 2:
                return 0

            current_diversity = self.calculate_diversity()
            if current_diversity >= target_diversity:
                return 0

            # Find pairs of similar individuals
            similar_pairs = []
            for i in range(len(self.individuals)):
                for j in range(i + 1, len(self.individuals)):
                    distance = self._calculate_genetic_distance(
                        self.individuals[i], self.individuals[j]
                    )
                    if distance < self.diversity_threshold_adaptive:
                        similar_pairs.append((i, j, distance))

            # Sort by similarity (most similar first)
            similar_pairs.sort(key=lambda x: x[2])

            # Remove individuals from similar pairs (keep better one)
            removed_indices = set()
            removed_count = 0

            for i, j, distance in similar_pairs:
                if i in removed_indices or j in removed_indices:
                    continue

                # Keep the individual with better fitness
                fitness_i = (
                    self.individuals[i].fitness
                    if hasattr(self.individuals[i], "fitness")
                    else float("inf")
                )
                fitness_j = (
                    self.individuals[j].fitness
                    if hasattr(self.individuals[j], "fitness")
                    else float("inf")
                )

                remove_index = i if fitness_i > fitness_j else j
                removed_indices.add(remove_index)
                removed_count += 1

                # Stop if we've removed enough
                if (
                    len(removed_indices) >= len(self.individuals) // 4
                ):  # Don't remove more than 25%
                    break

            # Remove individuals (in reverse order to maintain indices)
            for index in sorted(removed_indices, reverse=True):
                self.individuals.pop(index)

            return removed_count

        except Exception as e:
            logger.error(f"Error maintaining diversity: {e}")
            return 0

    def clear(self) -> None:
        """Clear the population"""
        self.individuals.clear()

    def copy(self) -> "Population":
        """Create a copy of the population"""
        try:
            copied_individuals = [ind.copy() for ind in self.individuals]
            new_pop = Population(
                copied_individuals, self.max_size, self.diversity_threshold
            )
            new_pop.generation = self.generation
            new_pop.fitness_history = self.fitness_history.copy()
            new_pop.diversity_history = self.diversity_history.copy()
            new_pop.best_ever_fitness = self.best_ever_fitness
            new_pop.last_improvement_generation = self.last_improvement_generation
            new_pop.stagnation_counter = self.stagnation_counter
            return new_pop
        except Exception as e:
            logger.error(f"Error copying population: {e}")
            return Population()


class PopulationManager:
    """
    High-level manager for population operations including initialization,
    evolution, and maintenance strategies.
    """

    def __init__(
        self,
        population_size: int = 50,
        problem: Optional[ExamSchedulingProblem] = None,
        diversity_target: float = 0.3,
    ):
        self.population_size = population_size
        self.problem = problem
        self.diversity_target = diversity_target

        # Create population
        self.population = Population(max_size=population_size, diversity_threshold=0.1)

        # Initialization strategies
        self.init_strategies = {
            PopulationInitStrategy.RANDOM: self._initialize_random,
            PopulationInitStrategy.SEEDED: self._initialize_seeded,
            PopulationInitStrategy.HYBRID: self._initialize_hybrid,
            PopulationInitStrategy.PROBLEM_AWARE: self._initialize_problem_aware,
        }

    async def initialize_population(
        self,
        strategy: PopulationInitStrategy = PopulationInitStrategy.HYBRID,
        seed_individual: Optional[Chromosome] = None,
    ) -> None:
        """Initialize population using specified strategy"""
        try:
            logger.info(
                f"Initializing population of size {self.population_size} using {strategy.value} strategy"
            )

            init_function = self.init_strategies.get(strategy)
            if not init_function:
                raise ValueError(f"Unknown initialization strategy: {strategy}")

            individuals = await init_function(seed_individual)

            # Ensure we have the right population size
            while len(individuals) < self.population_size:
                random_individual = await self._create_random_individual()
                individuals.append(random_individual)

            # Truncate if too many
            individuals = individuals[: self.population_size]

            # Set population
            self.population.individuals = individuals

            logger.info(f"Population initialized with {len(individuals)} individuals")

        except Exception as e:
            logger.error(f"Error initializing population: {e}")
            raise

    async def initialize_from_seed(
        self,
        seed_chromosome: Chromosome,
        variation_rate: float = 0.3,
        random_individuals: float = 0.2,
    ) -> None:
        """Initialize population from CP-SAT seed solution (research paper approach)"""
        try:
            logger.info("Initializing population from CP-SAT seed solution")

            individuals = []

            # Add the seed individual
            individuals.append(seed_chromosome)

            # Create variations of the seed (research paper approach)
            variation_count = int(self.population_size * variation_rate)
            for _ in range(variation_count):
                variation = await self._create_seed_variation(seed_chromosome)
                individuals.append(variation)

            # Create random individuals for diversity
            random_count = int(self.population_size * random_individuals)
            for _ in range(random_count):
                random_individual = await self._create_random_individual()
                individuals.append(random_individual)

            # Fill remaining with hybrid approach
            while len(individuals) < self.population_size:
                if random.random() < 0.5:
                    # Another seed variation
                    variation = await self._create_seed_variation(seed_chromosome)
                    individuals.append(variation)
                else:
                    # Random individual
                    random_individual = await self._create_random_individual()
                    individuals.append(random_individual)

            # Set population
            self.population.individuals = individuals[: self.population_size]

            logger.info(
                f"Population initialized from seed with {len(self.population.individuals)} individuals"
            )

        except Exception as e:
            logger.error(f"Error initializing population from seed: {e}")
            raise

    async def _initialize_random(
        self, seed_individual: Optional[Chromosome] = None
    ) -> List[Chromosome]:
        """Initialize population with random individuals"""
        try:
            individuals = []
            for _ in range(self.population_size):
                individual = await self._create_random_individual()
                individuals.append(individual)
            return individuals
        except Exception as e:
            logger.error(f"Error in random initialization: {e}")
            return []

    async def _initialize_seeded(
        self, seed_individual: Optional[Chromosome] = None
    ) -> List[Chromosome]:
        """Initialize population with seed individual and variations"""
        try:
            if not seed_individual:
                return await self._initialize_random()

            individuals = [seed_individual]

            # Create variations of the seed
            for _ in range(self.population_size - 1):
                variation = await self._create_seed_variation(seed_individual)
                individuals.append(variation)

            return individuals
        except Exception as e:
            logger.error(f"Error in seeded initialization: {e}")
            return []

    async def _initialize_hybrid(
        self, seed_individual: Optional[Chromosome] = None
    ) -> List[Chromosome]:
        """Initialize population with mix of seeded and random individuals"""
        try:
            individuals = []

            if seed_individual:
                # Add seed
                individuals.append(seed_individual)

                # Add seed variations (30% of population)
                variation_count = max(1, self.population_size // 3)
                for _ in range(variation_count):
                    variation = await self._create_seed_variation(seed_individual)
                    individuals.append(variation)

            # Fill remaining with random individuals
            while len(individuals) < self.population_size:
                random_individual = await self._create_random_individual()
                individuals.append(random_individual)

            return individuals[: self.population_size]

        except Exception as e:
            logger.error(f"Error in hybrid initialization: {e}")
            return []

    async def _initialize_problem_aware(
        self, seed_individual: Optional[Chromosome] = None
    ) -> List[Chromosome]:
        """Initialize population with problem-specific heuristics"""
        try:
            individuals = []

            if seed_individual:
                individuals.append(seed_individual)

            # Create problem-aware individuals based on problem characteristics
            if self.problem:
                # Different strategies based on problem size
                if len(self.problem.exams) > 100:
                    # Large problems - focus on simple, efficient heuristics
                    for _ in range(self.population_size // 3):
                        individual = await self._create_simple_heuristic_individual()
                        individuals.append(individual)

                # Medium-complexity heuristics
                for _ in range(self.population_size // 3):
                    individual = await self._create_complex_heuristic_individual()
                    individuals.append(individual)

            # Fill remaining with random
            while len(individuals) < self.population_size:
                random_individual = await self._create_random_individual()
                individuals.append(random_individual)

            return individuals[: self.population_size]

        except Exception as e:
            logger.error(f"Error in problem-aware initialization: {e}")
            return []

    async def _create_random_individual(self) -> Chromosome:
        """Create a random chromosome"""
        try:
            if self.problem is None:
                raise ValueError("Problem must be set to create random individuals")

            chromosome = Chromosome.create_random(self.problem)
            return chromosome

        except Exception as e:
            logger.error(f"Error creating random individual: {e}")
            # Return empty chromosome as fallback
            return Chromosome()

    async def _create_seed_variation(self, seed: Chromosome) -> Chromosome:
        """Create a variation of the seed chromosome"""
        try:
            # Copy the seed
            variation = seed.copy()

            # Apply mutations to create variation
            # This would need to be implemented based on your mutation operators
            # For now, just return a copy
            return variation

        except Exception as e:
            logger.error(f"Error creating seed variation: {e}")
            return Chromosome()

    async def _create_simple_heuristic_individual(self) -> Chromosome:
        """Create individual with simple heuristic (for large problems)"""
        try:
            if self.problem is None:
                raise ValueError("Problem must be set to create heuristic individuals")

            # Create using random initialization for now
            return await self._create_random_individual()

        except Exception as e:
            logger.error(f"Error creating simple heuristic individual: {e}")
            return Chromosome()

    async def _create_complex_heuristic_individual(self) -> Chromosome:
        """Create individual with complex heuristic"""
        try:
            if self.problem is None:
                raise ValueError("Problem must be set to create heuristic individuals")

            # Create using random initialization for now
            return await self._create_random_individual()

        except Exception as e:
            logger.error(f"Error creating complex heuristic individual: {e}")
            return Chromosome()

    async def create_random_individuals(self, count: int) -> List[Chromosome]:
        """Create multiple random individuals"""
        try:
            individuals = []
            for _ in range(count):
                individual = await self._create_random_individual()
                individuals.append(individual)
            return individuals
        except Exception as e:
            logger.error(f"Error creating random individuals: {e}")
            return []

    def get_best_individual(self) -> Optional[Chromosome]:
        """Get the best individual in population"""
        return self.population.get_best_individual()

    def get_worst_individual_index(self) -> int:
        """Get index of worst individual"""
        try:
            worst = self.population.get_worst_individual()
            if worst:
                return self.population.individuals.index(worst)
            return 0
        except Exception as e:
            logger.error(f"Error getting worst individual index: {e}")
            return 0

    def get_elite_individuals(self, count: int) -> List[Chromosome]:
        """Get elite individuals"""
        return self.population.get_elite_individuals(count)

    async def replace_population(self, new_individuals: List[Chromosome]) -> None:
        """Replace current population with new individuals"""
        try:
            self.population.individuals = new_individuals[: self.population_size]
            self.population.advance_generation()
        except Exception as e:
            logger.error(f"Error replacing population: {e}")

    def size(self) -> int:
        """Get population size"""
        return len(self.population)

    def get_statistics(self) -> PopulationStatistics:
        """Get population statistics"""
        return self.population.get_statistics()

    def calculate_diversity(self) -> float:
        """Calculate population diversity"""
        return self.population.calculate_diversity()

    def maintain_diversity(self) -> int:
        """Maintain population diversity"""
        return self.population.maintain_diversity(self.diversity_target)

    def advance_generation(self) -> None:
        """Advance to next generation"""
        self.population.advance_generation()

    async def get_population_summary(self) -> Dict[str, Any]:
        """Get comprehensive population summary"""
        try:
            stats = self.get_statistics()
            diversity = self.calculate_diversity()

            # Fitness distribution
            fitness_values = [
                ind.fitness
                for ind in self.population.individuals
                if hasattr(ind, "fitness") and ind.fitness is not None
            ]

            fitness_quartiles = []
            if fitness_values:
                sorted_fitness = sorted(fitness_values)
                n = len(sorted_fitness)
                fitness_quartiles = [
                    sorted_fitness[0],  # Min
                    sorted_fitness[n // 4] if n >= 4 else sorted_fitness[0],  # Q1
                    sorted_fitness[n // 2] if n >= 2 else sorted_fitness[0],  # Median
                    sorted_fitness[3 * n // 4] if n >= 4 else sorted_fitness[-1],  # Q3
                    sorted_fitness[-1],  # Max
                ]

            return {
                "generation": stats.generation,
                "population_size": stats.size,
                "fitness_statistics": {
                    "best": stats.best_fitness,
                    "worst": stats.worst_fitness,
                    "average": stats.average_fitness,
                    "std": stats.fitness_std,
                    "quartiles": fitness_quartiles,
                },
                "diversity_metrics": {
                    "overall_diversity": diversity,
                    "unique_individuals": stats.unique_individuals,
                    "diversity_target": self.diversity_target,
                },
                "population_composition": {
                    "elite_proportion": stats.elite_proportion,
                },
                "evolution_progress": {
                    "stagnation_generations": stats.stagnation_generations,
                    "convergence_measure": stats.convergence_measure,
                    "last_improvement": self.population.last_improvement_generation,
                },
            }

        except Exception as e:
            logger.error(f"Error getting population summary: {e}")
            return {"error": str(e)}
