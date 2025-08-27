#C:\Users\fresh\OneDrive\Dokumen\thesis\proj\CODE\adaptive-exam-timetabling\backend\app\models\academic.py
import uuid
from typing import List, Optional

from sqlalchemy import Date, DateTime, String, Boolean, Integer, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .scheduling import Exam, StaffUnavailability, Staff
from .jobs import TimetableJob
from .file_uploads import FileUploadSession
from .base import Base, TimestampMixin


class AcademicSession(Base, TimestampMixin):
    __tablename__ = "academic_sessions"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    semester_system: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[str] = mapped_column(Date, nullable=False)
    end_date: Mapped[str] = mapped_column(Date, nullable=False)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)

    exams: Mapped[List["Exam"]] = relationship("Exam", back_populates="session")
    registrations: Mapped[List["CourseRegistration"]] = relationship("CourseRegistration", back_populates="session")
    file_uploads: Mapped[List["FileUploadSession"]] = relationship("FileUploadSession", back_populates="session")
    staff_unavailability: Mapped[List["StaffUnavailability"]] = relationship("StaffUnavailability", back_populates="session")
    jobs: Mapped[List["TimetableJob"]] = relationship("TimetableJob", back_populates="session")


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    faculty_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("faculties.id"), nullable=False)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True, nullable=True)

    faculty: Mapped["Faculty"] = relationship("Faculty", back_populates="departments")
    programmes: Mapped[List["Programme"]] = relationship("Programme", back_populates="department")
    staff: Mapped[List["Staff"]] = relationship("Staff", back_populates="department")
    courses: Mapped[List["Course"]] = relationship("Course", back_populates="department")


class Faculty(Base, TimestampMixin):
    __tablename__ = "faculties"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True, nullable=True)

    departments: Mapped[List["Department"]] = relationship("Department", back_populates="faculty")


class Programme(Base, TimestampMixin):
    __tablename__ = "programmes"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)
    degree_type: Mapped[str] = mapped_column(String, nullable=False)
    duration_years: Mapped[int] = mapped_column(Integer, nullable=False)
    department_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True, nullable=True)

    department: Mapped["Department"] = relationship("Department", back_populates="programmes")
    students: Mapped[List["Student"]] = relationship("Student", back_populates="programme")


class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    credit_units: Mapped[int] = mapped_column(Integer, nullable=False)
    course_level: Mapped[int] = mapped_column(Integer, nullable=False)
    semester: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_practical: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)
    morning_only: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)
    exam_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, default=180, nullable=True)
    department_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True, nullable=True)

    department: Mapped["Department"] = relationship("Department", back_populates="courses")
    exams: Mapped[List["Exam"]] = relationship("Exam", back_populates="course")
    registrations: Mapped[List["CourseRegistration"]] = relationship("CourseRegistration", back_populates="course")


class Student(Base, TimestampMixin):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    matric_number: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    entry_year: Mapped[int] = mapped_column(Integer, nullable=False)
    current_level: Mapped[int] = mapped_column(Integer, nullable=False)
    student_type: Mapped[str] = mapped_column(String, default="regular", nullable=True)
    special_needs: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    programme_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("programmes.id"), nullable=False)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True, nullable=True)

    programme: Mapped["Programme"] = relationship("Programme", back_populates="students")
    registrations: Mapped[List["CourseRegistration"]] = relationship("CourseRegistration", back_populates="student")


class CourseRegistration(Base, TimestampMixin):
    __tablename__ = "course_registrations"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("students.id"), nullable=False)
    course_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("academic_sessions.id"), nullable=False)
    registration_type: Mapped[str] = mapped_column(String, default="regular", nullable=True)
    registered_at: Mapped[Optional[str]] = mapped_column(DateTime, server_default=func.now(), nullable=True)

    student: Mapped["Student"] = relationship("Student", back_populates="registrations")
    course: Mapped["Course"] = relationship("Course", back_populates="registrations")
    session: Mapped["AcademicSession"] = relationship("AcademicSession", back_populates="registrations")
