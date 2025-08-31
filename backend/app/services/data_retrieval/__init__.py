# backend/app/services/data_retrieval/__init__.py

"""
Data retrieval services package

This package contains services for retrieving and preparing data
for the scheduling engine from the database.
"""

from .scheduling_data import SchedulingData
from .conflict_analysis import ConflictAnalysis
from .helpers import refresh_materialized_view, batch_query_ids, iso_date_range

# New data retrieval modules
from .academic_data import AcademicData
from .user_data import UserData
from .infrastructure_data import InfrastructureData
from .job_data import JobData
from .constraint_data import ConstraintData
from .audit_data import AuditData
from .file_upload_data import FileUploadData
from .timetable_edit_data import TimetableEditData

__all__ = [
    # Core modules (existing)
    "SchedulingData",
    "ConflictAnalysis",
    "refresh_materialized_view",
    "batch_query_ids",
    "iso_date_range",
    # New data retrieval modules
    "AcademicData",
    "UserData",
    "InfrastructureData",
    "JobData",
    "ConstraintData",
    "AuditData",
    "FileUploadData",
    "TimetableEditData",
]
