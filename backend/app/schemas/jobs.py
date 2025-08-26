# app/schemas/jobs.py
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

class TimetableJobBase(BaseModel):
    session_id: UUID
    configuration_id: UUID

class TimetableJobCreate(TimetableJobBase):
    initiated_by: UUID

class TimetableJobRead(TimetableJobBase):
    id: UUID
    status: str
    progress_percentage: int
    cp_sat_runtime_seconds: Optional[int]
    ga_runtime_seconds: Optional[int]
    total_runtime_seconds: Optional[int]
    hard_constraint_violations: int
    soft_constraint_score: Optional[float]
    room_utilization_percentage: Optional[float]
    solver_phase: Optional[str]
    error_message: Optional[str]
    result_data: Optional[dict]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        orm_mode = True
