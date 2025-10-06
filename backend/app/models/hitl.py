# C:\Users\fresh\OneDrive\Dokumen\thesis\proj\CODE\adaptive-exam-timetabling\backend\app\models\hitl.py

import uuid
from datetime import datetime, date
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import (
    String,
    Text,
    ForeignKey,
    DateTime,
    Boolean,
    Integer,
    Date,
    func,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

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
        PG_UUID(as_uuid=True),
        ForeignKey(
            "exam_system.timetable_versions.id",
            use_alter=True,
            name="timetable_scenarios_parent_version_id_fkey",
        ),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    versions: Mapped[List["TimetableVersion"]] = relationship(
        "TimetableVersion",
        foreign_keys="TimetableVersion.scenario_id",
        back_populates="scenario",
    )
    # REMOVED: constraint_configurations relationship as the table doesn't exist.
    locks: Mapped[List["TimetableLock"]] = relationship(
        "TimetableLock", back_populates="scenario"
    )
    jobs: Mapped[List["TimetableJob"]] = relationship(
        "TimetableJob", back_populates="scenario"
    )


# REMOVED: ConstraintConfiguration model is not in the DB schema.


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
    # MODIFIED: time_slot_id changed to timeslot_template_period_id to match schema
    timeslot_template_period_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("timeslot_template_periods.id"),
        nullable=True,
    )
    exam_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    room_ids: Mapped[Optional[List[uuid.UUID]]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)), nullable=True
    )
    locked_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    locked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    scenario: Mapped["TimetableScenario"] = relationship(
        "TimetableScenario", back_populates="locks"
    )
    exam: Mapped["Exam"] = relationship("Exam")
    # MODIFIED: Relationship updated to TimeSlotTemplatePeriod
    timeslot_period: Mapped[Optional["TimeSlotTemplatePeriod"]] = relationship(
        "TimeSlotTemplatePeriod"
    )
    locker: Mapped["User"] = relationship("User")

    __table_args__ = (
        Index("idx_timetable_locks_scenario_active", "scenario_id", "is_active"),
    )
