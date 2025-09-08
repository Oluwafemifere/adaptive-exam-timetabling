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
    Time,
    func,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .base import Base, TimestampMixin

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from .academic import AcademicSession, Course, Department
    from .infrastructure import ExamRoom, Room


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
    time_slot_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("time_slots.id"), nullable=True
    )
    exam_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
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
    # Use string references to avoid circular imports
    course: Mapped["Course"] = relationship("Course", back_populates="exams")
    session: Mapped["AcademicSession"] = relationship(
        "AcademicSession", back_populates="exams"
    )
    time_slot: Mapped["TimeSlot"] = relationship("TimeSlot", back_populates="exams")
    exam_rooms: Mapped[List["ExamRoom"]] = relationship(
        "ExamRoom", back_populates="exam"
    )
    invigilators: Mapped[List["ExamInvigilator"]] = relationship(
        "ExamInvigilator", back_populates="exam"
    )
    exam_departments: Mapped[List["ExamDepartment"]] = relationship(
        "ExamDepartment",
        back_populates="exam",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    departments: Mapped[List["Department"]] = relationship(
        "Department",
        secondary="exam_departments",
        back_populates="exams",
        viewonly=True,
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


class TimeSlot(Base, TimestampMixin):
    __tablename__ = "time_slots"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    start_time: Mapped[Time] = mapped_column(Time, nullable=False)
    end_time: Mapped[Time] = mapped_column(Time, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=180, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    exams: Mapped[List["Exam"]] = relationship("Exam", back_populates="time_slot")
    staff_unavailability: Mapped[List["StaffUnavailability"]] = relationship(
        "StaffUnavailability", back_populates="time_slot"
    )


class Staff(Base, TimestampMixin):
    __tablename__ = "staff"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    staff_number: Mapped[str] = mapped_column(String, unique=True, nullable=False)
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
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )


class ExamInvigilator(Base, TimestampMixin):
    __tablename__ = "exam_invigilators"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("exams.id"), nullable=False
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("staff.id"), nullable=False
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False
    )
    assigned_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    is_chief_invigilator: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    exam: Mapped["Exam"] = relationship("Exam", back_populates="invigilators")
    staff: Mapped["Staff"] = relationship("Staff", back_populates="invigilations")
    room: Mapped["Room"] = relationship(
        "Room"
    )  # Simple relationship without back_populates for now


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
    time_slot_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("time_slots.id"), nullable=True
    )
    unavailable_date: Mapped[Date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)

    staff: Mapped["Staff"] = relationship("Staff", back_populates="unavailability")
    session: Mapped["AcademicSession"] = relationship(
        "AcademicSession", back_populates="staff_unavailability"
    )
    time_slot: Mapped["TimeSlot"] = relationship(
        "TimeSlot", back_populates="staff_unavailability"
    )
