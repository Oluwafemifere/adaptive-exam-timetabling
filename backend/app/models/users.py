# app/models/users.py

import uuid
from typing import TYPE_CHECKING, List, Optional
from datetime import datetime
from sqlalchemy import ARRAY, String, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .jobs import TimetableJob
    from .academic import Student
    from .scheduling import Staff
    from .constraints import ConstraintConfiguration
    from .hitl import TimetableScenario


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str | None] = mapped_column(String)
    phone_number: Mapped[str | None] = mapped_column(String(255))
    password_hash: Mapped[str | None] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime)
    role: Mapped[str | None] = mapped_column(String(255))

    notifications: Mapped[List["UserNotification"]] = relationship(
        back_populates="user"
    )
    initiated_jobs: Mapped[List["TimetableJob"]] = relationship(
        back_populates="initiator"
    )
    staff_profile: Mapped[Optional["Staff"]] = relationship(back_populates="user")
    student_profile: Mapped[Optional["Student"]] = relationship(back_populates="user")
    filter_presets: Mapped[List["UserFilterPreset"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    created_scenarios: Mapped[List["TimetableScenario"]] = relationship(
        back_populates="creator"
    )


class UserNotification(Base, TimestampMixin):
    __tablename__ = "user_notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("system_events.id"), nullable=False
    )
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)

    user: Mapped["User"] = relationship(back_populates="notifications")
    event: Mapped["SystemEvent"] = relationship(back_populates="notifications")


class SystemConfiguration(Base):
    __tablename__ = "system_configurations"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    solver_parameters: Mapped[dict | None] = mapped_column(JSONB)
    constraint_config_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("constraint_configurations.id"),
        nullable=False,
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    constraint_configuration: Mapped["ConstraintConfiguration"] = relationship(
        back_populates="system_configurations"
    )
    creator: Mapped[Optional["User"]] = relationship()


class SystemEvent(Base, TimestampMixin):
    __tablename__ = "system_events"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    priority: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    event_metadata: Mapped[dict | None] = mapped_column(JSONB)
    affected_users: Mapped[List[uuid.UUID] | None] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True))
    )
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)

    notifications: Mapped[List["UserNotification"]] = relationship(
        back_populates="event"
    )
    resolver: Mapped[Optional["User"]] = relationship()


class UserFilterPreset(Base):
    __tablename__ = "user_filter_presets"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    preset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    preset_type: Mapped[str] = mapped_column(String(50), nullable=False)
    filters: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="filter_presets")
