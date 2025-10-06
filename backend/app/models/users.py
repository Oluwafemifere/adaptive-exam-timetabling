# backend/app/models/users.py

import uuid
from typing import TYPE_CHECKING, List, Optional
from datetime import datetime
from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    ARRAY,
    func,
    Index,
    # REMOVED: Unused Enum import
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .base import Base, TimestampMixin

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from .jobs import TimetableJob
    from .constraints import ConfigurationConstraint
    from .academic import Faculty, Department, Student
    from .scheduling import Staff


# This enum can still be used for application logic but is not directly tied to the DB type
import enum


class UserRoleEnum(str, enum.Enum):
    admin = "admin"
    staff = "staff"
    student = "student"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    # ADDED: phone column to match schema
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)

    # --- FIX: Changed Enum to String to match the database schema ---
    # The 'role' column in the database is a varchar, not a custom enum type.
    # This change correctly maps the model attribute to the database column type.
    role: Mapped[str] = mapped_column(
        String(255), nullable=False, default=UserRoleEnum.student.value
    )

    # REMOVED: The 'roles' relationship to the old assignment table.

    # Use string references to avoid circular imports
    notifications: Mapped[List["UserNotification"]] = relationship(
        back_populates="user"
    )
    initiated_jobs: Mapped[List["TimetableJob"]] = relationship(
        back_populates="initiated_by_user"
    )
    # Defines the one-to-one relationship to a staff profile
    staff: Mapped[Optional["Staff"]] = relationship(
        "Staff", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    # NEW: Defines the one-to-one relationship to a student profile
    student: Mapped[Optional["Student"]] = relationship(
        "Student", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    # NEW: Relationship to user filter presets
    filter_presets: Mapped[List["UserFilterPreset"]] = relationship(
        "UserFilterPreset", back_populates="user", cascade="all, delete-orphan"
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
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="notifications")
    event: Mapped["SystemEvent"] = relationship(back_populates="notifications")


class SystemConfiguration(Base, TimestampMixin):
    __tablename__ = "system_configurations"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    solver_parameters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Use string references
    constraints: Mapped[List["ConfigurationConstraint"]] = relationship(
        back_populates="configuration"
    )
    jobs: Mapped[List["TimetableJob"]] = relationship(back_populates="configuration")


class SystemEvent(Base, TimestampMixin):
    __tablename__ = "system_events"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    priority: Mapped[str] = mapped_column(String, default="medium", nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String, nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    event_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    affected_users: Mapped[List[uuid.UUID] | None] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)), nullable=True
    )
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    resolved_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)

    notifications: Mapped[List["UserNotification"]] = relationship(
        back_populates="event"
    )
    resolver: Mapped["User"] = relationship(foreign_keys=[resolved_by])


# NEW MODEL for user_filter_presets table
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

    user: Mapped["User"] = relationship("User", back_populates="filter_presets")
