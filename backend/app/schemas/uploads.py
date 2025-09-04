# app/schemas/uploads.py
from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

MODEL_CONFIG = ConfigDict(from_attributes=True)


class UploadedFileBase(BaseModel):
    model_config = MODEL_CONFIG

    file_name: str
    file_path: str
    file_size: int
    file_type: str
    mime_type: Optional[str] = None
    checksum: Optional[str] = None
    row_count: Optional[int] = None
    validation_status: str = Field(default="pending")
    validation_errors: Optional[Dict[str, Any]] = None


class UploadedFileCreate(UploadedFileBase):
    model_config = MODEL_CONFIG

    upload_session_id: UUID


class UploadedFileRead(UploadedFileBase):
    model_config = MODEL_CONFIG

    id: UUID
    uploaded_at: datetime


class FileUploadSessionBase(BaseModel):
    model_config = MODEL_CONFIG

    upload_type: str
    session_id: Optional[UUID] = None
    status: str = Field(default="processing")
    total_records: int = Field(default=0)
    processed_records: int = Field(default=0)
    validation_errors: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None


class FileUploadSessionCreate(FileUploadSessionBase):
    model_config = MODEL_CONFIG

    uploaded_by: UUID


class FileUploadSessionRead(FileUploadSessionBase):
    model_config = MODEL_CONFIG

    id: UUID
    created_at: datetime
    uploaded_files: List[UploadedFileRead] = Field(default_factory=list)
