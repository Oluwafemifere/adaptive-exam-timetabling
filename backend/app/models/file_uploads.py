# app/models/file_uploads.py
import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey, DateTime, BigInteger, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .users import User
    from .academic import AcademicSession


class DataSeedingSession(Base, TimestampMixin):
    __tablename__ = "data_seeding_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    academic_session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("academic_sessions.id"),
        unique=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    academic_session: Mapped["AcademicSession"] = relationship(
        back_populates="data_seeding_sessions"
    )
    creator: Mapped["User"] = relationship()
    file_uploads: Mapped[List["FileUpload"]] = relationship(
        back_populates="data_seeding_session"
    )


class FileUpload(Base, TimestampMixin):
    __tablename__ = "file_uploads"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    data_seeding_session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("data_seeding_sessions.id"), nullable=False
    )
    upload_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    total_records: Mapped[int | None] = mapped_column(Integer)
    processed_records: Mapped[int | None] = mapped_column(Integer)
    validation_errors: Mapped[dict | None] = mapped_column(JSONB)

    data_seeding_session: Mapped["DataSeedingSession"] = relationship(
        back_populates="file_uploads"
    )


class FileUploadSession(Base, TimestampMixin):
    __tablename__ = "file_upload_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    upload_type: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("academic_sessions.id")
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    total_records: Mapped[int | None] = mapped_column(Integer, default=0)
    processed_records: Mapped[int | None] = mapped_column(Integer, default=0)
    validation_errors: Mapped[dict | None] = mapped_column(JSONB, default={})
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    uploader: Mapped["User"] = relationship()
    session: Mapped[Optional["AcademicSession"]] = relationship(
        back_populates="file_upload_sessions"
    )
    uploaded_files: Mapped[List["UploadedFile"]] = relationship(
        back_populates="upload_session"
    )


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    upload_session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("file_upload_sessions.id"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_type: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String)
    checksum: Mapped[str | None] = mapped_column(String)
    row_count: Mapped[int | None] = mapped_column(Integer)
    validation_status: Mapped[str] = mapped_column(String, nullable=False)
    validation_errors: Mapped[dict | None] = mapped_column(JSONB)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    upload_session: Mapped["FileUploadSession"] = relationship(
        back_populates="uploaded_files"
    )
