# app/models/versioning.py

import uuid
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Text, Integer, Index, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .jobs import TimetableJob
    from .academic import AcademicSession
    from .users import User
    from .scheduling import TimetableAssignment
    from .hitl import TimetableScenario


class TimetableVersion(Base, TimestampMixin):
    __tablename__ = "timetable_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("timetable_jobs.id"), nullable=False
    )
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("timetable_versions.id")
    )
    version_type: Mapped[str] = mapped_column(String(20), nullable=False)
    archive_date: Mapped[datetime | None] = mapped_column(DateTime)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    scenario_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("timetable_scenarios.id", ondelete="CASCADE")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    approval_level: Mapped[str | None] = mapped_column(String)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)

    job: Mapped["TimetableJob"] = relationship(back_populates="versions")
    parent_version: Mapped[Optional["TimetableVersion"]] = relationship(
        "TimetableVersion", remote_side=[id], back_populates="child_versions"
    )
    child_versions: Mapped[List["TimetableVersion"]] = relationship(
        back_populates="parent_version"
    )
    version_metadata: Mapped[List["VersionMetadata"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )
    dependencies: Mapped[List["VersionDependency"]] = relationship(
        foreign_keys="VersionDependency.version_id",
        back_populates="version",
        cascade="all, delete-orphan",
    )
    dependents: Mapped[List["VersionDependency"]] = relationship(
        foreign_keys="VersionDependency.depends_on_version_id",
        back_populates="depends_on_version",
    )
    scenario: Mapped[Optional["TimetableScenario"]] = relationship(
        foreign_keys=[scenario_id], back_populates="versions"
    )
    timetable_assignments: Mapped[List["TimetableAssignment"]] = relationship(
        back_populates="version"
    )
    approver: Mapped[Optional["User"]] = relationship()
    conflicts: Mapped[List["TimetableConflict"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )

    # ADDED: This new relationship completes the link from TimetableScenario's parent_version
    scenarios_where_parent: Mapped[List["TimetableScenario"]] = relationship(
        foreign_keys="TimetableScenario.parent_version_id",
        back_populates="parent_version",
    )

    __table_args__ = (
        Index("idx_timetable_versions_job_id", "job_id"),
        Index("idx_timetable_versions_parent_version_id", "parent_version_id"),
        Index("idx_timetable_versions_active", "is_active"),
        Index("idx_timetable_versions_published", "is_published"),
    )


class VersionMetadata(Base, TimestampMixin):
    __tablename__ = "version_metadata"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("timetable_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[dict | None] = mapped_column(JSONB)

    version: Mapped["TimetableVersion"] = relationship(
        back_populates="version_metadata"
    )
    __table_args__ = (Index("idx_version_metadata_version_id", "version_id"),)


class VersionDependency(Base, TimestampMixin):
    __tablename__ = "version_dependencies"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("timetable_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    depends_on_version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("timetable_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    dependency_type: Mapped[str] = mapped_column(String(20), nullable=False)

    version: Mapped["TimetableVersion"] = relationship(
        foreign_keys=[version_id], back_populates="dependencies"
    )
    depends_on_version: Mapped["TimetableVersion"] = relationship(
        foreign_keys=[depends_on_version_id], back_populates="dependents"
    )

    __table_args__ = (
        Index("idx_version_dependencies_version_id", "version_id"),
        Index(
            "idx_version_dependencies_depends_on_version_id", "depends_on_version_id"
        ),
    )


class SessionTemplate(Base, TimestampMixin):
    __tablename__ = "session_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Foreign Key for Relationship 2
    source_session_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("academic_sessions.id")
    )

    template_data: Mapped[dict | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationship 2: This template is based on a source session
    source_session: Mapped[Optional["AcademicSession"]] = relationship(
        foreign_keys=[source_session_id],
        back_populates="templates_from_this_session",
    )

    # Relationship 1: This template is used by multiple sessions
    template_for_sessions: Mapped[List["AcademicSession"]] = relationship(
        foreign_keys="AcademicSession.template_id",
        back_populates="template",
    )

    __table_args__ = (
        Index("idx_session_templates_source_session_id", "source_session_id"),
        Index("idx_session_templates_active", "is_active"),
    )


class TimetableConflict(Base):
    __tablename__ = "timetable_conflicts"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("timetable_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    version: Mapped["TimetableVersion"] = relationship(back_populates="conflicts")
    __table_args__ = (Index("idx_timetable_conflicts_version_id", "version_id"),)
