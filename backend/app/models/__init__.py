# app/models/__init__.py
from .base import Base, TimestampMixin

from .users import (
    User, UserRole, UserRoleAssignment, UserNotification,
    SystemConfiguration, SystemEvent
)
from .constraints import ConstraintCategory, ConstraintRule, ConfigurationConstraint
from .academic import (
    AcademicSession, Department, Faculty, Programme,
    Course, Student, CourseRegistration
)
from .infrastructure import Building, RoomType, Room, ExamRoom
from .jobs import TimetableJob, TimetableVersion
from .scheduling import (
    Exam, TimeSlot, Staff, ExamInvigilator, StaffUnavailability
)

__all__ = [
    "Base", "TimestampMixin",
    "User", "UserRole", "UserRoleAssignment", "UserNotification",
    "SystemConfiguration", "SystemEvent",
    "ConstraintCategory", "ConstraintRule", "ConfigurationConstraint",
    "AcademicSession", "Department", "Faculty", "Programme",
    "Course", "Student", "CourseRegistration",
    "Building", "RoomType", "Room", "ExamRoom",
    "TimetableJob", "TimetableVersion",
    "Exam", "TimeSlot", "Staff", "ExamInvigilator", "StaffUnavailability"
]
