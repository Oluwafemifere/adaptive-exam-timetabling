# backend/app/services/seeding/__init__.py

"""
Seeding Services Package

This package consolidates all services related to the data seeding and staging process.
It provides a single point of access for managing seeding sessions, handling file uploads
for seeding, and interacting with the staging area where data is prepared before being
committed to the main application tables.

Modules:
- data_seeding_service: Manages the lifecycle of data seeding sessions and retrieves staged data.
- staging_service: Provides an interface for adding, updating, and deleting records in the
  individual staging tables.

Exposed Classes:
- DataSeedingService: The primary service for orchestration of data seeding operations.
- StagingService: The service for direct manipulation of staged data records.
"""

from .data_seeding_service import DataSeedingService
from .staging_service import StagingService
from .file_upload_service import FileUploadService

__all__ = [
    "DataSeedingService",
    "StagingService",
    "FileUploadService",
]
