# app/schemas/academic.py
"""Pydantic v2 schemas for academic domain."""

from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime

# Use attribute loading for ORM compatibility
MODEL_CONFIG = ConfigDict(from_attributes=True)


class AcademicSessionRead(BaseModel):
    model_config = MODEL_CONFIG

    id: Optional[UUID] = None
    name: str
    semester_system: str
    start_date: date
    end_date: date
    is_active: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # avoid deep circular nesting; expose related ids
    exam_ids: List[UUID] = Field(default_factory=list)
    registration_ids: List[UUID] = Field(default_factory=list)
    timetable_job_ids: List[UUID] = Field(default_factory=list)
    staff_unavailability_ids: List[UUID] = Field(default_factory=list)


class FacultyRead(BaseModel):
    model_config = MODEL_CONFIG

    id: Optional[UUID] = None
    name: str
    code: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    department_ids: List[UUID] = Field(default_factory=list)


class DepartmentRead(BaseModel):
    model_config = MODEL_CONFIG

    id: Optional[UUID] = None
    name: str
    code: str
    faculty_id: UUID
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    programme_ids: List[UUID] = Field(default_factory=list)
    course_ids: List[UUID] = Field(default_factory=list)
    staff_ids: List[UUID] = Field(default_factory=list)


class ProgrammeRead(BaseModel):
    model_config = MODEL_CONFIG

    id: Optional[UUID] = None
    name: str
    code: str
    department_id: UUID
    degree_type: str
    duration_years: int
    is_active: bool = True
    created_at: Optional[datetime] = None
    student_ids: List[UUID] = Field(default_factory=list)


class CourseRead(BaseModel):
    model_config = MODEL_CONFIG

    id: Optional[UUID] = None
    code: str
    title: str
    credit_units: int
    course_level: int
    semester: Optional[int] = None
    department_id: UUID
    exam_duration_minutes: int = 180
    is_practical: bool = False
    morning_only: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    registration_ids: List[UUID] = Field(default_factory=list)
    exam_ids: List[UUID] = Field(default_factory=list)


class StudentRead(BaseModel):
    model_config = MODEL_CONFIG

    id: Optional[UUID] = None
    matric_number: str
    programme_id: UUID
    current_level: int
    entry_year: int
    student_type: str = "regular"
    special_needs: Optional[List[str]] = None
    user_id: Optional[UUID] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    registration_ids: List[UUID] = Field(default_factory=list)


class StaffRead(BaseModel):
    model_config = MODEL_CONFIG

    id: Optional[UUID] = None
    staff_number: str
    staff_type: str
    position: Optional[str] = None
    department_id: Optional[UUID] = None
    can_invigilate: bool = False
    max_daily_sessions: int = 2
    max_consecutive_sessions: int = 2
    user_id: Optional[UUID] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    unavailability_ids: List[UUID] = Field(default_factory=list)
    invigilator_assignment_ids: List[UUID] = Field(default_factory=list)


class CourseRegistrationRead(BaseModel):
    model_config = MODEL_CONFIG

    id: Optional[UUID] = None
    student_id: UUID
    course_id: UUID
    session_id: UUID
    registration_type: str = "regular"
    registered_at: Optional[datetime] = None


class StaffUnavailabilityRead(BaseModel):
    model_config = MODEL_CONFIG

    id: Optional[UUID] = None
    staff_id: UUID
    session_id: UUID
    unavailable_date: date
    time_slot_id: Optional[UUID] = None
    reason: Optional[str] = None
    created_at: Optional[datetime] = None
