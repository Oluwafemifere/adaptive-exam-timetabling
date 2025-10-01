# app/models/hitl.py

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
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .users import User
    from .versioning import TimetableVersion
    from .scheduling import Exam, TimeSlot
    from .jobs import TimetableJob


class TimetableScenario(Base, TimestampMixin):
    __tablename__ = "timetable_scenarios"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    parent_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("timetable_versions.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    versions: Mapped[List["TimetableVersion"]] = relationship(
        "TimetableVersion", back_populates="scenario"
    )
    constraint_configurations: Mapped[List["ConstraintConfiguration"]] = relationship(
        "ConstraintConfiguration", back_populates="scenario"
    )
    locks: Mapped[List["TimetableLock"]] = relationship(
        "TimetableLock", back_populates="scenario"
    )
    jobs: Mapped[List["TimetableJob"]] = relationship(
        "TimetableJob", back_populates="scenario"
    )


class ConstraintConfiguration(Base, TimestampMixin):
    __tablename__ = "constraint_configurations"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("timetable_scenarios.id"), nullable=False
    )
    definitions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    scenario: Mapped["TimetableScenario"] = relationship(
        "TimetableScenario", back_populates="constraint_configurations"
    )
    jobs: Mapped[List["TimetableJob"]] = relationship(
        "TimetableJob", back_populates="constraint_config"
    )


class TimetableLock(Base, TimestampMixin):
    __tablename__ = "timetable_locks"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("timetable_scenarios.id"), nullable=False
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("exams.id"), nullable=False
    )
    time_slot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("time_slots.id"), nullable=True
    )
    exam_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    room_ids: Mapped[Optional[List[uuid.UUID]]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)), nullable=True
    )
    locked_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    scenario: Mapped["TimetableScenario"] = relationship(
        "TimetableScenario", back_populates="locks"
    )
    exam: Mapped["Exam"] = relationship("Exam")
    time_slot: Mapped[Optional["TimeSlot"]] = relationship("TimeSlot")
    locker: Mapped["User"] = relationship("User")
