# app/schemas/jobs.py
from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Optional, Any, List
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
    session_id: UUID
    configuration_id: UUID
    initiated_by: UUID
    status: str
    progress_percentage: int
    solver_phase: Optional[str] = None
    error_message: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    scenario_id: Optional[UUID] = None
    constraint_config_id: Optional[UUID] = None
    cp_sat_runtime_seconds: Optional[int] = None
    total_runtime_seconds: Optional[int] = None
    hard_constraint_violations: int = 0
    soft_constraints_violations: Optional[float] = None
    room_utilization_percentage: Optional[float] = None
    version_ids: List[UUID] = Field(default_factory=list)


class TimetableJobSummaryRead(BaseModel):
    """Lean schema for listing successful jobs for a session."""

    model_config = MODEL_CONFIG

    id: UUID
    created_at: datetime
    status: str
    version_id: Optional[UUID] = None
    is_published: Optional[bool] = False
