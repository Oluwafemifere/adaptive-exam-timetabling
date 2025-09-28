# app/schemas/__init__.py
"""Expose schema modules and primary Pydantic models for convenient imports."""

from . import auth, academic, jobs, scheduling, uploads, versioning

# Re-export commonly used classes for direct import
from .auth import TokenData, Token
from .academic import (
    AcademicSessionRead,
    FacultyRead,
    DepartmentRead,
    ProgrammeRead,
    CourseRead,
    StudentRead,
    StudentEnrollmentRead,
    CourseRegistrationRead,
)
from .jobs import TimetableJobBase, TimetableJobCreate, TimetableJobRead
from .scheduling import (
    TimetableAssignmentRead,
    ExamRead,
    StaffRead,
    StaffUnavailabilityRead,
    TimetableGenerationRequest,
    TimetableGenerationResponse,
)
from .uploads import (
    UploadedFileBase,
    UploadedFileCreate,
    UploadedFileRead,
    FileUploadSessionBase,
    FileUploadSessionCreate,
    FileUploadSessionRead,
)
from .versioning import TimetableVersionRead, SessionTemplateRead


__all__ = [
    # modules
    "auth",
    "academic",
    "jobs",
    "scheduling",
    "uploads",
    "versioning",
    # auth
    "TokenData",
    "Token",
    # academic
    "AcademicSessionRead",
    "FacultyRead",
    "DepartmentRead",
    "ProgrammeRead",
    "CourseRead",
    "StudentRead",
    "StudentEnrollmentRead",
    "CourseRegistrationRead",
    # jobs
    "TimetableJobBase",
    "TimetableJobCreate",
    "TimetableJobRead",
    # scheduling
    "TimetableAssignmentRead",
    "ExamRead",
    "StaffRead",
    "StaffUnavailabilityRead",
    "TimetableGenerationRequest",
    "TimetableGenerationResponse",
    # uploads
    "UploadedFileBase",
    "UploadedFileCreate",
    "UploadedFileRead",
    "FileUploadSessionBase",
    "FileUploadSessionCreate",
    "FileUploadSessionRead",
    # versioning
    "TimetableVersionRead",
    "SessionTemplateRead",
]
