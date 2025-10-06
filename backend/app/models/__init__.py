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
    TimeSlotTemplate,  # Added
    TimeSlotTemplatePeriod,  # Added
    AssignmentChangeRequest,
    ConflictReport,
)
from .infrastructure import (
    Building,
    RoomType,
    Room,
)
from .users import (
    User,
    UserNotification,
    SystemConfiguration,
    SystemEvent,
    UserFilterPreset,
)
from .jobs import TimetableJob, TimetableJobExamDay
from .versioning import (
    TimetableVersion,
    VersionMetadata,
    VersionDependency,
    SessionTemplate,
    TimetableConflict,
)
from .constraints import (
    ConfigurationConstraint,
    ConstraintRule,
    ConstraintCategory,
)
from .audit_logs import AuditLog
from .file_uploads import FileUploadSession, UploadedFile
from .timetable_edits import TimetableEdit
from .hitl import TimetableScenario, TimetableLock

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
    "StudentEnrollment",
    "CourseRegistration",
    "CourseInstructor",
    # Scheduling models
    "Exam",
    "ExamDepartment",
    "Staff",
    "ExamInvigilator",
    "StaffUnavailability",
    "TimetableAssignment",
    "TimeSlotTemplate",
    "TimeSlotTemplatePeriod",
    "AssignmentChangeRequest",
    "ConflictReport",
    # Infrastructure models
    "Building",
    "RoomType",
    "Room",
    # User and system models
    "User",
    "UserNotification",
    "SystemConfiguration",
    "SystemEvent",
    "UserFilterPreset",  # Added
    # Job models
    "TimetableJob",
    "TimetableJobExamDay",  # Added
    # Versioning models
    "TimetableVersion",
    "VersionMetadata",
    "VersionDependency",
    "SessionTemplate",
    "TimetableConflict",
    # Constraint models
    "ConfigurationConstraint",
    "ConstraintRule",
    "ConstraintCategory",
    # Audit and file models
    "AuditLog",
    "FileUploadSession",
    "UploadedFile",
    "TimetableEdit",
    # HITL models
    "TimetableScenario",
    "TimetableLock",
]
