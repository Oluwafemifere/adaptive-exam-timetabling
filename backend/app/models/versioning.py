# backend/app/models/versioning.py

import uuid
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime

from sqlalchemy import String, DateTime, Boolean, ForeignKey, Text, Integer, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .base import Base, TimestampMixin

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from .jobs import TimetableJob
    from .academic import AcademicSession
    from .users import User
    from .scheduling import TimetableAssignment


class TimetableVersion(Base, TimestampMixin):
    """
    Enhanced TimetableVersion model with support for version hierarchies,
    multiple versions per job, and comprehensive versioning capabilities.
    """

    __tablename__ = "timetable_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("timetable_jobs.id"),
        nullable=False,
        # Removed unique=True to allow multiple versions per job
    )

    # NEW FIELDS for enhanced versioning
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("timetable_versions.id"), nullable=True
    )
    version_type: Mapped[str] = mapped_column(
        String(20), default="primary", nullable=False
    )
    archive_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Existing fields with enhanced functionality
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approval_level: Mapped[str | None] = mapped_column(String, nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Enhanced relationships
    job: Mapped["TimetableJob"] = relationship(
        "TimetableJob", back_populates="versions"
    )

    parent_version: Mapped["TimetableVersion"] = relationship(
        "TimetableVersion", remote_side=[id], back_populates="child_versions"
    )
    child_versions: Mapped[List["TimetableVersion"]] = relationship(
        "TimetableVersion", back_populates="parent_version"
    )

    # Version-specific relationships
    version_metadata: Mapped[List["VersionMetadata"]] = relationship(
        "VersionMetadata", back_populates="version", cascade="all, delete-orphan"
    )
    dependencies: Mapped[List["VersionDependency"]] = relationship(
        "VersionDependency",
        foreign_keys="VersionDependency.version_id",
        back_populates="version",
        cascade="all, delete-orphan",
    )
    dependent_versions: Mapped[List["VersionDependency"]] = relationship(
        "VersionDependency",
        foreign_keys="VersionDependency.depends_on_version_id",
        back_populates="depends_on_version",
    )

    # Link to assignments
    timetable_assignments: Mapped[List["TimetableAssignment"]] = relationship(
        "TimetableAssignment", back_populates="version"
    )

    approver: Mapped["User"] = relationship("User", foreign_keys=[approved_by])

    # Add indexes for performance
    __table_args__ = (
        Index("idx_timetable_versions_job_id", "job_id"),
        Index("idx_timetable_versions_parent_version_id", "parent_version_id"),
        Index("idx_timetable_versions_active", "is_active"),
        Index("idx_timetable_versions_published", "is_published"),
    )


class VersionMetadata(Base, TimestampMixin):
    """
    Stores additional metadata for timetable versions including titles,
    descriptions, and tags for better organization and searchability.
    """

    __tablename__ = "version_metadata"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("timetable_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationship
    version: Mapped["TimetableVersion"] = relationship(
        "TimetableVersion", back_populates="version_metadata"
    )

    # Indexes
    __table_args__ = (Index("idx_version_metadata_version_id", "version_id"),)


class VersionDependency(Base, TimestampMixin):
    """
    Tracks dependencies between timetable versions, enabling version
    hierarchies and dependency management.
    """

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
    dependency_type: Mapped[str] = mapped_column(
        String(20), default="parent", nullable=False
    )

    # Relationships
    version: Mapped["TimetableVersion"] = relationship(
        "TimetableVersion", foreign_keys=[version_id], back_populates="dependencies"
    )
    depends_on_version: Mapped["TimetableVersion"] = relationship(
        "TimetableVersion",
        foreign_keys=[depends_on_version_id],
        back_populates="dependent_versions",
    )

    # Indexes
    __table_args__ = (
        Index("idx_version_dependencies_version_id", "version_id"),
        Index(
            "idx_version_dependencies_depends_on_version_id", "depends_on_version_id"
        ),
    )


class SessionTemplate(Base, TimestampMixin):
    """
    Stores templates for academic sessions to enable reuse of configurations
    across semesters and efficient semester setup.
    """

    __tablename__ = "session_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_session_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("academic_sessions.id"), nullable=True
    )
    template_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # FIXED: Specify foreign_keys explicitly to resolve ambiguity
    source_session: Mapped["AcademicSession"] = relationship(
        "AcademicSession",
        foreign_keys=[source_session_id],
        back_populates="session_templates",
    )
    sessions: Mapped[List["AcademicSession"]] = relationship(
        "AcademicSession",
        foreign_keys="AcademicSession.template_id",
        back_populates="template",
    )

    # Indexes
    __table_args__ = (
        Index("idx_session_templates_source_session_id", "source_session_id"),
        Index("idx_session_templates_active", "is_active"),
    )
