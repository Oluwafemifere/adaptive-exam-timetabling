# backend/app/schemas/profile.py
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime


class FilterPresetBase(BaseModel):
    preset_name: str = Field(..., min_length=1, max_length=255)
    preset_type: str = Field(..., min_length=1, max_length=50)
    filters: Dict[str, Any]


class FilterPresetCreate(FilterPresetBase):
    pass


class FilterPresetRead(FilterPresetBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
