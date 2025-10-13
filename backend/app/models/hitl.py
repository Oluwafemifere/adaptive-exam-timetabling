# app/models/hitl.py

import uuid
from datetime import datetime, date
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, DateTime, Boolean, Date, func, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

if TYPE_CHECKING:
    from .users import User
    from .versioning import TimetableVersion
    from .scheduling import Exam, TimeSlotTemplatePeriod
    from .jobs import TimetableJob


class TimetableScenario(Base):
    __tablename__ = "timetable_scenarios"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("timetable_versions.id")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    creator: Mapped["User"] = relationship()

    versions: Mapped[List["TimetableVersion"]] = relationship(
        foreign_keys="TimetableVersion.scenario_id", back_populates="scenario"
    )

    # FIXED: The relationship now correctly back-populates the new one in TimetableVersion
    parent_version: Mapped[Optional["TimetableVersion"]] = relationship(
        foreign_keys=[parent_version_id], back_populates="scenarios_where_parent"
    )

    locks: Mapped[List["TimetableLock"]] = relationship(back_populates="scenario")
    jobs: Mapped[List["TimetableJob"]] = relationship(back_populates="scenario")


class TimetableLock(Base):
    __tablename__ = "timetable_locks"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("timetable_scenarios.id"), nullable=False
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("exams.id"), nullable=False
    )
    timeslot_template_period_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("timeslot_template_periods.id")
    )
    exam_date: Mapped[date | None] = mapped_column(Date)
    room_ids: Mapped[List[uuid.UUID] | None] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True))
    )
    locked_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    locked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reason: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)

    scenario: Mapped["TimetableScenario"] = relationship(back_populates="locks")
    exam: Mapped["Exam"] = relationship()
    timeslot_period: Mapped[Optional["TimeSlotTemplatePeriod"]] = relationship()
    locker: Mapped["User"] = relationship()

    __table_args__ = (
        Index("idx_timetable_locks_scenario_active", "scenario_id", "is_active"),
    )
