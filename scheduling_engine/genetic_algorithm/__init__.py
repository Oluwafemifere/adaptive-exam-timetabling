"""
DEAP-Integrated Constraint-Aware Genetic Algorithm Module

This module provides a complete refactored GA system using the DEAP framework
for implementing genetic algorithms with constraint-aware pruning and CP-SAT
solver hints generation.

Key Features:
- DEAP framework integration for all GA operations
- Constraint-aware variable pruning that preserves critical variables
- CP-SAT solver hints generation from GA solutions
- Multi-objective optimization with constraint prioritization
- Adaptive operators that adjust based on constraint satisfaction
- Comprehensive constraint violation tracking and reporting
"""

# Import DEAP if available
try:
    from deap import base, creator, tools, algorithms

    DEAP_AVAILABLE = True
    print("DEAP framework available and loaded successfully")
except ImportError:
    DEAP_AVAILABLE = False
    print("Warning: DEAP framework not available. Install with: pip install deap")

# Core components
from .chromosome import (
    DEAPIndividual,
    SchedulingPreferences,
    PruningDecisions,
    ChromosomeEncoder,
    ChromosomeDecoder,
)

from .fitness import (
    DEAPFitnessEvaluator,
    ConstraintAwareFitnessEvaluator,
    FitnessComponents,
    create_single_objective_evaluator,
    create_multi_objective_evaluator,
    create_constraint_aware_fitness_classes,
)

from .operators import (
    ConstraintAwareCrossover,
    ConstraintAwareMutation,
    ConstraintAwareSelection,
    create_constraint_aware_toolbox,
    register_constraint_aware_operators,
    create_conservative_operators,
    create_explorative_operators,
    create_balanced_operators,
)

from .population import (
    DEAPPopulation,
    DEAPPopulationManager,
    PopulationStatistics,
)

from .evolution_manager import (
    DEAPConstraintAwareEvolutionManager,
    ConstraintAwareGAParameters,
    ConstraintAwareEvolutionReport,
    create_constraint_aware_ga,
)

# Version and metadata
__version__ = "1.0.0"
__author__ = "AI Assistant"
__description__ = (
    "DEAP-integrated constraint-aware genetic algorithm for exam timetabling"
)

# Public API
__all__ = [
    # Core classes
    "DEAPIndividual",
    "DEAPPopulation",
    "DEAPConstraintAwareEvolutionManager",
    # Configuration classes
    "ConstraintAwareGAParameters",
    "SchedulingPreferences",
    "PruningDecisions",
    # Component classes
    "ChromosomeEncoder",
    "ChromosomeDecoder",
    "ConstraintAwareFitnessEvaluator",
    "DEAPPopulationManager",
    # Operator classes
    "ConstraintAwareCrossover",
    "ConstraintAwareMutation",
    "ConstraintAwareSelection",
    # Result classes
    "ConstraintAwareEvolutionReport",
    "PopulationStatistics",
    "FitnessComponents",
    # Factory functions
    "create_constraint_aware_ga",
    "create_constraint_aware_toolbox",
    "create_single_objective_evaluator",
    "create_multi_objective_evaluator",
    # Utility functions
    "register_constraint_aware_operators",
    "create_constraint_aware_fitness_classes",
    # Operator factory functions
    "create_conservative_operators",
    "create_explorative_operators",
    "create_balanced_operators",
    # Constants
    "DEAP_AVAILABLE",
]


def setup_deap_environment():
    """
    Setup DEAP environment with constraint-aware fitness classes.

    This function should be called once before using the GA system
    to ensure all DEAP creators are properly initialized.
    """
    if not DEAP_AVAILABLE:
        print("Warning: DEAP not available. Some functionality will be limited.")
        return False

    # Create constraint-aware fitness classes
    create_constraint_aware_fitness_classes()

    print("DEAP environment setup completed successfully")
    return True


def get_default_parameters(
    problem_type: str = "exam_timetabling",
) -> ConstraintAwareGAParameters:
    """
    Get default parameters optimized for specific problem types.

    Args:
        problem_type: Type of problem ("exam_timetabling", "course_timetabling", etc.)

    Returns:
        ConstraintAwareGAParameters with optimized defaults
    """
    if problem_type == "exam_timetabling":
        return ConstraintAwareGAParameters(
            population_size=60,
            max_generations=150,
            pruning_aggressiveness=0.25,
            constraint_pressure=0.4,
            min_feasible_ratio=0.35,
            critical_constraint_weight=0.35,
            crossover_prob=0.85,
            mutation_prob=0.25,
            adaptive_operators=True,
            feasibility_pressure_adaptation=True,
        )
    elif problem_type == "course_timetabling":
        return ConstraintAwareGAParameters(
            population_size=50,
            max_generations=120,
            pruning_aggressiveness=0.2,
            constraint_pressure=0.3,
            min_feasible_ratio=0.3,
            critical_constraint_weight=0.3,
            crossover_prob=0.8,
            mutation_prob=0.2,
            adaptive_operators=True,
            feasibility_pressure_adaptation=True,
        )
    else:
        # Generic timetabling defaults
        return ConstraintAwareGAParameters()


def validate_problem_compatibility(problem) -> bool:
    """
    Validate that the problem instance is compatible with the constraint-aware GA.

    Args:
        problem: Problem instance to validate

    Returns:
        True if compatible, False otherwise
    """
    required_attributes = ["exams", "rooms", "timeslots"]

    for attr in required_attributes:
        if not hasattr(problem, attr):
            print(f"Error: Problem missing required attribute '{attr}'")
            return False

    if not problem.exams:
        print("Error: Problem has no exams defined")
        return False

    if not problem.rooms:
        print("Error: Problem has no rooms defined")
        return False

    if not problem.timeslots:
        print("Error: Problem has no timeslots defined")
        return False

    print("Problem validation passed")
    return True


def create_quick_ga(
    problem, constraint_encoder, problem_type: str = "exam_timetabling"
):
    """
    Quick setup function to create a constraint-aware GA with sensible defaults.

    Args:
        problem: The scheduling problem instance
        constraint_encoder: The constraint encoder for CP-SAT integration
        problem_type: Type of problem for parameter optimization

    Returns:
        Configured DEAPConstraintAwareEvolutionManager ready to use
    """
    # Setup DEAP environment
    setup_deap_environment()

    # Validate problem
    if not validate_problem_compatibility(problem):
        raise ValueError("Problem instance is not compatible with constraint-aware GA")

    # Get optimized parameters
    parameters = get_default_parameters(problem_type)

    # Create GA instance
    ga = create_constraint_aware_ga(problem, constraint_encoder, **parameters.__dict__)

    print(
        f"Created constraint-aware GA for {problem_type} with {parameters.population_size} individuals"
    )
    return ga


# Example usage and documentation
USAGE_EXAMPLE = """
# Example usage of the DEAP-integrated constraint-aware GA

from your_deap_ga_module import create_quick_ga, ConstraintAwareGAParameters

# Setup (required once)
from your_deap_ga_module import setup_deap_environment
setup_deap_environment()

# Basic usage with default parameters
ga = create_quick_ga(problem, constraint_encoder, "exam_timetabling")
result = ga.solve()

print(f"GA completed successfully: {result.success}")
print(f"Best fitness: {result.best_fitness:.4f}")
print(f"Constraint violations: {result.final_constraint_violations}")
print(f"Feasibility rate: {result.final_feasibility_rate:.1%}")

# Advanced usage with custom parameters
custom_params = ConstraintAwareGAParameters(
    population_size=100,
    max_generations=200,
    constraint_pressure=0.5,
    critical_constraint_weight=0.4,
    adaptive_operators=True,
)

ga = create_constraint_aware_ga(problem, constraint_encoder, **custom_params.__dict__)
result = ga.solve()

# Extract CP-SAT solver hints and pruning decisions
solver_hints = ga.get_constraint_aware_solver_hints()
pruning_decisions = ga.get_constraint_aware_pruning_decisions()

print(f"Generated {len(solver_hints)} solver hints")
print(f"Pruned {pruning_decisions.get_total_pruned()} variables safely")

# Get detailed performance metrics
metrics = ga.get_constraint_performance_metrics()
print(f"Constraint satisfaction trend: {metrics['constraint_insights']['constraint_satisfaction_trend']:.3f}")
"""


def print_usage_example():
    """Print comprehensive usage example."""
    print("DEAP-Integrated Constraint-Aware GA Usage Example:")
    print("=" * 60)
    print(USAGE_EXAMPLE)


if __name__ == "__main__":
    print(f"DEAP Constraint-Aware GA Module v{__version__}")
    print(f"DEAP Available: {DEAP_AVAILABLE}")
    print()
    print_usage_example()
