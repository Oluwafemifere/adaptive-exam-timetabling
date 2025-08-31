# backend\app\models\jobs.py
import uuid
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
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .base import Base, TimestampMixin

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from .users import SystemConfiguration, User
    from .academic import AcademicSession


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
    soft_constraint_score: Mapped[Numeric | None] = mapped_column(
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

    # Use string references to avoid circular imports
    session: Mapped["AcademicSession"] = relationship(back_populates="jobs")
    configuration: Mapped["SystemConfiguration"] = relationship(back_populates="jobs")
    initiated_by_user: Mapped["User"] = relationship(back_populates="initiated_jobs")
    version: Mapped["TimetableVersion"] = relationship(
        back_populates="job", uselist=False
    )


class TimetableVersion(Base, TimestampMixin):
    __tablename__ = "timetable_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("timetable_jobs.id"),
        nullable=False,
        unique=True,
    )
    version_number: Mapped[int] = mapped_column(
        Integer, unique=True, nullable=False, default=1
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approval_level: Mapped[str | None] = mapped_column(String, nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)

    job: Mapped["TimetableJob"] = relationship(back_populates="version")
    approver: Mapped["User"] = relationship(foreign_keys=[approved_by])
