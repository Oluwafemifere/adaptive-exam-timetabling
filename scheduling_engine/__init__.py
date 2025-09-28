# scheduling_engine/__init__.py

"""
Scheduling Engine Package Initialization

This package implements a hybrid genetic-based constraint programming approach
for exam timetabling, based on the research paper:
"Genetic-based Constraint Programming for Resource Constrained Job Scheduling"
"""

from .config import (
    SchedulingEngineConfig,
    SolverPhase,
    OptimizationObjective,
    config,
    get_logger,
)

from .core import (
    ExamSchedulingProblem,
    TimetableSolution,
    ConstraintRegistry,
    SolutionMetrics,
)
from .cp_sat.model_builder import CPSATModelBuilder
from .cp_sat.solver_manager import CPSATSolverManager

__version__ = "1.0.0"
__author__ = "Baze University Exam Scheduling System"

# Package-level exports
__all__ = [
    # Configuration
    "SchedulingEngineConfig",
    "SolverPhase",
    "OptimizationObjective",
    "config",
    "get_logger",
    # Core components
    "ExamSchedulingProblem",
    "TimetableSolution",
    "ConstraintRegistry",
    "SolutionMetrics",
    "CPSATModelBuilder",
    "CPSATSolverManager",
]

# Initialize package-level logger
logger = get_logger("main")
logger.info(f"Scheduling Engine v{__version__} initialized")
