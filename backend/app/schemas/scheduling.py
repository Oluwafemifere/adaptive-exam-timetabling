# app/schemas/scheduling.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date, time, datetime


class TimeSlotRead(BaseModel):
    id: UUID
    name: str
    start_time: time
    end_time: time
    duration_minutes: int
    is_active: bool

    class Config:
        orm_mode = True


class RoomAssignment(BaseModel):
    room_id: UUID
    allocated_capacity: int
    is_primary: bool

    class Config:
        orm_mode = True


class ExamRead(BaseModel):
    id: UUID
    course_id: UUID
    session_id: UUID
    time_slot_id: Optional[UUID]
    exam_date: Optional[date]
    duration_minutes: int
    expected_students: int
    requires_special_arrangements: bool
    status: str
    notes: Optional[str]
    room_assignments: List[RoomAssignment] = []

    class Config:
        orm_mode = True


class StaffRead(BaseModel):
    id: UUID
    staff_number: str
    staff_type: str
    position: Optional[str]
    department_id: Optional[UUID]
    can_invigilate: bool
    max_daily_sessions: int
    max_consecutive_sessions: int
    is_active: bool

    class Config:
        orm_mode = True


class StaffUnavailabilityRead(BaseModel):
    id: UUID
    staff_id: UUID
    session_id: UUID
    unavailable_date: date
    time_slot_id: Optional[UUID]
    reason: Optional[str]

    class Config:
        orm_mode = True


# New schemas for the scheduling router
class SchedulingDataResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any]


class TimetableGenerationRequest(BaseModel):
    session_id: UUID
    configuration_id: UUID
    options: Optional[Dict[str, Any]] = None


class TimetableGenerationResponse(BaseModel):
    success: bool
    message: str
    job_id: UUID
    status: str
    estimated_completion_minutes: int


class ConflictAnalysisResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any]


class SchedulingJobResponse(BaseModel):
    success: bool
    job: Any  # This should be TimetableJobRead from jobs schema
