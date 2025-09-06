# scheduling_engine/genetic_algorithm/operators/__init__.py

"""
Genetic Algorithm Operators Package.

Implements crossover, mutation, and selection operators for exam scheduling optimization
following Nguyen et al. 2024 research paper specifications.
"""

from typing import List, Dict, Any, Optional, Tuple, Union
import logging

from .crossover import (
    CrossoverOperator,
    CrossoverConfig,
    UniformCrossover,
    OrderBasedCrossover,
    PriorityBasedCrossover,
    CrossoverOperatorFactory,
)

from .mutation import (
    MutationOperator,
    MutationConfig,
    PriorityMutation,
    GaussianPriorityMutation,
    MutationOperatorFactory,
)

from .selection import (
    SelectionOperator,
    SelectionConfig,
    TournamentSelection,
    RouletteWheelSelection,
    RankSelection,
    StochasticUniversalSampling,
    EliteSelection,
    FitnessProportionalSelection,
    AdaptiveSelection,
    MultiObjectiveSelection,
    HybridSelection,
    SelectionOperatorFactory,
    SelectionUtils,
)

logger = logging.getLogger(__name__)

# Research paper parameter constants
RESEARCH_PAPER_PARAMS: Dict[str, Any] = {
    "crossover_rate": 0.9,  # 90% as specified
    "mutation_rate": 0.1,  # 10% as specified
    "tournament_size": 5,  # Size 5 as specified
    "elite_proportion": 0.1,  # 10% elite preservation
    "population_size_range": (50, 200),  # Adaptive population sizing
}

# Default operator configurations based on research paper
DEFAULT_CROSSOVER_CONFIG = CrossoverConfig(
    crossover_rate=float(RESEARCH_PAPER_PARAMS["crossover_rate"]),
    priority_blend_factor=0.6,
    preserve_elite_genes=True,
    repair_offspring=True,
    diversity_preservation=True,
    constraint_aware_crossover=True,
)

DEFAULT_MUTATION_CONFIG = MutationConfig(
    mutation_rate=float(RESEARCH_PAPER_PARAMS["mutation_rate"]),
    priority_mutation_strength=0.3,
    assignment_mutation_rate=0.2,
    adaptive_mutation=True,
    constraint_guided_mutation=True,
    repair_mutations=True,
    diversity_preservation=True,
)

DEFAULT_SELECTION_CONFIG = SelectionConfig(
    tournament_size=int(RESEARCH_PAPER_PARAMS["tournament_size"]),
    elite_proportion=float(RESEARCH_PAPER_PARAMS["elite_proportion"]),
    diversity_preservation=True,
    fitness_sharing=True,
    pressure_factor=1.2,
    selection_strategy="tournament",
)

# Define operator set type
OperatorSet = Dict[str, Union[CrossoverOperator, MutationOperator, SelectionOperator]]


# Factory functions for easy operator creation
def create_default_operators() -> OperatorSet:
    """Create default operator set based on research paper specifications"""
    return {
        "crossover": CrossoverOperatorFactory.create_operator(
            "priority", DEFAULT_CROSSOVER_CONFIG
        ),
        "mutation": MutationOperatorFactory.create_operator(
            "priority", DEFAULT_MUTATION_CONFIG
        ),
        "selection": SelectionOperatorFactory.create_operator(
            "tournament", DEFAULT_SELECTION_CONFIG
        ),
    }


def create_research_paper_operators() -> OperatorSet:
    """Create operators with exact research paper specifications"""
    return {
        "crossover": CrossoverOperatorFactory.create_operator(
            "priority", DEFAULT_CROSSOVER_CONFIG
        ),
        "mutation": MutationOperatorFactory.create_operator(
            "priority", DEFAULT_MUTATION_CONFIG
        ),
        "selection": SelectionOperatorFactory.create_operator(
            "tournament", DEFAULT_SELECTION_CONFIG
        ),
    }


def create_adaptive_operators() -> OperatorSet:
    """Create adaptive operators for dynamic strategy selection"""
    return {
        "crossover": CrossoverOperatorFactory.create_operator(
            "priority", DEFAULT_CROSSOVER_CONFIG
        ),
        "mutation": MutationOperatorFactory.create_operator(
            "priority", DEFAULT_MUTATION_CONFIG
        ),
        "selection": SelectionOperatorFactory.create_operator(
            "tournament", DEFAULT_SELECTION_CONFIG
        ),
    }


# Operator performance tracking
class OperatorPerformanceTracker:
    """Track performance of different operator combinations"""

    def __init__(self) -> None:
        self.performance_history: List[Dict[str, Any]] = []
        self.operator_statistics: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
            "crossover": {},
            "mutation": {},
            "selection": {},
        }

    def record_generation_performance(
        self,
        generation: int,
        operators_used: Dict[str, str],
        population_metrics: Dict[str, float],
        best_fitness: float,
        diversity: float,
    ) -> None:
        """Record performance metrics for a generation"""
        entry: Dict[str, Any] = {
            "generation": generation,
            "operators": operators_used.copy(),
            "best_fitness": best_fitness,
            "diversity": diversity,
            "population_metrics": population_metrics.copy(),
        }

        self.performance_history.append(entry)

        # Update operator statistics
        for operator_type, operator_name in operators_used.items():
            stats_for_type = self.operator_statistics.setdefault(operator_type, {})
            stats_for_name = stats_for_type.setdefault(operator_name, [])
            stats_for_name.append(
                {
                    "fitness": best_fitness,
                    "diversity": diversity,
                    "generation": generation,
                }
            )

    def get_best_operator_combination(self) -> Dict[str, str]:
        """Get the operator combination with best average performance"""
        try:
            if not self.performance_history:
                return {
                    "crossover": "priority",
                    "mutation": "priority",
                    "selection": "tournament",
                }

            # Analyze recent performance (last 20% of generations)
            recent_count = max(1, len(self.performance_history) // 5)
            recent_history = self.performance_history[-recent_count:]

            # Group by operator combination
            combo_performance: Dict[Tuple[Tuple[str, str], ...], List[float]] = {}

            for entry in recent_history:
                operators: Dict[str, str] = entry.get("operators", {})
                # Make a stable key: tuple of (type,name) sorted by type
                combo_key = tuple(sorted(operators.items()))
                combo_performance.setdefault(combo_key, []).append(
                    entry["best_fitness"]
                )

            # Find best average performance
            best_combo: Optional[Dict[str, str]] = None
            best_avg_fitness = float("-inf")

            for combo_key, fitness_values in combo_performance.items():
                avg_fitness = sum(fitness_values) / len(fitness_values)
                if avg_fitness > best_avg_fitness:
                    best_avg_fitness = avg_fitness
                    best_combo = dict(combo_key)

            return best_combo or {
                "crossover": "priority",
                "mutation": "priority",
                "selection": "tournament",
            }

        except Exception as e:
            logger.error(f"Error getting best operator combination: {e}")
            return {
                "crossover": "priority",
                "mutation": "priority",
                "selection": "tournament",
            }


# Utility functions
def validate_operator_compatibility(
    crossover_op: CrossoverOperator,
    mutation_op: MutationOperator,
    selection_op: SelectionOperator,
) -> Dict[str, Any]:
    """Validate that operators are compatible with each other"""
    compatibility: Dict[str, Any] = {
        "is_compatible": True,
        "warnings": [],
        "recommendations": [],
    }

    try:
        # Check parameter compatibility
        if hasattr(crossover_op, "config") and hasattr(mutation_op, "config"):
            try:
                cr = getattr(crossover_op.config, "crossover_rate", 0.0)
                mr = getattr(mutation_op.config, "mutation_rate", 0.0)
                total_rate = float(cr or 0.0) + float(mr or 0.0)
                if total_rate > 1.1:  # Allow small tolerance
                    compatibility["warnings"].append(
                        f"High total operator rate: {total_rate:.2f} (crossover + mutation)"
                    )
            except Exception:
                # ignore conversion errors and continue
                pass

        # Check selection pressure compatibility
        if hasattr(selection_op, "config"):
            ts = getattr(selection_op.config, "tournament_size", None)
            if isinstance(ts, int) and ts > 10:
                compatibility["warnings"].append(
                    "High tournament size may increase selection pressure significantly"
                )

        # Adaptive operator recommendations
        adaptive_operators: List[str] = []
        if "Adaptive" in str(type(crossover_op)):
            adaptive_operators.append("crossover")
        if "Adaptive" in str(type(mutation_op)):
            adaptive_operators.append("mutation")
        if "Adaptive" in str(type(selection_op)):
            adaptive_operators.append("selection")

        if len(adaptive_operators) >= 2:
            compatibility["recommendations"].append(
                f"Multiple adaptive operators detected: {adaptive_operators}. "
                "Consider using fixed operators for stability."
            )

        return compatibility

    except Exception as e:
        return {
            "is_compatible": False,
            "warnings": [f"Compatibility check error: {str(e)}"],
            "recommendations": [],
        }


def get_recommended_operator_parameters(
    problem_size: int, constraint_complexity: str = "medium"
) -> Dict[str, Any]:
    """Get recommended operator parameters based on problem characteristics"""
    try:
        recommendations: Dict[str, Any] = {}

        # Crossover rate recommendations
        if problem_size < 50:
            recommendations["crossover_rate"] = 0.8
        elif problem_size < 200:
            recommendations["crossover_rate"] = 0.9  # Research paper default
        else:
            recommendations["crossover_rate"] = 0.95  # Higher for large problems

        # Mutation rate recommendations
        if constraint_complexity == "low":
            recommendations["mutation_rate"] = 0.05
        elif constraint_complexity == "medium":
            recommendations["mutation_rate"] = 0.1  # Research paper default
        else:
            recommendations["mutation_rate"] = 0.15  # Higher for complex constraints

        # Tournament size recommendations
        if problem_size < 30:
            recommendations["tournament_size"] = 3
        elif problem_size < 100:
            recommendations["tournament_size"] = 5  # Research paper default
        else:
            recommendations["tournament_size"] = 7  # Larger for big problems

        # Elite proportion recommendations
        recommendations["elite_proportion"] = min(
            0.15, max(0.05, 10 / max(1, problem_size))
        )

        return recommendations

    except Exception as e:
        logger.error(f"Error getting recommended parameters: {e}")
        return {
            "crossover_rate": 0.9,
            "mutation_rate": 0.1,
            "tournament_size": 5,
            "elite_proportion": 0.1,
        }


# Export all operators and utilities
__all__ = [
    # Crossover
    "CrossoverOperator",
    "CrossoverConfig",
    "UniformCrossover",
    "OrderBasedCrossover",
    "PriorityBasedCrossover",
    "CrossoverOperatorFactory",
    # Mutation
    "MutationOperator",
    "MutationConfig",
    "PriorityMutation",
    "GaussianPriorityMutation",
    "MutationOperatorFactory",
    # Selection
    "SelectionOperator",
    "SelectionConfig",
    "TournamentSelection",
    "RouletteWheelSelection",
    "RankSelection",
    "StochasticUniversalSampling",
    "EliteSelection",
    "FitnessProportionalSelection",
    "AdaptiveSelection",
    "MultiObjectiveSelection",
    "HybridSelection",
    "SelectionOperatorFactory",
    "SelectionUtils",
    # Configurations and factories
    "RESEARCH_PAPER_PARAMS",
    "DEFAULT_CROSSOVER_CONFIG",
    "DEFAULT_MUTATION_CONFIG",
    "DEFAULT_SELECTION_CONFIG",
    "create_default_operators",
    "create_research_paper_operators",
    "create_adaptive_operators",
    "OperatorPerformanceTracker",
    # Utilities
    "validate_operator_compatibility",
    "get_recommended_operator_parameters",
]
