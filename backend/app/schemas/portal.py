# app/schemas/portal.py
from uuid import UUID
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class ConflictReportCreate(BaseModel):
    exam_id: UUID
    description: str = Field(..., min_length=10)


class RequestManage(BaseModel):
    new_status: str
    notes: str = Field(..., min_length=5)


class ChangeRequestCreate(BaseModel):
    assignment_id: UUID
    reason: str
    description: str = Field(..., min_length=10)


class StaffAvailabilityUpdate(BaseModel):
    # FIX: Added session_id, which is required by the backend service.
    session_id: UUID
    availability_data: Dict[str, Any]
