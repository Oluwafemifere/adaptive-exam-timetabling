# scheduling_engine/genetic_algorithm/__init__.py

"""
Genetic Algorithm module initialization.
Implements the GA phase of the hybrid approach for evolving variable selectors.
"""

from .chromosome import (
    VariableSelectorChromosome,
    ExamPriorityGene,
    GPNode,
    TerminalNode,
    FunctionNode,
)
from .population import Population, PopulationStatistics, PopulationManager
from .fitness import FitnessEvaluator, FitnessResult, FitnessConfig
from .evolution_manager import (
    EvolutionManager,
    EvolutionConfig,
    EvolutionResult,
    GenerationResult,
)
from .operators import *

__all__ = [
    # Core GA components
    "VariableSelectorChromosome",
    "ExamPriorityGene",
    "GPNode",
    "TerminalNode",
    "FunctionNode",
    "Population",
    "PopulationStatistics",
    "PopulationManager",
    "FitnessEvaluator",
    "FitnessResult",
    "FitnessConfig",
    "EvolutionManager",
    "EvolutionConfig",
    "EvolutionResult",
    "GenerationResult",
    # Genetic operators
    "CrossoverOperator",
    "UniformCrossover",
    "OrderBasedCrossover",
    "PriorityBasedCrossover",
    "MutationOperator",
    "PriorityMutation",
    "GaussianPriorityMutation",
    "SelectionOperator",
    "TournamentSelection",
    "EliteSelection",
]
