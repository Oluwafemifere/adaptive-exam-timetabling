# app/schemas/uploads.py
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class UploadedFileBase(BaseModel):
    file_name: str
    file_path: str
    file_size: int
    file_type: str
    mime_type: Optional[str]
    checksum: Optional[str]
    row_count: Optional[int]
    validation_status: str = Field(default="pending")
    validation_errors: Optional[dict]

class UploadedFileCreate(UploadedFileBase):
    upload_session_id: UUID

class UploadedFileRead(UploadedFileBase):
    id: UUID
    uploaded_at: datetime

    class Config:
        orm_mode = True

class FileUploadSessionBase(BaseModel):
    upload_type: str
    session_id: Optional[UUID]
    status: str = Field(default="processing")
    total_records: int = Field(default=0)
    processed_records: int = Field(default=0)
    validation_errors: Optional[dict]
    completed_at: Optional[datetime]

class FileUploadSessionCreate(FileUploadSessionBase):
    uploaded_by: UUID

class FileUploadSessionRead(FileUploadSessionBase):
    id: UUID
    created_at: datetime
    uploaded_files: List[UploadedFileRead] = []

    class Config:
        orm_mode = True
