# app/schemas/scheduling.py
"""Pydantic v2 schemas for scheduling domain."""

from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date, time, datetime

MODEL_CONFIG = ConfigDict(from_attributes=True)


# --- Base Schemas ---


class ExamBase(BaseModel):
    course_id: UUID
    session_id: UUID
    duration_minutes: int
    expected_students: int
    requires_special_arrangements: bool = False
    status: str = "pending"
    notes: Optional[str] = None
    is_practical: bool = False
    requires_projector: bool = False
    is_common: bool = False
    morning_only: bool = False


class ExamCreate(ExamBase):
    pass


class ExamUpdate(BaseModel):
    course_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    duration_minutes: Optional[int] = None
    expected_students: Optional[int] = None
    requires_special_arrangements: Optional[bool] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    is_practical: Optional[bool] = None
    requires_projector: Optional[bool] = None
    is_common: Optional[bool] = None
    morning_only: Optional[bool] = None


class TimetableAssignmentRead(BaseModel):
    model_config = MODEL_CONFIG

    id: UUID
    exam_id: UUID
    room_id: UUID
    time_slot_id: UUID
    student_count: int
    is_confirmed: bool
    version_id: Optional[UUID] = None
    allocated_capacity: int
    is_primary: bool
    seating_arrangement: Optional[Dict[str, Any]] = None
    invigilator_ids: List[UUID] = Field(alias="invigilators", default_factory=list)


class ExamRead(ExamBase):
    model_config = MODEL_CONFIG
    id: UUID
    timetable_assignment_ids: List[UUID] = Field(
        alias="timetable_assignments", default_factory=list
    )
    prerequisite_ids: List[UUID] = Field(alias="prerequisites", default_factory=list)
    dependent_exam_ids: List[UUID] = Field(
        alias="dependent_exams", default_factory=list
    )
    department_ids: List[UUID] = Field(default_factory=list)


class StaffRead(BaseModel):
    model_config = MODEL_CONFIG

    id: UUID
    staff_number: str
    first_name: str
    last_name: str
    staff_type: str
    position: Optional[str] = None
    department_id: Optional[UUID] = None
    can_invigilate: bool = False
    max_daily_sessions: int = 2
    max_consecutive_sessions: int = 2
    max_concurrent_exams: int = 1
    max_students_per_invigilator: int = 50
    generic_availability_preferences: Optional[Dict[str, Any]] = None
    user_id: Optional[UUID] = None
    is_active: bool = True


class StaffUnavailabilityRead(BaseModel):
    model_config = MODEL_CONFIG

    id: UUID
    staff_id: UUID
    session_id: UUID
    unavailable_date: date
    time_slot_period: Optional[str] = None
    reason: Optional[str] = None


# Router-level request/response models


class SchedulingDataResponse(BaseModel):
    model_config = MODEL_CONFIG

    success: bool
    message: str
    data: Dict[str, Any]


class TimeslotTemplate(BaseModel):
    """Schema for defining a timeslot template."""

    name: str = Field(
        ..., description="The name of the timeslot (e.g., 'Morning', 'Afternoon')."
    )
    start_time: time = Field(..., description="The start time of the timeslot.")
    end_time: time = Field(..., description="The end time of the timeslot.")


class TimetableGenerationRequest(BaseModel):
    model_config = MODEL_CONFIG

    session_id: UUID
    configuration_id: Optional[UUID] = None
    options: Optional[Dict[str, Any]] = None
    start_date: date
    end_date: date
    timeslot_templates: List[TimeslotTemplate] = Field(
        ..., description="A list of templates defining the timeslots for each day."
    )


class TimetableGenerationResponse(BaseModel):
    model_config = MODEL_CONFIG

    success: bool
    message: str
    job_id: UUID
    status: str
    estimated_completion_minutes: int = 15


class ConflictAnalysisResponse(BaseModel):
    model_config = MODEL_CONFIG

    success: bool
    message: str
    data: Dict[str, Any]


# --- NEWLY ADDED SCHEMAS ---


class ManualTimetableEditCreate(BaseModel):
    exam_id: UUID
    old_values: Dict[str, Any]
    new_values: Dict[str, Any]
    reason: str = Field(..., min_length=10)


class TimetableValidationRequest(BaseModel):
    version_id: UUID
    assignments: List[Dict[str, Any]]
