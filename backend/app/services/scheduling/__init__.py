# backend/app/services/scheduling/__init__.py

"""
Consolidated scheduling services package with optimized components.
"""

# Core scheduling components
from .enhanced_engine_connector import (
    EnhancedSchedulingEngineConnector,
    ProblemInstance,
    OptimizationResult,
)

from .integrated_engine_manager import IntegratedSchedulingEngineManager

from .hybrid_optimization_coordinator import (
    HybridOptimizationCoordinator,
    OptimizationPhaseResult,
)

from .incremental_optimizer import IncrementalOptimizer

from .problem_instance_builder import (
    ProblemInstanceBuilder,
    CPSATModel,
    CPSATVariables,
    GAChromosome,
)

# Legacy compatibility imports
from .constraint_builder import ConstraintBuilder

# Create aliases for backward compatibility
SchedulingService = IntegratedSchedulingEngineManager
SchedulingEngineConnector = EnhancedSchedulingEngineConnector
IncrementalSolver = IncrementalOptimizer

__all__ = [
    # Primary interfaces
    "IntegratedSchedulingEngineManager",
    "EnhancedSchedulingEngineConnector",
    "HybridOptimizationCoordinator",
    "IncrementalOptimizer",
    "ProblemInstanceBuilder",
    # Data structures
    "ProblemInstance",
    "OptimizationResult",
    "OptimizationPhaseResult",
    "CPSATModel",
    "CPSATVariables",
    "GAChromosome",
    # Legacy/compatibility
    "ConstraintBuilder",
    "SchedulingService",
    "SchedulingEngineConnector",
    "IncrementalSolver",
]
