# backend/app/schemas/staging.py
"""Pydantic schemas for interacting with staging table records."""

from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from uuid import UUID
from datetime import date


# =================== Buildings ===================
class BuildingCreate(BaseModel):
    code: str
    name: str
    faculty_code: str


class BuildingUpdate(BaseModel):
    name: Optional[str] = None
    faculty_code: Optional[str] = None


# =================== Course Departments ===================
class CourseDepartmentCreate(BaseModel):
    course_code: str
    department_code: str


class CourseDepartmentUpdate(BaseModel):
    department_code: str  # The primary key part (course_code) cannot be changed


# =================== Course Faculties ===================
class CourseFacultyCreate(BaseModel):
    course_code: str
    faculty_code: str


class CourseFacultyUpdate(BaseModel):
    faculty_code: str


# =================== Course Instructors ===================
class CourseInstructorCreate(BaseModel):
    staff_number: str
    course_code: str


# =================== Course Registrations ===================
class CourseRegistrationCreate(BaseModel):
    student_matric_number: str
    course_code: str
    registration_type: str = "regular"


class CourseRegistrationUpdate(BaseModel):
    registration_type: str


# =================== Courses ===================
class CourseCreate(BaseModel):
    code: str
    title: str
    credit_units: int
    exam_duration_minutes: int
    course_level: int
    semester: int
    is_practical: bool
    morning_only: bool


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    credit_units: Optional[int] = None
    exam_duration_minutes: Optional[int] = None
    course_level: Optional[int] = None
    semester: Optional[int] = None
    is_practical: Optional[bool] = None
    morning_only: Optional[bool] = None


# =================== Departments ===================
class DepartmentCreate(BaseModel):
    code: str
    name: str
    faculty_code: str


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    faculty_code: Optional[str] = None


# =================== Faculties ===================
class FacultyCreate(BaseModel):
    code: str
    name: str


class FacultyUpdate(BaseModel):
    name: Optional[str] = None


# =================== Programmes ===================
class ProgrammeCreate(BaseModel):
    code: str
    name: str
    department_code: str
    degree_type: str
    duration_years: int


class ProgrammeUpdate(BaseModel):
    name: Optional[str] = None
    department_code: Optional[str] = None
    degree_type: Optional[str] = None
    duration_years: Optional[int] = None


# =================== Rooms ===================
class RoomCreate(BaseModel):
    code: str
    name: str
    building_code: str
    capacity: int
    exam_capacity: int
    has_ac: bool
    has_projector: bool
    has_computers: bool
    max_inv_per_room: int
    room_type_code: str
    floor_number: int
    accessibility_features: List[str]
    notes: Optional[str] = None


class RoomUpdate(BaseModel):
    name: Optional[str] = None
    building_code: Optional[str] = None
    capacity: Optional[int] = None
    exam_capacity: Optional[int] = None
    has_ac: Optional[bool] = None
    has_projector: Optional[bool] = None
    has_computers: Optional[bool] = None
    max_inv_per_room: Optional[int] = None
    room_type_code: Optional[str] = None
    floor_number: Optional[int] = None
    accessibility_features: Optional[List[str]] = None
    notes: Optional[str] = None


# =================== Staff ===================
class StaffCreate(BaseModel):
    staff_number: str
    first_name: str
    last_name: str
    email: EmailStr
    department_code: str
    staff_type: str
    can_invigilate: bool
    is_instructor: bool
    max_daily_sessions: int
    max_consecutive_sessions: int
    max_concurrent_exams: int
    max_students_per_invigilator: int
    user_email: Optional[EmailStr] = None


class StaffUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    department_code: Optional[str] = None
    staff_type: Optional[str] = None
    can_invigilate: Optional[bool] = None
    is_instructor: Optional[bool] = None
    max_daily_sessions: Optional[int] = None
    max_consecutive_sessions: Optional[int] = None
    max_concurrent_exams: Optional[int] = None
    max_students_per_invigilator: Optional[int] = None
    user_email: Optional[EmailStr] = None


# =================== Staff Unavailability ===================
class StaffUnavailabilityCreate(BaseModel):
    staff_number: str
    unavailable_date: date
    period_name: str
    reason: Optional[str] = None


class StaffUnavailabilityUpdate(BaseModel):
    reason: str


# =================== Students ===================
class StudentCreate(BaseModel):
    matric_number: str
    first_name: str
    last_name: str
    entry_year: int
    programme_code: str
    user_email: Optional[EmailStr] = None


class StudentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    entry_year: Optional[int] = None
    programme_code: Optional[str] = None
    user_email: Optional[EmailStr] = None


# =================================================================
# Staging Data Read Models
# =================================================================
# These models represent the data as it is read from the database.


class Building(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    faculty_code: Optional[str] = None


class CourseDepartment(BaseModel):
    course_code: Optional[str] = None
    department_code: Optional[str] = None


class CourseFaculty(BaseModel):
    course_code: Optional[str] = None
    faculty_code: Optional[str] = None


class CourseInstructor(BaseModel):
    staff_number: Optional[str] = None
    course_code: Optional[str] = None


class CourseRegistration(BaseModel):
    student_matric_number: Optional[str] = None
    course_code: Optional[str] = None
    registration_type: Optional[str] = None


class Course(BaseModel):
    code: Optional[str] = None
    title: Optional[str] = None
    credit_units: Optional[int] = None
    exam_duration_minutes: Optional[int] = None
    course_level: Optional[int] = None
    semester: Optional[int] = None
    is_practical: Optional[bool] = None
    morning_only: Optional[bool] = None


class Department(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    faculty_code: Optional[str] = None


class Faculty(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None


class Programme(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    department_code: Optional[str] = None
    degree_type: Optional[str] = None
    duration_years: Optional[int] = None


class Room(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    building_code: Optional[str] = None
    capacity: Optional[int] = None
    exam_capacity: Optional[int] = None
    has_ac: Optional[bool] = None
    has_projector: Optional[bool] = None
    has_computers: Optional[bool] = None
    max_inv_per_room: Optional[int] = None
    room_type_code: Optional[str] = None
    floor_number: Optional[int] = None
    accessibility_features: Optional[List[str]] = None
    notes: Optional[str] = None


class Staff(BaseModel):
    staff_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    department_code: Optional[str] = None
    staff_type: Optional[str] = None
    can_invigilate: Optional[bool] = None
    is_instructor: Optional[bool] = None
    max_daily_sessions: Optional[int] = None
    max_consecutive_sessions: Optional[int] = None
    max_concurrent_exams: Optional[int] = None
    max_students_per_invigilator: Optional[int] = None
    user_email: Optional[EmailStr] = None


class StaffUnavailability(BaseModel):
    staff_number: Optional[str] = None
    unavailable_date: Optional[date] = None
    period_name: Optional[str] = None
    reason: Optional[str] = None


class Student(BaseModel):
    matric_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    entry_year: Optional[int] = None
    programme_code: Optional[str] = None
    user_email: Optional[EmailStr] = None


# =================== Main Response Schema ===================


class StagedSessionData(BaseModel):
    """Container schema for all data in a staging session."""

    buildings: List[Building]
    course_departments: List[CourseDepartment]
    course_faculties: List[CourseFaculty]
    course_instructors: List[CourseInstructor]
    course_registrations: List[CourseRegistration]
    courses: List[Course]
    departments: List[Department]
    faculties: List[Faculty]
    programmes: List[Programme]
    rooms: List[Room]
    staff: List[Staff]
    staff_unavailability: List[StaffUnavailability]
    students: List[Student]
