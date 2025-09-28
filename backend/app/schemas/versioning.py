# app/schemas/versioning.py
"""Pydantic v2 schemas for versioning domain."""

from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

# Use attribute loading for ORM compatibility
MODEL_CONFIG = ConfigDict(from_attributes=True)


class TimetableVersionRead(BaseModel):
    model_config = MODEL_CONFIG

    id: UUID
    job_id: UUID
    parent_version_id: Optional[UUID] = None
    version_type: str
    version_number: int
    is_active: bool
    is_published: bool
    archive_date: Optional[datetime] = None
    approval_level: Optional[str] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    timetable_assignment_ids: List[UUID] = Field(
        alias="timetable_assignments", default_factory=list
    )


class SessionTemplateRead(BaseModel):
    model_config = MODEL_CONFIG

    id: UUID
    name: str
    description: Optional[str] = None
    source_session_id: Optional[UUID] = None
    template_data: Optional[Dict[str, Any]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
