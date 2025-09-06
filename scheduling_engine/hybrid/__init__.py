# scheduling_engine/hybrid/__init__.py

"""
Hybrid Module for CP-SAT + Genetic Algorithm Integration.

This module implements the hybrid genetic-based constraint programming approach
from the research paper, combining CP-SAT for feasibility with genetic algorithms
for optimization through evolved variable selectors.

Components:
- Coordinator: Main orchestrator for the hybrid optimization pipeline
- Adaptive Controller: Dynamic parameter adjustment based on problem characteristics
- Incremental Optimizer: Handles manual edits and local solution refinement
- Solution Converter: Transforms between different solution representations

Key Features:
- Two-phase optimization (CP-SAT → GA)
- Adaptive parameter tuning
- Real-time solution editing
- Faculty-based partitioning support
- Solution format conversion
- Performance monitoring and statistics
"""

from .coordinator import (
    HybridCoordinator,
    OptimizationResults,
    OptimizationPhase,
    create_hybrid_coordinator,
)
from .adaptive_controller import (
    AdaptiveController,
    AdaptationTrigger,
    AdaptationStrategy,
    AdaptationEvent,
    PerformanceWindow,
    create_adaptive_controller,
)
from .incremental_optimizer import (
    IncrementalOptimizer,
    EditType,
    EditRequest,
    EditResult,
    OptimizationScope,
    RepairStrategy,
    IncrementalOptimizationResult,
    create_incremental_optimizer,
)
from .solution_converter import (
    SolutionConverter,
    ConversionFormat,
    ConversionResult,
    ConversionDirection,
    CPSATSolutionData,
    GeneticSolutionData,
    DatabaseSolutionData,
    create_solution_converter,
)

__all__ = [
    # Main coordinator
    "HybridCoordinator",
    "OptimizationResults",
    "OptimizationPhase",
    "create_hybrid_coordinator",
    # Adaptive controller
    "AdaptiveController",
    "AdaptationTrigger",
    "AdaptationStrategy",
    "AdaptationEvent",
    "PerformanceWindow",
    "create_adaptive_controller",
    # Incremental optimizer
    "IncrementalOptimizer",
    "EditType",
    "EditRequest",
    "EditResult",
    "OptimizationScope",
    "RepairStrategy",
    "IncrementalOptimizationResult",
    "create_incremental_optimizer",
    # Solution converter
    "SolutionConverter",
    "ConversionFormat",
    "ConversionResult",
    "ConversionDirection",
    "CPSATSolutionData",
    "GeneticSolutionData",
    "DatabaseSolutionData",
    "create_solution_converter",
]

# Package metadata
__version__ = "1.0.0"
__author__ = "Baze University Scheduling Engine Team"
__description__ = "Hybrid genetic-based constraint programming for exam timetabling"
