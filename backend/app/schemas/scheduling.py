# app/schemas/scheduling.py
from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date, time, datetime

MODEL_CONFIG = ConfigDict(from_attributes=True)


class TimeSlotRead(BaseModel):
    model_config = MODEL_CONFIG

    id: UUID
    name: str
    start_time: time
    end_time: time
    duration_minutes: int
    is_active: bool


class RoomAssignment(BaseModel):
    model_config = MODEL_CONFIG

    room_id: UUID
    allocated_capacity: int
    is_primary: bool


class ExamRead(BaseModel):
    model_config = MODEL_CONFIG

    id: UUID
    course_id: UUID
    session_id: UUID
    time_slot_id: Optional[UUID] = None
    exam_date: Optional[date] = None
    duration_minutes: int
    expected_students: int
    requires_special_arrangements: bool = False
    status: str
    notes: Optional[str] = None
    room_assignments: List[RoomAssignment] = Field(default_factory=list)


class StaffRead(BaseModel):
    model_config = MODEL_CONFIG

    id: UUID
    staff_number: str
    staff_type: str
    position: Optional[str] = None
    department_id: Optional[UUID] = None
    can_invigilate: bool = False
    max_daily_sessions: int = 2
    max_consecutive_sessions: int = 2
    is_active: bool = True


class StaffUnavailabilityRead(BaseModel):
    model_config = MODEL_CONFIG

    id: UUID
    staff_id: UUID
    session_id: UUID
    unavailable_date: date
    time_slot_id: Optional[UUID] = None
    reason: Optional[str] = None


# Router-level request/response models


class SchedulingDataResponse(BaseModel):
    model_config = MODEL_CONFIG

    success: bool
    message: str
    data: Dict[str, Any]


class TimetableGenerationRequest(BaseModel):
    model_config = MODEL_CONFIG

    session_id: UUID
    configuration_id: UUID
    options: Optional[Dict[str, Any]] = None


class TimetableGenerationResponse(BaseModel):
    model_config = MODEL_CONFIG

    success: bool
    message: str
    job_id: UUID
    status: str
    estimated_completion_minutes: int


class ConflictAnalysisResponse(BaseModel):
    model_config = MODEL_CONFIG

    success: bool
    message: str
    data: Dict[str, Any]


class SchedulingJobResponse(BaseModel):
    model_config = MODEL_CONFIG

    success: bool
    job: Any  # usually TimetableJobRead
