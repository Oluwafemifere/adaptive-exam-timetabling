"""

Safe Operators Module - DEAP-Integrated genetic operators without circular imports.

This module fixes circular import issues and implements constraint-aware
genetic operators that work with the safe chromosome implementation.

"""

import random
import logging
from typing import List, Tuple, Any, Optional
import numpy as np

# Safe imports - no circular dependencies
from .deap_setup import is_deap_available, get_deap_fitness_max
from .types import PruningDecisions, safe_copy_dict, safe_copy_set

# Import DEAPIndividual only for type checking
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .chromosome import DEAPIndividual

logger = logging.getLogger(__name__)


class ConstraintAwareCrossover:
    """
    FIXED: DEAP-compatible constraint-aware crossover operator.

    Fixes:
    - No circular imports
    - Safe copying operations
    - Proper constraint preservation
    - GENE LENGTH VALIDATION and empty individual handling
    """

    def __init__(self, alpha: float = 0.3, adaptive: bool = True):
        self.base_alpha = alpha
        self.adaptive = adaptive

    def get_fitness_value(self, individual: "DEAPIndividual") -> float:
        """Safely get fitness value from individual."""
        try:
            if (
                hasattr(individual, "fitness")
                and individual.fitness.valid
                and hasattr(individual.fitness, "values")
                and len(individual.fitness.values) > 0
            ):
                return float(individual.fitness.values[0])
        except (IndexError, TypeError, ValueError):
            pass
        return 0.0

    def _create_valid_individual(self, target_length: int) -> "DEAPIndividual":
        """Create a valid individual with the target length."""
        # Import here to avoid circular imports
        from .chromosome import DEAPIndividual

        if target_length <= 0:
            target_length = 16  # Minimal safe length

        genes = [random.uniform(0.0, 1.0) for _ in range(target_length)]
        individual = DEAPIndividual(genes)
        return individual

    def __call__(
        self, parent1: "DEAPIndividual", parent2: "DEAPIndividual"
    ) -> Tuple["DEAPIndividual", "DEAPIndividual"]:
        """FIXED: Perform constraint-aware adaptive blend crossover with gene length validation."""

        # CRITICAL FIX: Handle gene length mismatches and empty individuals
        if len(parent1) != len(parent2) or len(parent1) == 0 or len(parent2) == 0:
            logger.error(
                f"Gene length mismatch or empty: {len(parent1)} vs {len(parent2)}"
            )

            # Handle empty individuals
            if len(parent1) == 0:
                parent1 = self._create_valid_individual(
                    len(parent2) if len(parent2) > 0 else 16
                )
            if len(parent2) == 0:
                parent2 = self._create_valid_individual(
                    len(parent1) if len(parent1) > 0 else 16
                )

            # Handle length mismatches
            if len(parent1) != len(parent2):
                min_len = min(len(parent1), len(parent2))
                if min_len > 0:
                    # Truncate to minimum length
                    parent1_genes = list(parent1[:min_len])
                    parent2_genes = list(parent2[:min_len])

                    from .chromosome import DEAPIndividual

                    parent1 = DEAPIndividual(parent1_genes)
                    parent2 = DEAPIndividual(parent2_genes)
                else:
                    # Both are problematic, create new ones
                    parent1 = self._create_valid_individual(16)
                    parent2 = self._create_valid_individual(16)

            logger.warning(
                f"Fixed length mismatch: both parents now have {len(parent1)} genes"
            )

        # ADDITIONAL SAFETY CHECK: Ensure both parents have valid lengths
        if len(parent1) == 0 or len(parent2) == 0:
            logger.error(
                "Still have empty individuals after fixing - creating new ones"
            )
            parent1 = self._create_valid_individual(16)
            parent2 = self._create_valid_individual(16)

        # Calculate adaptive alpha if enabled
        if self.adaptive:
            constraint_similarity = self._calculate_constraint_compatibility(
                parent1, parent2
            )
            fitness_diff = abs(
                (self.get_fitness_value(parent1) if parent1.fitness.valid else 0)
                - (self.get_fitness_value(parent2) if parent2.fitness.valid else 0)
            )
            alpha = min(
                0.8, self.base_alpha + 0.3 * constraint_similarity + 0.2 * fitness_diff
            )
        else:
            alpha = self.base_alpha

        # Create offspring using safe copying
        try:
            offspring1 = parent1.copy()
            offspring2 = parent2.copy()
        except Exception as e:
            logger.error(f"Error copying parents: {e}")
            # Fallback to creating new individuals
            offspring1 = self._create_valid_individual(len(parent1))
            offspring2 = self._create_valid_individual(len(parent2))

        # Identify constraint-critical gene segments
        critical_segments = self._identify_critical_gene_segments(len(parent1))

        # Perform constraint-aware blend crossover
        for i in range(len(parent1)):
            is_critical = any(start <= i < end for start, end in critical_segments)

            if is_critical:
                # More conservative crossover for critical genes
                local_alpha = alpha * 0.5
                preservation_prob = 0.3

                if random.random() < preservation_prob:
                    # Preserve one parent's gene completely
                    if random.random() < 0.5:
                        offspring1[i] = parent1[i]
                        offspring2[i] = parent2[i]
                    else:
                        offspring1[i] = parent2[i]
                        offspring2[i] = parent1[i]
                else:
                    # Conservative blend for critical genes
                    gamma = (1 + 2 * local_alpha) * random.random() - local_alpha
                    gamma = max(-0.3, min(0.3, gamma))  # Limit range

                    offspring1[i] = gamma * parent1[i] + (1 - gamma) * parent2[i]
                    offspring2[i] = gamma * parent2[i] + (1 - gamma) * parent1[i]
            else:
                # Regular blend crossover for non-critical genes
                gamma = (1 + 2 * alpha) * random.random() - alpha

                offspring1[i] = gamma * parent1[i] + (1 - gamma) * parent2[i]
                offspring2[i] = gamma * parent2[i] + (1 - gamma) * parent1[i]

            # Ensure values stay in [0, 1] range
            offspring1[i] = max(0.0, min(1.0, offspring1[i]))
            offspring2[i] = max(0.0, min(1.0, offspring2[i]))

        # Reset fitness for offspring
        try:
            del offspring1.fitness.values  # Proper DEAP way to invalidate fitness
            del offspring2.fitness.values
        except (AttributeError, TypeError):
            # Fallback if fitness deletion fails
            if hasattr(offspring1, "fitness"):
                offspring1.fitness.values = ()
                offspring1.fitness.valid = False
            if hasattr(offspring2, "fitness"):
                offspring2.fitness.values = ()
                offspring2.fitness.valid = False

        offspring1.age = 0
        offspring2.age = 0

        # Safe blending of pruning decisions
        offspring1.pruning_decisions = self._blend_pruning_decisions_safe(
            parent1.pruning_decisions, parent2.pruning_decisions, 0.7
        )
        offspring2.pruning_decisions = self._blend_pruning_decisions_safe(
            parent2.pruning_decisions, parent1.pruning_decisions, 0.7
        )

        logger.debug(
            f"Constraint-aware crossover: alpha={alpha:.3f}, critical_segments={len(critical_segments)}"
        )

        return offspring1, offspring2

    def _calculate_constraint_compatibility(
        self, parent1: "DEAPIndividual", parent2: "DEAPIndividual"
    ) -> float:
        """Calculate constraint compatibility between parents."""
        if not (parent1.fitness.valid and parent2.fitness.valid):
            return 0.5

        violations1 = getattr(parent1, "constraint_violations", 0)
        violations2 = getattr(parent2, "constraint_violations", 0)
        critical1 = getattr(parent1, "critical_constraint_violations", 0)
        critical2 = getattr(parent2, "critical_constraint_violations", 0)

        violation_similarity = 1.0 / (1.0 + abs(violations1 - violations2))
        critical_similarity = 1.0 / (1.0 + abs(critical1 - critical2) * 2.0)

        return (violation_similarity + critical_similarity) / 2.0

    def _identify_critical_gene_segments(
        self, gene_length: int
    ) -> List[Tuple[int, int]]:
        """Identify gene segments that correspond to constraint-critical variables."""
        segments = []

        # Exam priorities are typically critical (first 20% of genes)
        exam_priority_end = int(gene_length * 0.2)
        segments.append((0, exam_priority_end))

        # High-preference assignments (middle segment)
        room_start = int(gene_length * 0.25)
        room_end = int(gene_length * 0.65)
        segments.append((room_start, room_end))

        return segments

    def _blend_pruning_decisions_safe(
        self,
        primary_pruning: Optional[PruningDecisions],
        secondary_pruning: Optional[PruningDecisions],
        primary_weight: float,
    ) -> PruningDecisions:
        """Safely blend pruning decisions while preserving constraint-critical variables."""
        if not primary_pruning or not secondary_pruning:
            return primary_pruning or PruningDecisions()

        # Start with safe copy of primary parent's decisions
        blended = PruningDecisions(
            pruned_x_vars=safe_copy_set(primary_pruning.pruned_x_vars),
            pruned_y_vars=safe_copy_set(primary_pruning.pruned_y_vars),
            pruned_u_vars=safe_copy_set(primary_pruning.pruned_u_vars),
            constraint_relaxations=safe_copy_dict(
                primary_pruning.constraint_relaxations
            ),
            critical_x_vars=safe_copy_set(primary_pruning.critical_x_vars),
            critical_y_vars=safe_copy_set(primary_pruning.critical_y_vars),
            critical_u_vars=safe_copy_set(primary_pruning.critical_u_vars),
        )

        # Merge critical variables from both parents (union for safety)
        blended.critical_x_vars.update(secondary_pruning.critical_x_vars)
        blended.critical_y_vars.update(secondary_pruning.critical_y_vars)
        blended.critical_u_vars.update(secondary_pruning.critical_u_vars)

        # Probabilistically add from secondary parent (but never prune critical variables)
        secondary_weight = 1.0 - primary_weight

        for var in secondary_pruning.pruned_x_vars:
            if random.random() < secondary_weight and blended.is_safe_to_prune(
                "x", var
            ):
                blended.pruned_x_vars.add(var)

        for var in secondary_pruning.pruned_y_vars:
            if random.random() < secondary_weight and blended.is_safe_to_prune(
                "y", var
            ):
                blended.pruned_y_vars.add(var)

        for var in secondary_pruning.pruned_u_vars:
            if random.random() < secondary_weight and blended.is_safe_to_prune(
                "u", var
            ):
                blended.pruned_u_vars.add(var)

        # Remove any accidentally pruned critical variables
        blended.pruned_x_vars -= blended.critical_x_vars
        blended.pruned_y_vars -= blended.critical_y_vars
        blended.pruned_u_vars -= blended.critical_u_vars

        # Blend constraint relaxations conservatively
        for (
            constraint_id,
            relaxation,
        ) in secondary_pruning.constraint_relaxations.items():
            if constraint_id in blended.constraint_relaxations:
                current_relaxation = blended.constraint_relaxations[constraint_id]
                blended.constraint_relaxations[constraint_id] = min(
                    current_relaxation, relaxation
                )
            elif random.random() < secondary_weight * 0.5:
                blended.constraint_relaxations[constraint_id] = relaxation

        return blended


class ConstraintAwareMutation:
    """
    FIXED: DEAP-compatible constraint-aware mutation operator.

    Fixes:
    - No circular imports
    - Safe constraint-aware mutation
    - Proper individual handling
    """

    def __init__(self, base_sigma: float = 0.1, indpb: float = 0.2):
        self.base_sigma = base_sigma
        self.indpb = indpb

    def __call__(self, individual: "DEAPIndividual") -> Tuple["DEAPIndividual"]:
        """Perform constraint-aware mutation."""
        mutated = individual.copy()

        # Calculate constraint-based mutation adjustment
        constraint_factor = self._calculate_constraint_mutation_factor(individual)
        critical_segments = self._identify_critical_gene_segments(len(individual))

        for i in range(len(mutated)):
            # Determine mutation probability based on constraint criticality
            is_critical = any(start <= i < end for start, end in critical_segments)

            if is_critical:
                mutation_prob = self.indpb * 0.5
                mutation_strength = self.base_sigma * 0.3
            else:
                mutation_prob = self.indpb
                mutation_strength = self.base_sigma

            if random.random() < mutation_prob:
                adaptive_sigma = mutation_strength * constraint_factor

                if is_critical:
                    # More conservative mutation for critical genes
                    mutation_value = random.gauss(0, adaptive_sigma)
                    mutation_value = max(-0.2, min(0.2, mutation_value))
                else:
                    mutation_value = random.gauss(0, adaptive_sigma)

                mutated[i] = max(0.0, min(1.0, mutated[i] + mutation_value))

        # Adaptively adjust pruning decisions
        mutated.pruning_decisions = self._adapt_pruning_decisions_post_mutation(
            individual, mutated
        )

        # Reset fitness
        try:
            del mutated.fitness.values
        except (AttributeError, TypeError):
            if hasattr(mutated, "fitness"):
                mutated.fitness.values = ()
                mutated.fitness.valid = False

        mutated.age = 0

        return (mutated,)  # DEAP expects tuple

    def _calculate_constraint_mutation_factor(
        self, individual: "DEAPIndividual"
    ) -> float:
        """Calculate mutation strength adjustment based on constraint violations."""
        regular_violations = getattr(individual, "constraint_violations", 0)
        critical_violations = getattr(individual, "critical_constraint_violations", 0)

        base_factor = min(2.0, 1.0 + regular_violations / 10.0)
        critical_factor = critical_violations * 0.5
        feasibility_factor = 1.0 - getattr(individual, "feasibility_score", 0.5)
        age_factor = min(1.0, individual.age * 0.1)

        total_factor = base_factor + critical_factor + feasibility_factor + age_factor

        return min(3.0, max(0.3, total_factor))

    def _identify_critical_gene_segments(
        self, gene_length: int
    ) -> List[Tuple[int, int]]:
        """Identify gene segments that correspond to constraint-critical variables."""
        segments = []

        exam_priority_end = int(gene_length * 0.2)
        segments.append((0, exam_priority_end))

        return segments

    def _adapt_pruning_decisions_post_mutation(
        self, original: "DEAPIndividual", mutated: "DEAPIndividual"
    ) -> PruningDecisions:
        """Adapt pruning decisions based on gene mutations while preserving constraints."""
        if not original.pruning_decisions:
            return PruningDecisions()

        # Start with safe copy of original pruning decisions
        adapted_pruning = PruningDecisions(
            pruned_x_vars=safe_copy_set(original.pruning_decisions.pruned_x_vars),
            pruned_y_vars=safe_copy_set(original.pruning_decisions.pruned_y_vars),
            pruned_u_vars=safe_copy_set(original.pruning_decisions.pruned_u_vars),
            constraint_relaxations=safe_copy_dict(
                original.pruning_decisions.constraint_relaxations
            ),
            critical_x_vars=safe_copy_set(original.pruning_decisions.critical_x_vars),
            critical_y_vars=safe_copy_set(original.pruning_decisions.critical_y_vars),
            critical_u_vars=safe_copy_set(original.pruning_decisions.critical_u_vars),
        )

        # Conservative adaptation: only reduce pruning for safety
        safe_pruned_x = {
            var
            for var in adapted_pruning.pruned_x_vars
            if adapted_pruning.is_safe_to_prune("x", var)
        }
        safe_pruned_y = {
            var
            for var in adapted_pruning.pruned_y_vars
            if adapted_pruning.is_safe_to_prune("y", var)
        }

        # Keep 80% of safe pruning decisions
        if safe_pruned_x:
            vars_to_keep = int(len(safe_pruned_x) * 0.8)
            if vars_to_keep < len(safe_pruned_x):
                kept_vars = set(random.sample(list(safe_pruned_x), vars_to_keep))
                adapted_pruning.pruned_x_vars = (
                    kept_vars | adapted_pruning.critical_x_vars
                )

        if safe_pruned_y:
            vars_to_keep = int(len(safe_pruned_y) * 0.8)
            if vars_to_keep < len(safe_pruned_y):
                kept_vars = set(random.sample(list(safe_pruned_y), vars_to_keep))
                adapted_pruning.pruned_y_vars = (
                    kept_vars | adapted_pruning.critical_y_vars
                )

        return adapted_pruning


class ConstraintAwareSelection:
    """
    FIXED: DEAP-compatible constraint-aware selection operator.

    Fixes:
    - No circular imports
    - Safe individual comparison
    - Proper constraint prioritization
    """

    def __init__(self, tournsize: int = 3, constraint_pressure: float = 0.3):
        self.tournsize = tournsize
        self.constraint_pressure = constraint_pressure

    def get_fitness_value(self, individual: "DEAPIndividual") -> float:
        """Safely get fitness value from individual."""
        try:
            if (
                hasattr(individual, "fitness")
                and individual.fitness.valid
                and hasattr(individual.fitness, "values")
                and len(individual.fitness.values) > 0
            ):
                return float(individual.fitness.values[0])
        except (IndexError, TypeError, ValueError):
            pass
        return 0.0

    def __call__(
        self, population: List["DEAPIndividual"], k: int, **kwargs
    ) -> List["DEAPIndividual"]:
        """Select individuals using constraint-aware tournament selection."""
        if not population:
            return []

        selected = []

        for _ in range(k):
            tournament_size = min(self.tournsize, len(population))
            tournament = random.sample(population, tournament_size)
            winner = self._conduct_constraint_aware_tournament(tournament)
            selected.append(winner)

        return selected

    def _conduct_constraint_aware_tournament(
        self, candidates: List["DEAPIndividual"]
    ) -> "DEAPIndividual":
        """Conduct tournament with constraint awareness."""
        best_candidate = None
        best_score = 0.0  # FIXED: Changed from float("-inf") to 0.0

        for candidate in candidates:
            score = self._calculate_constraint_aware_score(candidate)
            if score > best_score:
                best_score = score
                best_candidate = candidate

        return best_candidate or candidates[0]

    def _calculate_constraint_aware_score(self, candidate: "DEAPIndividual") -> float:
        """Calculate tournament score with constraint awareness."""
        # Critical constraint satisfaction bonus
        critical_violations = getattr(candidate, "critical_constraint_violations", 0)
        if critical_violations == 0:
            critical_bonus = 0.5
        else:
            critical_bonus = -critical_violations * 0.3

        # Regular constraint satisfaction
        regular_violations = getattr(candidate, "constraint_violations", 0)
        constraint_penalty = regular_violations * 0.1

        # Fitness component
        fitness_score = self.get_fitness_value(candidate)

        # Age penalty
        age_penalty = min(0.1, candidate.age * 0.01)

        # Combined score
        total_score = (
            fitness_score * (1.0 - self.constraint_pressure)
            + critical_bonus * self.constraint_pressure * 2.0
            - constraint_penalty * self.constraint_pressure
            - age_penalty
        )

        return total_score


# Specialized operator classes for different scenarios
class ExplorativeMutation(ConstraintAwareMutation):
    """More explorative mutation for escaping local optima."""

    def __init__(self):
        super().__init__(base_sigma=0.15, indpb=0.3)

    def _calculate_constraint_mutation_factor(
        self, individual: "DEAPIndividual"
    ) -> float:
        """More aggressive mutation factors for exploration."""
        base_factor = super()._calculate_constraint_mutation_factor(individual)

        if individual.age > 3:
            exploration_boost = min(1.5, individual.age * 0.2)
            base_factor *= exploration_boost

        return min(4.0, base_factor)


class ConservativeCrossover(ConstraintAwareCrossover):
    """Very conservative crossover for highly constrained problems."""

    def __init__(self):
        super().__init__(alpha=0.2, adaptive=True)


# Factory functions for different constraint scenarios
def create_conservative_operators():
    """Create operators for highly constrained problems."""
    return {
        "crossover": ConservativeCrossover(),
        "mutation": ConstraintAwareMutation(base_sigma=0.05, indpb=0.15),
        "selection": ConstraintAwareSelection(tournsize=5, constraint_pressure=0.5),
    }


def create_explorative_operators():
    """Create operators for escaping local optima."""
    return {
        "crossover": ConstraintAwareCrossover(alpha=0.4, adaptive=True),
        "mutation": ExplorativeMutation(),
        "selection": ConstraintAwareSelection(tournsize=3, constraint_pressure=0.2),
    }


def create_balanced_operators():
    """Create balanced operators for general use."""
    return {
        "crossover": ConstraintAwareCrossover(alpha=0.3, adaptive=True),
        "mutation": ConstraintAwareMutation(base_sigma=0.1, indpb=0.2),
        "selection": ConstraintAwareSelection(tournsize=3, constraint_pressure=0.3),
    }


def create_constraint_aware_toolbox(problem=None, constraint_encoder=None):
    """Create a complete toolbox with constraint-aware operators."""
    if not is_deap_available():
        logger.warning("DEAP not available - returning mock toolbox")
        return type("Toolbox", (), {})()

    try:
        from deap import base

        toolbox = base.Toolbox()

        # Constraint-aware operators
        constraint_crossover = ConstraintAwareCrossover(alpha=0.3, adaptive=True)
        constraint_mutation = ConstraintAwareMutation(base_sigma=0.1, indpb=0.2)
        constraint_selection = ConstraintAwareSelection(
            tournsize=3, constraint_pressure=0.3
        )

        toolbox.register("mate", constraint_crossover)
        toolbox.register("mutate", constraint_mutation)
        toolbox.register("select", constraint_selection)
        toolbox.register("map", map)

        return toolbox

    except ImportError:
        logger.error("DEAP import failed despite availability check")
        return type("Toolbox", (), {})()


def register_constraint_aware_operators(toolbox):
    """Register constraint-aware operators with DEAP toolbox."""
    if not is_deap_available():
        return

    crossover = ConstraintAwareCrossover(alpha=0.3, adaptive=True)
    mutation = ConstraintAwareMutation(base_sigma=0.1, indpb=0.2)
    selection = ConstraintAwareSelection(tournsize=3, constraint_pressure=0.3)

    toolbox.register("mate", crossover)
    toolbox.register("mutate", mutation)
    toolbox.register("select", selection)
