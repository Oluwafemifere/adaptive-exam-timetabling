# backend/app/services/data_management/__init__.py
"""
Data Management Services Package.

Provides services for core CRUD operations and database seeding.
"""

from .core_data_service import CoreDataService


__all__ = [
    "CoreDataService",
]
