# backend/app/services/__init__.py

"""
Services package for the Adaptive Exam Timetabling System.
Contains all service modules for scheduling, notification, export, data validation,
data retrieval, and data management functionality.
"""

# Import sub-packages
from . import scheduling
from . import notification
from . import export
from . import data_validation
from . import data_retrieval
from . import data_management
from .session_setup_service import SessionSetupService


__all__ = [
    # Sub-packages
    "scheduling",
    "notification",
    "export",
    "data_validation",
    "data_retrieval",
    "data_management",
    # Main classes from data_management
    "SessionSetupService",
]
