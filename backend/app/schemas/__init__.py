# app/schemas/__init__.py
"""Expose schema modules and primary Pydantic models for convenient imports."""

from . import (
    auth,
    academic,
    jobs,
    scheduling,
    uploads,
    versioning,
    admin,
    system,
    infrastructure,
    users,
    role,
    notifications,
    portal,
)

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

from .admin import (
    JsonSeedingRequest,
    SeedingRequest,
    UploadSessionCreate,
)

from .jobs import TimetableJobBase, TimetableJobCreate, TimetableJobRead

from .scheduling import (
    TimetableAssignmentRead,
    ExamBase,
    ExamCreate,
    ExamUpdate,
    ExamRead,
    StaffRead,
    StaffUnavailabilityRead,
    TimeslotTemplate,
    SchedulingDataResponse,
    TimetableGenerationRequest,
    TimetableGenerationResponse,
    ConflictAnalysisResponse,
    ManualTimetableEditCreate,
    TimetableValidationRequest,
)

from .system import (
    SystemConfigBase,
    SystemConfigCreate,
    SystemConfigUpdate,
    SystemConfigRead,
    GenericResponse,
    AuditLogRead,
    PaginatedAuditLogResponse,
    ReportGenerateRequest,
)


from .uploads import (
    UploadedFileBase,
    UploadedFileCreate,
    UploadedFileRead,
    FileUploadSessionBase,
    FileUploadSessionCreate,
    FileUploadSessionRead,
)

from .versioning import (
    TimetableVersionRead,
    SessionTemplateRead,
    ScenarioCreate,
    ScenarioRead,
    ScenarioComparisonRequest,
)

from .infrastructure import (
    RoomBase,
    RoomCreate,
    RoomUpdate,
    RoomRead,
)

from .users import (
    UserBase,
    UserCreate,
    UserRead,
    UserManagementRecord,
    PaginatedUserResponse,
)

from .role import (
    RoleAssignment,
    UserRolesResponse,
    PermissionCheckResponse,
)

from .notifications import (
    NotificationRead,
    MarkNotificationsReadRequest,
)

from .portal import (
    ConflictReportCreate,
    RequestManage,
    ChangeRequestCreate,
    StaffAvailabilityUpdate,
)


__all__ = [
    # modules
    "auth",
    "academic",
    "jobs",
    "scheduling",
    "uploads",
    "versioning",
    "admin",
    "system",
    "infrastructure",
    "users",
    "role",
    "notifications",
    "portal",
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
    # admin
    "JsonSeedingRequest",
    "SeedingRequest",
    "UploadSessionCreate",
    # jobs
    "TimetableJobBase",
    "TimetableJobCreate",
    "TimetableJobRead",
    # scheduling
    "TimetableAssignmentRead",
    "ExamBase",
    "ExamCreate",
    "ExamUpdate",
    "ExamRead",
    "StaffRead",
    "StaffUnavailabilityRead",
    "TimeslotTemplate",
    "SchedulingDataResponse",
    "TimetableGenerationRequest",
    "TimetableGenerationResponse",
    "ConflictAnalysisResponse",
    "ManualTimetableEditCreate",
    "TimetableValidationRequest",
    # system
    "SystemConfigBase",
    "SystemConfigCreate",
    "SystemConfigUpdate",
    "SystemConfigRead",
    "GenericResponse",
    "AuditLogRead",
    "PaginatedAuditLogResponse",
    "ReportGenerateRequest",
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
    "ScenarioCreate",
    "ScenarioRead",
    "ScenarioComparisonRequest",
    # infrastructure
    "RoomBase",
    "RoomCreate",
    "RoomUpdate",
    "RoomRead",
    # users
    "UserBase",
    "UserCreate",
    "UserRead",
    "UserManagementRecord",
    "PaginatedUserResponse",
    # role
    "RoleAssignment",
    "UserRolesResponse",
    "PermissionCheckResponse",
    # notifications
    "NotificationRead",
    "MarkNotificationsReadRequest",
    # portal
    "ConflictReportCreate",
    "RequestManage",
    "ChangeRequestCreate",
    "StaffAvailabilityUpdate",
]
