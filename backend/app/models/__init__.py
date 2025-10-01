# app/models/__init__.py

from .base import Base
from .academic import (
    AcademicSession,
    Department,
    Faculty,
    Programme,
    Course,
    Student,
    StudentEnrollment,
    CourseRegistration,
    CourseInstructor,
)
from .scheduling import (
    Exam,
    ExamDepartment,
    Staff,
    ExamInvigilator,
    StaffUnavailability,
    TimetableAssignment,
)
from .infrastructure import (
    Building,
    RoomType,
    Room,
    ExamAllowedRoom,
)
from .users import (
    User,
    UserRole,
    UserRoleAssignment,
    UserNotification,
    SystemConfiguration,
    SystemEvent,
)
from .jobs import TimetableJob
from .versioning import (
    TimetableVersion,
    VersionMetadata,
    VersionDependency,
    SessionTemplate,
)
from .constraints import (
    ConfigurationConstraint,
    ConstraintRule,
    ConstraintCategory,
)
from .audit_logs import AuditLog
from .file_uploads import FileUploadSession, UploadedFile
from .timetable_edits import TimetableEdit

# Export all models for easy import
__all__ = [
    # Base
    "Base",
    # Academic models
    "AcademicSession",
    "Department",
    "Faculty",
    "Programme",
    "Course",
    "Student",
    "StudentEnrollment",  # New model
    "CourseRegistration",
    "CourseInstructor",
    # Scheduling models
    "Exam",
    "ExamDepartment",
    "Staff",
    "ExamInvigilator",
    "StaffUnavailability",
    "TimetableAssignment",
    # Infrastructure models
    "Building",
    "RoomType",
    "Room",
    "ExamAllowedRoom",
    # User and system models
    "User",
    "UserRole",
    "UserRoleAssignment",
    "UserNotification",
    "SystemConfiguration",
    "SystemEvent",
    # Job models
    "TimetableJob",
    # NEW: Versioning models
    "TimetableVersion",
    "VersionMetadata",
    "VersionDependency",
    "SessionTemplate",
    # Constraint models
    "ConfigurationConstraint",
    "ConstraintRule",
    "ConstraintCategory",
    # Audit and file models
    "AuditLog",
    "FileUploadSession",
    "UploadedFile",
    "TimetableEdit",
]
