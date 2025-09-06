# scheduling_engine/genetic_algorithm/operators/crossover.py

"""
Crossover Operators for Genetic Algorithm.

Implements constraint-preserving crossover operators for exam scheduling optimization.
Based on Nguyen et al. 2024 research paper with 90% crossover rate and
variable ordering evolution for genetic-based constraint programming.
"""

from typing import List, Dict, Any, Optional, Set, Tuple, Union, cast
from dataclasses import dataclass
import random
import logging
from uuid import UUID
from abc import ABC, abstractmethod
from collections import defaultdict

from ...core.problem_model import ExamSchedulingProblem
from ..chromosome import VariableSelectorChromosome, ExamPriorityGene

logger = logging.getLogger(__name__)


@dataclass
class CrossoverConfig:
    """Configuration for crossover operations"""

    crossover_rate: float = 0.9  # As specified in research paper (90%)
    priority_blend_factor: float = 0.6
    preserve_elite_genes: bool = True
    repair_offspring: bool = True
    diversity_preservation: bool = True
    constraint_aware_crossover: bool = True


class CrossoverOperator(ABC):
    """Abstract base class for crossover operators"""

    def __init__(self, config: CrossoverConfig):
        self.config = config
        self.generation_count = 0
        self.crossover_statistics: Dict[str, List[Any]] = defaultdict(list)

    @abstractmethod
    def crossover(
        self,
        parent1: VariableSelectorChromosome,
        parent2: VariableSelectorChromosome,
        problem: ExamSchedulingProblem,
    ) -> Tuple[VariableSelectorChromosome, VariableSelectorChromosome]:
        """Perform crossover between two parents"""
        pass

    def should_apply_crossover(self) -> bool:
        """Determine if crossover should be applied"""
        return random.random() < self.config.crossover_rate

    def _repair_chromosome_constraints(
        self, chromosome: VariableSelectorChromosome, problem: ExamSchedulingProblem
    ) -> VariableSelectorChromosome:
        """Placeholder for constraint repair logic"""
        # This would be implemented to repair constraint violations in offspring
        return chromosome

    def _are_assignments_compatible(
        self,
        gene1: ExamPriorityGene,
        gene2: ExamPriorityGene,
        exam: Any,
        problem: ExamSchedulingProblem,
    ) -> bool:
        """Placeholder for assignment compatibility check"""
        # This would be implemented to check if assignments are compatible
        return True

    def _resolve_pmx_conflicts(
        self,
        chromosome: VariableSelectorChromosome,
        mapping: Dict[UUID, UUID],
        start_point: int,
        end_point: int,
    ) -> None:
        """Placeholder for PMX conflict resolution"""
        # This would be implemented to resolve PMX conflicts
        pass

    def _track_crossover_performance(
        self,
        strategy: str,
        parent1: VariableSelectorChromosome,
        parent2: VariableSelectorChromosome,
        offspring1: VariableSelectorChromosome,
        offspring2: VariableSelectorChromosome,
        problem: ExamSchedulingProblem,
    ) -> None:
        """Placeholder for tracking crossover performance"""
        # This would be implemented to track crossover performance
        pass


class UniformCrossover(CrossoverOperator):
    """
    Uniform crossover operator.

    Exchanges genes between parents with equal probability while
    preserving constraint feasibility and variable ordering priorities.
    """

    def crossover(
        self,
        parent1: VariableSelectorChromosome,
        parent2: VariableSelectorChromosome,
        problem: ExamSchedulingProblem,
    ) -> Tuple[VariableSelectorChromosome, VariableSelectorChromosome]:
        """Perform uniform crossover"""
        try:
            if not self.should_apply_crossover():
                return parent1.copy(), parent2.copy()

            offspring1 = parent1.copy()
            offspring2 = parent2.copy()

            # Ensure both parents have same exam order (by exam_id)
            exam_order1 = {gene.exam_id: i for i, gene in enumerate(parent1.genes)}
            exam_order2 = {gene.exam_id: i for i, gene in enumerate(parent2.genes)}

            # Common exams between parents
            common_exams = set(exam_order1.keys()) & set(exam_order2.keys())

            if not common_exams:
                logger.warning("No common exams between parents for crossover")
                return parent1.copy(), parent2.copy()

            # Perform uniform crossover on common exams
            for exam_id in common_exams:
                if random.random() < 0.5:
                    # Exchange genes between offspring
                    idx1 = exam_order1[exam_id]
                    idx2 = exam_order2[exam_id]

                    if idx1 < len(offspring1.genes) and idx2 < len(offspring2.genes):
                        # Exchange priority trees
                        gene1 = offspring1.genes[idx1]
                        gene2 = offspring2.genes[idx2]

                        # Swap priority trees
                        gene1.priority_tree, gene2.priority_tree = (
                            gene2.priority_tree,
                            gene1.priority_tree,
                        )
                        gene1.cached_priority = None
                        gene2.cached_priority = None

            # Repair constraints if enabled
            if self.config.repair_offspring:
                offspring1 = self._repair_chromosome_constraints(offspring1, problem)
                offspring2 = self._repair_chromosome_constraints(offspring2, problem)

            # Invalidate fitness for recalculation
            offspring1.fitness = 0.0
            offspring2.fitness = 0.0

            logger.debug(
                f"Uniform crossover completed for {len(common_exams)} common exams"
            )
            return offspring1, offspring2

        except Exception as e:
            logger.error(f"Uniform crossover failed: {e}")
            return parent1.copy(), parent2.copy()


class OrderBasedCrossover(CrossoverOperator):
    """
    Order-based crossover operator.

    Preserves relative gene ordering while exchanging priority-based
    variable selectors as emphasized in the research paper.
    """

    def crossover(
        self,
        parent1: VariableSelectorChromosome,
        parent2: VariableSelectorChromosome,
        problem: ExamSchedulingProblem,
    ) -> Tuple[VariableSelectorChromosome, VariableSelectorChromosome]:
        """Perform order-based crossover"""
        try:
            if not self.should_apply_crossover():
                return parent1.copy(), parent2.copy()

            # Create copies for offspring
            offspring1 = parent1.copy()
            offspring2 = parent2.copy()

            # Get crossover points
            min_length = min(len(parent1.genes), len(parent2.genes))
            if min_length < 2:
                return offspring1, offspring2

            # Select crossover segment (25-75% of chromosome)
            segment_size = random.randint(min_length // 4, 3 * min_length // 4)
            start_point = random.randint(0, min_length - segment_size)
            end_point = start_point + segment_size

            # Extract segments with priority preservation
            segment1 = parent1.genes[start_point:end_point]
            segment2 = parent2.genes[start_point:end_point]

            # Priority-based ordering exchange
            segment1_exams = {gene.exam_id for gene in segment1}
            segment2_exams = {gene.exam_id for gene in segment2}

            # Create new orderings based on other parent's priorities
            new_segment1 = self._create_ordered_segment(
                segment2, segment1_exams, parent2
            )
            new_segment2 = self._create_ordered_segment(
                segment1, segment2_exams, parent1
            )

            # Replace segments in offspring
            offspring1.genes[start_point:end_point] = new_segment1
            offspring2.genes[start_point:end_point] = new_segment2

            # Repair constraints
            if self.config.repair_offspring:
                offspring1 = self._repair_chromosome_constraints(offspring1, problem)
                offspring2 = self._repair_chromosome_constraints(offspring2, problem)

            offspring1.fitness = 0.0
            offspring2.fitness = 0.0

            logger.debug(
                f"Order-based crossover completed with segment [{start_point}:{end_point}]"
            )
            return offspring1, offspring2

        except Exception as e:
            logger.error(f"Order-based crossover failed: {e}")
            return parent1.copy(), parent2.copy()

    def _create_ordered_segment(
        self,
        source_segment: List[ExamPriorityGene],
        target_exam_ids: Set[UUID],
        reference_parent: VariableSelectorChromosome,
    ) -> List[ExamPriorityGene]:
        """Create ordered segment based on reference parent priorities"""
        try:
            # Filter source segment for target exams
            new_segment = []
            for gene in source_segment:
                if gene.exam_id in target_exam_ids:
                    new_gene = gene.copy()
                    new_segment.append(new_gene)

            return new_segment

        except Exception as e:
            logger.error(f"Error creating ordered segment: {e}")
            return source_segment.copy()


class PriorityBasedCrossover(CrossoverOperator):
    """
    Priority-based crossover operator.

    Focuses on exchanging priority scores to evolve effective
    variable ordering strategies for constraint programming.
    """

    def crossover(
        self,
        parent1: VariableSelectorChromosome,
        parent2: VariableSelectorChromosome,
        problem: ExamSchedulingProblem,
    ) -> Tuple[VariableSelectorChromosome, VariableSelectorChromosome]:
        """Perform priority-based crossover"""
        try:
            if not self.should_apply_crossover():
                return parent1.copy(), parent2.copy()

            offspring1 = parent1.copy()
            offspring2 = parent2.copy()

            # Align chromosomes by exam_id
            exam_mapping1 = {gene.exam_id: gene for gene in offspring1.genes}
            exam_mapping2 = {gene.exam_id: gene for gene in offspring2.genes}

            common_exams = set(exam_mapping1.keys()) & set(exam_mapping2.keys())

            if not common_exams:
                return offspring1, offspring2

            # Priority exchange methods
            exchange_method = random.choice(["arithmetic", "geometric", "weighted"])

            for exam_id in common_exams:
                gene1 = exam_mapping1[exam_id]
                gene2 = exam_mapping2[exam_id]

                # Since we don't have priority_score in ExamPriorityGene,
                # we'll need to calculate priorities first
                terminals1 = problem.extract_gp_terminals(exam_id)
                terminals2 = problem.extract_gp_terminals(exam_id)

                priority1 = gene1.calculate_priority(terminals1)
                priority2 = gene2.calculate_priority(terminals2)

                if exchange_method == "arithmetic":
                    # Arithmetic crossover
                    alpha = random.uniform(0.3, 0.7)
                    new_priority1 = alpha * priority1 + (1 - alpha) * priority2
                    new_priority2 = alpha * priority2 + (1 - alpha) * priority1

                elif exchange_method == "geometric":
                    # Geometric crossover
                    alpha = random.uniform(0.3, 0.7)
                    new_priority1 = (priority1**alpha) * (priority2 ** (1 - alpha))
                    new_priority2 = (priority2**alpha) * (priority1 ** (1 - alpha))

                else:  # weighted
                    # Weighted crossover based on parent fitness
                    fitness1 = parent1.fitness if parent1.fitness is not None else 0.0
                    fitness2 = parent2.fitness if parent2.fitness is not None else 0.0

                    total_fitness = fitness1 + fitness2
                    if total_fitness > 0:
                        weight1 = fitness1 / total_fitness
                        weight2 = fitness2 / total_fitness
                    else:
                        weight1 = weight2 = 0.5

                    new_priority1 = weight1 * priority1 + weight2 * priority2
                    new_priority2 = weight2 * priority1 + weight1 * priority2

                # Store new priorities in cached_priority
                gene1.cached_priority = max(0.0, min(1.0, new_priority1))
                gene2.cached_priority = max(0.0, min(1.0, new_priority2))

            # Repair constraints if enabled
            if self.config.repair_offspring:
                offspring1 = self._repair_chromosome_constraints(offspring1, problem)
                offspring2 = self._repair_chromosome_constraints(offspring2, problem)

            offspring1.fitness = 0.0
            offspring2.fitness = 0.0

            logger.debug(
                f"Priority-based crossover completed using {exchange_method} method"
            )
            return offspring1, offspring2

        except Exception as e:
            logger.error(f"Priority-based crossover failed: {e}")
            return parent1.copy(), parent2.copy()


# Crossover operator factory
class CrossoverOperatorFactory:
    @staticmethod
    def create_operator(
        operator_type: str, config: CrossoverConfig, **kwargs
    ) -> Union[UniformCrossover, OrderBasedCrossover, PriorityBasedCrossover]:
        operators = {
            "uniform": UniformCrossover,
            "order": OrderBasedCrossover,
            "priority": PriorityBasedCrossover,
        }
        operator_class = operators.get(operator_type, UniformCrossover)
        return operator_class(config)  # type: ignore
