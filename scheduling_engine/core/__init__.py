# scheduling_engine/core/__init__.py

"""
Core module for scheduling engine data structures and interfaces
"""

from .problem_model import (
    ExamSchedulingProblem,
    Exam,
    TimeSlot,
    Room,
    Student,
)
from .solution import TimetableSolution, ExamAssignment, SolutionStatus
from .constraint_registry import ConstraintRegistry, ConstraintDefinition
from .metrics import SolutionMetrics, QualityScore, PerformanceMetrics

__all__ = [
    # Problem model
    "ExamSchedulingProblem",
    "Exam",
    "TimeSlot",
    "Room",
    "Student",
    # Solution model
    "TimetableSolution",
    "ExamAssignment",
    "SolutionStatus",
    # Constraint system
    "ConstraintRegistry",
    "ConstraintDefinition",
    # Metrics and evaluation
    "SolutionMetrics",
    "QualityScore",
    "PerformanceMetrics",
]
