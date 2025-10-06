# backend/app/schemas/reports.py
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Any
from uuid import UUID
from datetime import datetime, date


class ReportSummaryCounts(BaseModel):
    """Defines the summary counts for all reports and requests."""

    total: int
    unread: int
    urgent_action_required: int


class StudentInfo(BaseModel):
    """Represents the student details attached to a conflict report."""

    id: UUID
    matric_number: str
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None


class StaffInfo(BaseModel):
    """Represents the staff details attached to a change request."""

    id: UUID
    staff_number: str
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    department_code: Optional[str] = None


class ExamDetails(BaseModel):
    """Represents the exam details attached to a report."""

    exam_id: UUID
    course_code: str
    course_title: str
    session_name: str


class AssignmentDetails(BaseModel):
    """Represents the assignment details attached to a request."""

    assignment_id: UUID
    exam_date: date
    course_code: str
    course_title: str
    room_code: str
    room_name: str


class ReviewDetails(BaseModel):
    """Represents the review details for a report or request."""

    reviewed_by_user_id: UUID
    reviewer_email: Optional[EmailStr] = None
    reviewer_name: Optional[str] = None
    resolver_notes: Optional[str] = None
    review_notes: Optional[str] = None


class ConflictReportItem(BaseModel):
    """Defines the structure for a single student conflict report."""

    id: UUID
    status: str
    description: Optional[str] = None
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    student: StudentInfo
    exam_details: ExamDetails
    review_details: Optional[ReviewDetails] = None


class ChangeRequestItem(BaseModel):
    """Defines the structure for a single staff change request."""

    id: UUID
    status: str
    reason: Optional[str] = None
    description: Optional[str] = None
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    staff: StaffInfo
    assignment_details: AssignmentDetails
    review_details: Optional[ReviewDetails] = None


class AllReportsResponse(BaseModel):
    """The main response model for the reports and requests endpoint."""

    summary_counts: ReportSummaryCounts
    conflict_reports: List[ConflictReportItem]
    assignment_change_requests: List[ChangeRequestItem]

    class Config:
        from_attributes = True
