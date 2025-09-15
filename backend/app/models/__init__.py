# app/models/__init__.py

from .base import Base, TimestampMixin

from .users import (
    User,
    UserRole,
    UserRoleAssignment,
    UserNotification,
    SystemConfiguration,
    SystemEvent,
)

from .constraints import ConstraintCategory, ConstraintRule, ConfigurationConstraint

from .academic import (
    AcademicSession,
    Department,
    Faculty,
    Programme,
    Course,
    Student,
    CourseRegistration,
)


from .jobs import TimetableJob, TimetableVersion


from .file_uploads import FileUploadSession, UploadedFile
from .audit_logs import AuditLog
from .timetable_edits import TimetableEdit
from .infrastructure import Building, RoomType, Room, ExamRoom, ExamAllowedRoom
from .scheduling import (
    Exam,
    TimeSlot,
    Staff,
    ExamInvigilator,
    StaffUnavailability,
    TimetableAssignment,
    ExamDepartment,
)

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "UserRole",
    "UserRoleAssignment",
    "UserNotification",
    "SystemConfiguration",
    "SystemEvent",
    "ConstraintCategory",
    "ConstraintRule",
    "ConfigurationConstraint",
    "AcademicSession",
    "Department",
    "Faculty",
    "Programme",
    "Course",
    "Student",
    "CourseRegistration",
    "Building",
    "RoomType",
    "Room",
    "ExamRoom",
    "TimetableJob",
    "TimetableVersion",
    "Exam",
    "TimeSlot",
    "Staff",
    "ExamInvigilator",
    "StaffUnavailability",
    "FileUploadSession",
    "AuditLog",
    "TimetableEdit",
    "ExamAllowedRoom",
    "TimetableAssignment",
    "ExamDepartment",
    "UploadedFile",
]
