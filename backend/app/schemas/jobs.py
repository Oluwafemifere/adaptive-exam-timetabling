# app/schemas/jobs.py
from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any
from uuid import UUID
from datetime import datetime

MODEL_CONFIG = ConfigDict(from_attributes=True)


class TimetableJobBase(BaseModel):
    model_config = MODEL_CONFIG

    session_id: UUID
    configuration_id: UUID


class TimetableJobCreate(TimetableJobBase):
    model_config = MODEL_CONFIG

    initiated_by: UUID


class TimetableJobRead(TimetableJobBase):
    model_config = MODEL_CONFIG

    id: UUID
    status: str
    progress_percentage: int
    cp_sat_runtime_seconds: Optional[int] = None
    ga_runtime_seconds: Optional[int] = None
    total_runtime_seconds: Optional[int] = None
    hard_constraint_violations: int = 0
    soft_constraint_score: Optional[float] = None
    room_utilization_percentage: Optional[float] = None
    solver_phase: Optional[str] = None
    error_message: Optional[str] = None
    result_data: Optional[dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
