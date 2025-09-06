# backend\app\__init__.py

"""Main application package for Adaptive Exam Timetabling System."""

# Core
from .core import (
    AppError,
    InfeasibleProblemError,
    JobAccessDeniedError,
    JobNotFoundError,
    SchedulingError,
)

# Services
from .services import (
    DatabaseSeeder,
    data_management,
    data_retrieval,
    data_validation,
    export,
    notification,
    scheduling,
)

__all__ = [
    # Core
    "AppError",
    "SchedulingError",
    "InfeasibleProblemError",
    "JobNotFoundError",
    "JobAccessDeniedError",
    # Services
    "scheduling",
    "notification",
    "export",
    "data_validation",
    "data_retrieval",
    "data_management",
    "DatabaseSeeder",
]
