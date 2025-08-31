# C:\Users\fresh\OneDrive\Dokumen\thesis\proj\CODE\adaptive-exam-timetabling\backend\app\models\file_uploads.py
import uuid
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import (
    String,
    Integer,
    ForeignKey,
    DateTime,
    Text,
    BigInteger,
    func,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .base import Base, TimestampMixin

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from .users import User
    from .academic import AcademicSession


class FileUploadSession(Base, TimestampMixin):
    __tablename__ = "file_upload_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    upload_type: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("academic_sessions.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String, default="processing", nullable=False)
    total_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    validation_errors: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)

    # Use string references to avoid circular imports
    uploader: Mapped["User"] = relationship("User")
    session: Mapped["AcademicSession"] = relationship(
        "AcademicSession", back_populates="file_uploads"
    )
    uploaded_files: Mapped[List["UploadedFile"]] = relationship(
        "UploadedFile", back_populates="upload_session"
    )


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    upload_session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("file_upload_sessions.id"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_type: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String, nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    validation_status: Mapped[str] = mapped_column(
        String, default="pending", nullable=False
    )
    validation_errors: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    uploaded_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    upload_session: Mapped["FileUploadSession"] = relationship(
        "FileUploadSession", back_populates="uploaded_files"
    )
