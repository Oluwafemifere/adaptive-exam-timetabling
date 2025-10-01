# backend\app\models\scheduling.py

import uuid

from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import (
    String,
    Integer,
    Date,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    func,
    Index,
    Table,
    Column,
    Time,
)

from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from datetime import date, time, datetime
from .base import Base, TimestampMixin

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from .academic import AcademicSession, Course, Department, CourseInstructor, Student
    from .infrastructure import Room, ExamAllowedRoom
    from .versioning import TimetableVersion
    from .users import User


# Association table for Exam prerequisites (self-referencing many-to-many)
exam_prerequisites_association = Table(
    "exam_prerequisites_association",
    Base.metadata,
    Column("exam_id", PG_UUID(as_uuid=True), ForeignKey("exams.id"), primary_key=True),
    Column(
        "prerequisite_id",
        PG_UUID(as_uuid=True),
        ForeignKey("exams.id"),
        primary_key=True,
    ),
)


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("academic_sessions.id"), nullable=False
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, default=180, nullable=False)
    expected_students: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    requires_special_arrangements: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_practical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_projector: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    is_common: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    morning_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # REMOVED: instructor_id is no longer on the Exam model.

    course: Mapped["Course"] = relationship("Course", back_populates="exams")
    session: Mapped["AcademicSession"] = relationship(
        "AcademicSession", back_populates="exams"
    )
    exam_departments: Mapped[List["ExamDepartment"]] = relationship(
        "ExamDepartment",
        back_populates="exam",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    departments = association_proxy("exam_departments", "department")
    allowed_rooms: Mapped[List["ExamAllowedRoom"]] = relationship(back_populates="exam")
    timetable_assignments: Mapped[List["TimetableAssignment"]] = relationship(
        back_populates="exam"
    )

    # Self-referencing many-to-many relationship for prerequisites
    prerequisites: Mapped[List["Exam"]] = relationship(
        "Exam",
        secondary=exam_prerequisites_association,
        primaryjoin=exam_prerequisites_association.c.exam_id == id,
        secondaryjoin=exam_prerequisites_association.c.prerequisite_id == id,
        back_populates="dependent_exams",
        lazy="selectin",
    )

    dependent_exams: Mapped[List["Exam"]] = relationship(
        "Exam",
        secondary=exam_prerequisites_association,
        primaryjoin=exam_prerequisites_association.c.prerequisite_id == id,
        secondaryjoin=exam_prerequisites_association.c.exam_id == id,
        back_populates="prerequisites",
        lazy="selectin",
    )


class ExamDepartment(Base, TimestampMixin):
    __tablename__ = "exam_departments"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
    )

    exam: Mapped["Exam"] = relationship("Exam", back_populates="exam_departments")
    department: Mapped["Department"] = relationship(
        "Department", back_populates="exam_departments"
    )


# Re-introduced TimeSlot model to match the database schema
class TimeSlot(Base, TimestampMixin):
    __tablename__ = "time_slots"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    period_name: Mapped[str] = mapped_column(String(50), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)


class Staff(Base, TimestampMixin):
    __tablename__ = "staff"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    staff_number: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True
    )
    position: Mapped[str | None] = mapped_column(String, nullable=True)
    staff_type: Mapped[str] = mapped_column(String, nullable=False)
    can_invigilate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_daily_sessions: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    max_consecutive_sessions: Mapped[int] = mapped_column(
        Integer, default=2, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_concurrent_exams: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )
    max_students_per_invigilator: Mapped[int] = mapped_column(
        Integer, default=50, nullable=False
    )
    generic_availability_preferences: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )

    department: Mapped["Department"] = relationship(
        "Department", back_populates="staff"
    )
    invigilations: Mapped[List["ExamInvigilator"]] = relationship(
        "ExamInvigilator", back_populates="staff"
    )
    unavailability: Mapped[List["StaffUnavailability"]] = relationship(
        "StaffUnavailability", back_populates="staff"
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, unique=True
    )
    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="staff", uselist=False
    )
    course_associations: Mapped[List["CourseInstructor"]] = relationship(
        back_populates="staff"
    )
    taught_courses: AssociationProxy[List["Course"]] = association_proxy(
        "course_associations", "course"
    )


class ExamInvigilator(Base, TimestampMixin):
    __tablename__ = "exam_invigilators"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("staff.id"), nullable=False
    )
    timetable_assignment_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("timetable_assignments.id"), nullable=False
    )
    # MODIFIED: Changed to role to match schema
    role: Mapped[str] = mapped_column(String(30), default="invigilator", nullable=False)

    staff: Mapped["Staff"] = relationship("Staff", back_populates="invigilations")
    timetable_assignment: Mapped["TimetableAssignment"] = relationship(
        "TimetableAssignment", back_populates="invigilators"
    )


class StaffUnavailability(Base):
    __tablename__ = "staff_unavailability"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("staff.id"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("academic_sessions.id"), nullable=False
    )
    time_slot_period: Mapped[str | None] = mapped_column(String, nullable=True)
    unavailable_date: Mapped[Date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)

    staff: Mapped["Staff"] = relationship("Staff", back_populates="unavailability")
    session: Mapped["AcademicSession"] = relationship(
        "AcademicSession", back_populates="staff_unavailability"
    )


class TimetableAssignment(Base):
    __tablename__ = "timetable_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("exams.id"), nullable=False
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False
    )
    exam_date: Mapped[Date] = mapped_column(Date, nullable=False)
    # MODIFIED: Replaced time_slot_period with time_slot_id to match schema
    time_slot_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("time_slots.id"), nullable=False
    )
    student_count: Mapped[int] = mapped_column(Integer, nullable=False)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("timetable_versions.id"), nullable=True
    )
    allocated_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    seating_arrangement: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    exam: Mapped["Exam"] = relationship(back_populates="timetable_assignments")
    room: Mapped["Room"] = relationship(back_populates="timetable_assignments")
    time_slot: Mapped["TimeSlot"] = relationship("TimeSlot")
    version: Mapped["TimetableVersion"] = relationship(
        "TimetableVersion", back_populates="timetable_assignments"
    )
    invigilators: Mapped[List["ExamInvigilator"]] = relationship(
        "ExamInvigilator", back_populates="timetable_assignment"
    )

    # Add indexes for performance
    __table_args__ = (
        Index("idx_timetable_assignments_version_id", "version_id"),
        Index("idx_timetable_assignments_exam_id", "exam_id"),
        Index("idx_timetable_assignments_day_time_slot", "exam_date", "time_slot_id"),
    )


# NEW MODEL from schema: assignment_change_requests
class AssignmentChangeRequest(Base):
    __tablename__ = "assignment_change_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("staff.id"), nullable=False
    )
    timetable_assignment_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("timetable_assignments.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id")
    )
    review_notes: Mapped[str | None] = mapped_column(Text)

    staff: Mapped["Staff"] = relationship("Staff")
    timetable_assignment: Mapped["TimetableAssignment"] = relationship(
        "TimetableAssignment"
    )
    reviewer: Mapped[Optional["User"]] = relationship("User")


# NEW MODEL from schema: conflict_reports
class ConflictReport(Base):
    __tablename__ = "conflict_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("students.id"), nullable=False
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("exams.id"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id")
    )
    resolver_notes: Mapped[str | None] = mapped_column(Text)

    student: Mapped["Student"] = relationship("Student")
    exam: Mapped["Exam"] = relationship("Exam")
    reviewer: Mapped[Optional["User"]] = relationship("User")
