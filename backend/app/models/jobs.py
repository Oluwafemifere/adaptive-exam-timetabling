# backend\app\models\jobs.py

import uuid
from datetime import date

from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import (
    String,
    ForeignKey,
    Integer,
    Numeric,
    DateTime,
    Text,
    Boolean,
    Index,
    Date,
)

from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

# REMOVED: Unused import
# from .hitl import ConstraintConfiguration, TimetableScenario
from .hitl import TimetableScenario


from .base import Base, TimestampMixin

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from .users import SystemConfiguration, User
    from .academic import AcademicSession
    from .versioning import TimetableVersion


class TimetableJob(Base, TimestampMixin):
    __tablename__ = "timetable_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("academic_sessions.id"), nullable=False
    )

    configuration_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("system_configurations.id"), nullable=False
    )

    initiated_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    status: Mapped[str] = mapped_column(String, default="queued", nullable=False)
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cp_sat_runtime_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ga_runtime_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_runtime_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hard_constraint_violations: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    scenario_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("timetable_scenarios.id"), nullable=True
    )
    # ADDED: constraint_config_id exists in the schema
    constraint_config_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
    checkpoint_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    soft_constraints_violations: Mapped[Numeric | None] = mapped_column(
        Numeric, nullable=True
    )
    room_utilization_percentage: Mapped[Numeric | None] = mapped_column(
        Numeric, nullable=True
    )
    solver_phase: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)

    # Fields from schema not present in the original model
    can_pause: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_resume: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_cancel: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    generation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processed_exams: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_exams: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fitness_score: Mapped[Numeric | None] = mapped_column(Numeric, nullable=True)

    # Use string references to avoid circular imports
    session: Mapped["AcademicSession"] = relationship(back_populates="jobs")
    configuration: Mapped["SystemConfiguration"] = relationship(back_populates="jobs")
    initiated_by_user: Mapped["User"] = relationship(back_populates="initiated_jobs")

    # MODIFIED: Changed to support multiple versions per job
    versions: Mapped[List["TimetableVersion"]] = relationship(
        "TimetableVersion", back_populates="job"
    )
    scenario: Mapped[Optional["TimetableScenario"]] = relationship(
        "TimetableScenario", back_populates="jobs"
    )


# NEW MODEL for timetable_job_exam_days table
class TimetableJobExamDay(Base):
    __tablename__ = "timetable_job_exam_days"

    timetable_job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("timetable_jobs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    exam_date: Mapped[date] = mapped_column(Date, primary_key=True)
