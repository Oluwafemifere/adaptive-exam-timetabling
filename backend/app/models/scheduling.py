# app/models/scheduling.py

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
    Table,
    Column,
    Time,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from datetime import date, time, datetime

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .academic import AcademicSession, Course, Department, Student, CourseInstructor
    from .infrastructure import Room
    from .versioning import TimetableVersion
    from .users import User

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
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_students: Mapped[int] = mapped_column(Integer, nullable=False)
    requires_special_arrangements: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    is_practical: Mapped[bool] = mapped_column(Boolean, nullable=False)
    requires_projector: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_common: Mapped[bool] = mapped_column(Boolean, nullable=False)
    morning_only: Mapped[bool] = mapped_column(Boolean, nullable=False)

    course: Mapped["Course"] = relationship(back_populates="exams")
    session: Mapped["AcademicSession"] = relationship(back_populates="exams")
    exam_departments: Mapped[List["ExamDepartment"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan"
    )
    departments: AssociationProxy[List["Department"]] = association_proxy(
        "exam_departments", "department"
    )
    timetable_assignments: Mapped[List["TimetableAssignment"]] = relationship(
        back_populates="exam"
    )

    prerequisites: Mapped[List["Exam"]] = relationship(
        "Exam",
        secondary=exam_prerequisites_association,
        primaryjoin=id == exam_prerequisites_association.c.exam_id,
        secondaryjoin=id == exam_prerequisites_association.c.prerequisite_id,
        back_populates="dependent_exams",
    )
    dependent_exams: Mapped[List["Exam"]] = relationship(
        "Exam",
        secondary=exam_prerequisites_association,
        primaryjoin=id == exam_prerequisites_association.c.prerequisite_id,
        secondaryjoin=id == exam_prerequisites_association.c.exam_id,
        back_populates="prerequisites",
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

    exam: Mapped["Exam"] = relationship(back_populates="exam_departments")
    department: Mapped["Department"] = relationship()


class Staff(Base, TimestampMixin):
    __tablename__ = "staff"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    staff_number: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("departments.id")
    )
    position: Mapped[str | None] = mapped_column(String)
    staff_type: Mapped[str] = mapped_column(String, nullable=False)
    can_invigilate: Mapped[bool] = mapped_column(Boolean, nullable=False)
    max_daily_sessions: Mapped[int] = mapped_column(Integer, nullable=False)
    max_consecutive_sessions: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    max_concurrent_exams: Mapped[int] = mapped_column(Integer, nullable=False)
    # FIX: Corrected column name from max_students_per_invigilator to match schema
    max_students_per_invigilator: Mapped[int] = mapped_column(Integer, nullable=False)
    # FIX: Added missing column from schema
    generic_availability_preferences: Mapped[dict | None] = mapped_column(JSONB)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), unique=True
    )

    department: Mapped[Optional["Department"]] = relationship(back_populates="staff")
    user: Mapped[Optional["User"]] = relationship(back_populates="staff_profile")
    exam_invigilations: Mapped[List["ExamInvigilator"]] = relationship(
        back_populates="staff"
    )
    unavailabilities: Mapped[List["StaffUnavailability"]] = relationship(
        back_populates="staff"
    )
    course_associations: Mapped[List["CourseInstructor"]] = relationship(
        back_populates="staff"
    )
    courses: AssociationProxy[List["Course"]] = association_proxy(
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
    role: Mapped[str] = mapped_column(String(30), nullable=False)

    staff: Mapped["Staff"] = relationship(back_populates="exam_invigilations")
    timetable_assignment: Mapped["TimetableAssignment"] = relationship(
        back_populates="invigilators"
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
    time_slot_period: Mapped[str | None] = mapped_column(String)
    unavailable_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(String)

    staff: Mapped["Staff"] = relationship(back_populates="unavailabilities")
    session: Mapped["AcademicSession"] = relationship(
        back_populates="staff_unavailability"
    )

    __table_args__ = (
        UniqueConstraint(
            "staff_id",
            "unavailable_date",
            "time_slot_period",
            name="staff_unavailability_unique",
        ),
        UniqueConstraint(
            "staff_id",
            "session_id",
            "unavailable_date",
            "time_slot_period",
            name="staff_unavailability_unique_idx",
        ),
    )


class TimeSlotTemplate(Base):
    __tablename__ = "timeslot_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    periods: Mapped[List["TimeSlotTemplatePeriod"]] = relationship(
        back_populates="template", cascade="all, delete-orphan"
    )
    academic_sessions: Mapped[List["AcademicSession"]] = relationship(
        back_populates="timeslot_template"
    )


class TimeSlotTemplatePeriod(Base):
    __tablename__ = "timeslot_template_periods"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    timeslot_template_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("timeslot_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    period_name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    template: Mapped["TimeSlotTemplate"] = relationship(back_populates="periods")
    timetable_assignments: Mapped[List["TimetableAssignment"]] = relationship(
        back_populates="timeslot_period"
    )

    __table_args__ = (
        UniqueConstraint(
            "timeslot_template_id", "period_name", name="uq_template_period_name"
        ),
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
    exam_date: Mapped[date] = mapped_column(Date, nullable=False)
    timeslot_template_period_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("timeslot_template_periods.id"),
        nullable=False,
    )
    student_count: Mapped[int] = mapped_column(Integer, nullable=False)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("timetable_versions.id")
    )
    allocated_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False)
    seating_arrangement: Mapped[dict | None] = mapped_column(JSONB)

    exam: Mapped["Exam"] = relationship(back_populates="timetable_assignments")
    room: Mapped["Room"] = relationship(back_populates="timetable_assignments")
    timeslot_period: Mapped["TimeSlotTemplatePeriod"] = relationship(
        back_populates="timetable_assignments"
    )
    version: Mapped[Optional["TimetableVersion"]] = relationship(
        back_populates="timetable_assignments"
    )
    invigilators: Mapped[List["ExamInvigilator"]] = relationship(
        back_populates="timetable_assignment"
    )

    __table_args__ = (
        Index("idx_timetable_assignments_version_id", "version_id"),
        Index("idx_timetable_assignments_exam_id", "exam_id"),
    )


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
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id")
    )
    review_notes: Mapped[str | None] = mapped_column(Text)

    staff: Mapped["Staff"] = relationship()
    timetable_assignment: Mapped["TimetableAssignment"] = relationship()
    reviewer: Mapped[Optional["User"]] = relationship()


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
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id")
    )
    resolver_notes: Mapped[str | None] = mapped_column(Text)

    student: Mapped["Student"] = relationship(back_populates="conflict_reports")
    exam: Mapped["Exam"] = relationship()
    reviewer: Mapped[Optional["User"]] = relationship()
