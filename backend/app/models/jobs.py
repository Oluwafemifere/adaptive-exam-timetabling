# app/models/jobs.py

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional, List
from sqlalchemy import (
    String,
    ForeignKey,
    Integer,
    Numeric,
    DateTime,
    Text,
    Boolean,
    Date,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .users import User
    from .academic import AcademicSession
    from .versioning import TimetableVersion
    from .hitl import TimetableScenario
    from .constraints import ConstraintConfiguration


class TimetableJob(Base, TimestampMixin):
    __tablename__ = "timetable_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("academic_sessions.id"), nullable=False
    )
    configuration_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False
    )  # Note: No FK constraint in schema
    initiated_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    progress_percentage: Mapped[int] = mapped_column(Integer, nullable=False)
    cp_sat_runtime_seconds: Mapped[int | None] = mapped_column(Integer)
    ga_runtime_seconds: Mapped[int | None] = mapped_column(Integer)
    total_runtime_seconds: Mapped[int | None] = mapped_column(Integer)
    hard_constraint_violations: Mapped[int] = mapped_column(Integer, nullable=False)
    scenario_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("timetable_scenarios.id")
    )
    constraint_config_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True)
    )
    checkpoint_data: Mapped[dict | None] = mapped_column(JSONB)
    soft_constraints_violations: Mapped[float | None] = mapped_column(Numeric)
    room_utilization_percentage: Mapped[float | None] = mapped_column(Numeric)
    solver_phase: Mapped[str | None] = mapped_column(String)
    error_message: Mapped[str | None] = mapped_column(Text)
    result_data: Mapped[dict | None] = mapped_column(JSONB)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    can_pause: Mapped[bool] = mapped_column(Boolean, nullable=False)
    can_resume: Mapped[bool] = mapped_column(Boolean, nullable=False)
    can_cancel: Mapped[bool] = mapped_column(Boolean, nullable=False)
    generation: Mapped[int | None] = mapped_column(Integer)
    processed_exams: Mapped[int | None] = mapped_column(Integer)
    total_exams: Mapped[int | None] = mapped_column(Integer)
    fitness_score: Mapped[float | None] = mapped_column(Numeric)

    session: Mapped["AcademicSession"] = relationship(back_populates="timetable_jobs")
    initiator: Mapped["User"] = relationship(back_populates="initiated_jobs")
    versions: Mapped[List["TimetableVersion"]] = relationship(back_populates="job")
    scenario: Mapped[Optional["TimetableScenario"]] = relationship(
        back_populates="jobs"
    )
    exam_days: Mapped[List["TimetableJobExamDay"]] = relationship(
        back_populates="timetable_job", cascade="all, delete-orphan"
    )


class TimetableJobExamDay(Base):
    __tablename__ = "timetable_job_exam_days"

    timetable_job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("timetable_jobs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    exam_date: Mapped[date] = mapped_column(Date, primary_key=True)

    timetable_job: Mapped["TimetableJob"] = relationship(back_populates="exam_days")
