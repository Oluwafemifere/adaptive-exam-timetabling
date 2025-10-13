# backend/app/schemas/session_management.py
"""
Pydantic schemas for the SessionManagement API, which provides a direct
interface to the session-aware PL/pgSQL functions.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date


# =========================================================================
# Payloads for Create/Update Operations
# These schemas define the expected JSON body for POST/PUT requests.
# =========================================================================


class CoursePayload(BaseModel):
    """Payload for creating or updating a course within a session."""

    code: str = Field(..., description="The unique code for the course, e.g., 'CS101'.")
    title: str = Field(..., description="The full title of the course.")
    credit_units: int = Field(..., gt=0, description="The number of credit units.")
    course_level: int = Field(
        ..., gt=0, description="The level of the course, e.g., 100, 200."
    )
    semester: Optional[int] = Field(
        None, ge=1, le=2, description="The semester the course is offered in."
    )
    exam_duration_minutes: int = Field(
        180, gt=0, description="The duration of the exam in minutes."
    )
    is_practical: Optional[bool] = False
    morning_only: Optional[bool] = False
    is_active: Optional[bool] = True


class BuildingPayload(BaseModel):
    """Payload for creating or updating a building within a session."""

    code: str = Field(
        ..., description="The unique code for the building, e.g., 'ENG_HALL'."
    )
    name: str = Field(..., description="The full name of the building.")
    is_active: Optional[bool] = True


class RoomPayload(BaseModel):
    """Payload for creating or updating a room within a session."""

    code: str = Field(..., description="The unique code for the room, e.g., 'R101'.")
    name: str = Field(..., description="The descriptive name of the room.")
    building_id: UUID = Field(
        ..., description="The ID of the building this room is in."
    )
    capacity: int = Field(
        ..., gt=0, description="The total seating capacity of the room."
    )
    exam_capacity: int = Field(..., gt=0, description="The exam seating capacity.")
    floor_number: Optional[int] = None
    has_projector: Optional[bool] = False
    max_inv_per_room: Optional[int] = 1
    is_active: Optional[bool] = True


class DepartmentPayload(BaseModel):
    """Payload for creating or updating a department."""

    code: str = Field(..., description="The unique code for the department.")
    name: str = Field(..., description="The name of the department.")
    faculty_id: UUID = Field(..., description="The ID of the parent faculty.")
    is_active: Optional[bool] = True


class StaffPayload(BaseModel):
    """Payload for creating or updating a staff member."""

    staff_number: str = Field(..., description="The unique staff identifier number.")
    first_name: str
    last_name: str
    department_id: Optional[UUID] = None
    position: Optional[str] = None
    staff_type: Optional[str] = "Academic"
    can_invigilate: Optional[bool] = True
    is_active: Optional[bool] = True


class ExamPayload(BaseModel):
    """Payload for creating or updating an exam."""

    course_id: UUID
    duration_minutes: int = Field(..., gt=0)
    expected_students: int = Field(..., ge=0)
    status: Optional[str] = "pending"
    is_practical: Optional[bool] = False
    morning_only: Optional[bool] = False
    requires_projector: Optional[bool] = False


class StaffUnavailabilityPayload(BaseModel):
    """Payload for creating a staff unavailability record."""

    staff_id: UUID
    unavailable_date: date
    time_slot_period: str = Field(
        ..., description="Name of the unavailable period, e.g., 'Morning', 'Afternoon'."
    )
    reason: Optional[str] = None


# =========================================================================
# Response Schemas for Paginated Data
# =========================================================================


class PaginatedResponse(BaseModel):
    """Generic structure for paginated responses."""

    total_items: int
    page: int
    page_size: int
    data: List[Dict[str, Any]]


class PaginatedCoursesResponse(PaginatedResponse): ...


class PaginatedStudentsResponse(PaginatedResponse): ...


class PaginatedStaffResponse(PaginatedResponse): ...


class PaginatedExamsResponse(PaginatedResponse): ...


class PaginatedDepartmentsResponse(PaginatedResponse): ...


# =========================================================================
# Response Schemas for the Full Data Graph
# =========================================================================


class RoomInGraph(BaseModel):
    id: UUID
    code: str
    name: str
    exam_capacity: int


class BuildingInGraph(BaseModel):
    id: UUID
    name: str
    rooms: List[RoomInGraph]


class StudentInGraph(BaseModel):
    id: UUID
    matric_number: str
    first_name: str
    last_name: str


class ProgrammeInGraph(BaseModel):
    id: UUID
    code: str
    name: str
    students: List[StudentInGraph]


class DepartmentInGraph(BaseModel):
    id: UUID
    code: str
    name: str
    programmes: List[ProgrammeInGraph]


class FacultyInGraph(BaseModel):
    id: UUID
    code: str
    name: str
    departments: List[DepartmentInGraph]


class InstructorInGraph(BaseModel):
    id: UUID
    first_name: str
    last_name: str


class CourseInGraph(BaseModel):
    id: UUID
    code: str
    title: str
    exam_duration_minutes: int
    student_ids: List[UUID]
    instructors: List[InstructorInGraph]


class StaffInGraph(BaseModel):
    id: UUID
    staff_number: str
    first_name: str
    last_name: str
    department_name: Optional[str] = None
    can_invigilate: bool


class SessionInfo(BaseModel):
    id: UUID
    name: str
    start_date: date
    end_date: date


class ScheduleItemInGraph(BaseModel):
    assignment_id: UUID
    exam_id: UUID
    room_id: UUID
    exam_date: date
    student_count: int
    course_code: str
    course_title: str
    room_name: str
    building_name: str
    # Add other relevant schedule fields if needed


class SessionDataGraphResponse(BaseModel):
    """
    Defines the comprehensive, nested JSON structure of all data for a given session.
    """

    session: Optional[SessionInfo] = None
    published_schedule: Optional[List[ScheduleItemInGraph]] = None
    faculties: List[FacultyInGraph]
    courses: List[CourseInGraph]
    buildings: List[BuildingInGraph]
    staff: List[StaffInGraph]
