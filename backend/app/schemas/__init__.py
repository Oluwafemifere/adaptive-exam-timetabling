# app/schemas/__init__.py
"""Expose schema modules and primary Pydantic models for convenient imports."""

from . import auth, academic, jobs, scheduling, uploads

# Re-export commonly used classes for direct import
from .auth import TokenData, Token
from .jobs import TimetableJobBase, TimetableJobCreate, TimetableJobRead
from .scheduling import (
    TimeSlotRead,
    RoomAssignment,
    ExamRead,
    StaffRead,
    StaffUnavailabilityRead,
)
from .uploads import (
    UploadedFileBase,
    UploadedFileCreate,
    UploadedFileRead,
    FileUploadSessionBase,
    FileUploadSessionCreate,
    FileUploadSessionRead,
)

__all__ = [
    # modules
    "auth",
    "academic",
    "jobs",
    "scheduling",
    "uploads",
    # auth
    "TokenData",
    "Token",
    # jobs
    "TimetableJobBase",
    "TimetableJobCreate",
    "TimetableJobRead",
    # scheduling
    "TimeSlotRead",
    "RoomAssignment",
    "ExamRead",
    "StaffRead",
    "StaffUnavailabilityRead",
    # uploads
    "UploadedFileBase",
    "UploadedFileCreate",
    "UploadedFileRead",
    "FileUploadSessionBase",
    "FileUploadSessionCreate",
    "FileUploadSessionRead",
]
