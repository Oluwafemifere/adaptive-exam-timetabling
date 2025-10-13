# backend/app/services/data_management/__init__.py

"""
Services for direct data manipulation and core entity management.
"""

from .core_data_service import CoreDataService
from .session_management_service import SessionManagementService  # <--- ADD THIS

__all__ = [
    "CoreDataService",
    "SessionManagementService",  # <--- AND ADD THIS
]
