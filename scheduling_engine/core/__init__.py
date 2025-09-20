# scheduling_engine/core/__init__.py

"""
Core module for scheduling engine data structures and interfaces
"""

from .problem_model import (
    ExamSchedulingProblem,
    Exam,
    Timeslot,
    Room,
    Student,
)
from .solution import TimetableSolution, ExamAssignment, SolutionStatus
from .constraint_registry import ConstraintRegistry
from .metrics import SolutionMetrics, QualityScore, PerformanceMetrics
from scheduling_engine.core.constraint_types import (
    ConstraintType,
    ConstraintCategory,
    ConstraintViolation,
    ConstraintSeverity,
    ConstraintDefinition,
)

__all__ = [
    # Problem model
    "ExamSchedulingProblem",
    "Exam",
    "Timeslot",
    "Room",
    "Student",
    # Solution model
    "TimetableSolution",
    "ExamAssignment",
    "SolutionStatus",
    # Constraint system
    "ConstraintRegistry",
    # Constraint Types
    "ConstraintDefinition",
    "ConstraintType",
    "ConstraintCategory",
    "ConstraintViolation",
    "ConstraintSeverity",
    # Metrics and evaluation
    "SolutionMetrics",
    "QualityScore",
    "PerformanceMetrics",
]
