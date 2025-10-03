# app/schemas/academic.py
"""Pydantic v2 schemas for academic domain."""

from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date, datetime

# Use attribute loading for ORM compatibility
MODEL_CONFIG = ConfigDict(from_attributes=True)


# --- Academic Session ---
class AcademicSessionBase(BaseModel):
    name: str
    start_date: date
    end_date: date
    timeslot_template_id: UUID


class AcademicSessionCreate(AcademicSessionBase):
    pass


class AcademicSessionUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    timeslot_template_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class AcademicSessionRead(BaseModel):
    model_config = MODEL_CONFIG

    id: UUID
    name: str
    semester_system: Optional[str] = None
    start_date: date
    end_date: date
    is_active: Optional[bool] = None
    template_id: Optional[UUID] = None
    archived_at: Optional[datetime] = None
    session_config: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    timeslot_template_id: Optional[UUID] = None

    # avoid deep circular nesting; expose related ids
    exam_ids: List[UUID] = Field(default_factory=list)
    registration_ids: List[UUID] = Field(default_factory=list)
    timetable_job_ids: List[UUID] = Field(alias="jobs", default_factory=list)
    staff_unavailability_ids: List[UUID] = Field(default_factory=list)
    student_enrollment_ids: List[UUID] = Field(
        alias="student_enrollments", default_factory=list
    )
    file_upload_ids: List[UUID] = Field(alias="file_uploads", default_factory=list)


# --- Course Schemas ---
class CourseBase(BaseModel):
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


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    code: Optional[str] = None
    title: Optional[str] = None
    credit_units: Optional[int] = None
    course_level: Optional[int] = None
    semester: Optional[int] = None
    department_id: Optional[UUID] = None
    exam_duration_minutes: Optional[int] = None
    is_practical: Optional[bool] = None
    morning_only: Optional[bool] = None
    is_active: Optional[bool] = None


class CourseRead(CourseBase):
    model_config = MODEL_CONFIG
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    registration_ids: List[UUID] = Field(default_factory=list)
    exam_ids: List[UUID] = Field(default_factory=list)
    instructor_ids: List[UUID] = Field(default_factory=list)


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
    exam_ids: List[UUID] = Field(default_factory=list)


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


class StudentRead(BaseModel):
    model_config = MODEL_CONFIG

    id: Optional[UUID] = None
    matric_number: str
    first_name: str
    last_name: str
    programme_id: UUID
    entry_year: int
    special_needs: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user_id: Optional[UUID] = None
    registration_ids: List[UUID] = Field(default_factory=list)
    enrollment_ids: List[UUID] = Field(alias="enrollments", default_factory=list)


class StudentEnrollmentRead(BaseModel):
    model_config = MODEL_CONFIG
    id: UUID
    student_id: UUID
    session_id: UUID
    level: int
    student_type: Optional[str] = "regular"
    is_active: Optional[bool] = True


class CourseRegistrationRead(BaseModel):
    model_config = MODEL_CONFIG

    id: Optional[UUID] = None
    student_id: UUID
    course_id: UUID
    session_id: UUID
    registration_type: str = "regular"
    registered_at: Optional[datetime] = None
