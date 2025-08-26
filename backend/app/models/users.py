# app/models/users.py
import uuid
from sqlalchemy import String, Boolean, DateTime, Text, JSON, ForeignKey, ARRAY, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .base import Base, TimestampMixin
from .jobs import TimetableJob
from .constraints import ConfigurationConstraint
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID]          = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str]             = mapped_column(String, unique=True, nullable=False)
    first_name: Mapped[str]        = mapped_column(String, nullable=False)
    last_name: Mapped[str]         = mapped_column(String, nullable=False)
    phone: Mapped[str | None]      = mapped_column(String, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool]        = mapped_column(Boolean, default=True, nullable=False)
    last_login: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)

    roles: Mapped[list["UserRoleAssignment"]]    = relationship(back_populates="user")
    notifications: Mapped[list["UserNotification"]] = relationship(back_populates="user")
    initiated_jobs: Mapped[list["TimetableJob"]]   = relationship(back_populates="initiated_by_user")

class UserRole(Base):
    __tablename__ = "user_roles"

    id: Mapped[uuid.UUID]      = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str]          = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    permissions: Mapped[dict]  = mapped_column(JSON, default={})

    assignments: Mapped[list["UserRoleAssignment"]] = relationship(back_populates="role")

class UserRoleAssignment(Base, TimestampMixin):
    __tablename__ = "user_role_assignments"

    id: Mapped[uuid.UUID]      = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("user_roles.id"), nullable=False)
    faculty_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("faculties.id"), nullable=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)
    assigned_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped["User"]             = relationship(back_populates="roles")
    role: Mapped["UserRole"]         = relationship(back_populates="assignments")

class UserNotification(Base, TimestampMixin):
    __tablename__ = "user_notifications"

    id: Mapped[uuid.UUID]      = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("system_events.id"), nullable=False)
    is_read: Mapped[bool]       = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"]           = relationship(back_populates="notifications")
    event: Mapped["SystemEvent"]   = relationship(back_populates="notifications")

class SystemConfiguration(Base, TimestampMixin):
    __tablename__ = "system_configurations"

    id: Mapped[uuid.UUID]      = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str]          = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_default: Mapped[bool]    = mapped_column(Boolean, default=False, nullable=False)

    constraints: Mapped[list["ConfigurationConstraint"]] = relationship(back_populates="configuration")
    jobs: Mapped[list["TimetableJob"]]                 = relationship(back_populates="configuration")

class SystemEvent(Base, TimestampMixin):
    __tablename__ = "system_events"

    id: Mapped[uuid.UUID]      = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str]         = mapped_column(String, nullable=False)
    message: Mapped[str]       = mapped_column(Text, nullable=False)
    event_type: Mapped[str]    = mapped_column(String, nullable=False)
    priority: Mapped[str]      = mapped_column(String, default="medium", nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String, nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    event_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    affected_users: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(PG_UUID(as_uuid=True)), nullable=True)
    is_resolved: Mapped[bool]    = mapped_column(Boolean, default=False, nullable=False)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)

    notifications: Mapped[list["UserNotification"]] = relationship(back_populates="event")
    resolver: Mapped["User"] = relationship(foreign_keys=[resolved_by])
