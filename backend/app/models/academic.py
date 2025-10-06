# C:\Users\fresh\OneDrive\Dokumen\thesis\proj\CODE\adaptive-exam-timetabling\backend\app\models\academic.py

import uuid
import enum

from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    String,
    Boolean,
    Integer,
    ForeignKey,
    Index,
    func,
    UniqueConstraint,
    Enum as SAEnum,
)

from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

from datetime import date, datetime

from sqlalchemy import ARRAY

from sqlalchemy.ext.associationproxy import association_proxy, AssociationProxy

# Remove direct imports that cause circular dependencies

# Use TYPE_CHECKING for type hints only

if TYPE_CHECKING:
    from .scheduling import (
        Exam,
        StaffUnavailability,
        Staff,
        ExamDepartment,
        TimeSlotTemplate,
    )
    from .jobs import TimetableJob
    from .file_uploads import FileUploadSession
    from .versioning import SessionTemplate
    from .users import User


# NEW ENUM to match the database schema
class SlotGenerationModeEnum(str, enum.Enum):
    fixed = "fixed"
    flexible = "flexible"


class AcademicSession(Base, TimestampMixin):
    __tablename__ = "academic_sessions"
    __table_args__ = {"schema": "exam_system"}

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    semester_system: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[Optional[bool]] = mapped_column(
        Boolean, default=False, nullable=True
    )

    # --- FIX for Circular Dependency ---
    # Add a name and use_alter=True to break the dependency cycle with session_templates.
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "exam_system.session_templates.id",
            name="fk_academic_sessions_template_id",
            use_alter=True,
        ),
        nullable=True,
    )
    archived_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    session_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    timeslot_template_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("exam_system.timeslot_templates.id"),
        nullable=True,
    )

    # --- FIX for DatatypeMismatchError ---
    # Make the SAEnum schema-aware by adding schema='exam_system'
    slot_generation_mode: Mapped[SlotGenerationModeEnum] = mapped_column(
        SAEnum(
            SlotGenerationModeEnum,
            name="slot_generation_mode_enum",
            create_type=False,
            schema="exam_system",
        ),
        nullable=False,
        default=SlotGenerationModeEnum.fixed,
    )

    # Use string references to avoid circular imports
    exams: Mapped[List["Exam"]] = relationship("Exam", back_populates="session")
    registrations: Mapped[List["CourseRegistration"]] = relationship(
        "CourseRegistration", back_populates="session"
    )
    staff_unavailability: Mapped[List["StaffUnavailability"]] = relationship(
        "StaffUnavailability", back_populates="session"
    )
    jobs: Mapped[List["TimetableJob"]] = relationship(
        "TimetableJob", back_populates="session"
    )
    file_uploads: Mapped[List["FileUploadSession"]] = relationship(
        "FileUploadSession", back_populates="session"
    )
    student_enrollments: Mapped[List["StudentEnrollment"]] = relationship(
        "StudentEnrollment", back_populates="session"
    )

    # RELATIONSHIPS
    template: Mapped["SessionTemplate"] = relationship(
        "SessionTemplate",
        foreign_keys=[template_id],
        back_populates="sessions",
        post_update=True,  # Helps resolve cycle during object flushing
    )
    session_templates: Mapped[List["SessionTemplate"]] = relationship(
        "SessionTemplate",
        foreign_keys="SessionTemplate.source_session_id",
        back_populates="source_session",
    )
    timeslot_template: Mapped[Optional["TimeSlotTemplate"]] = relationship(
        "TimeSlotTemplate", back_populates="academic_sessions"
    )

    # Add indexes for performance
    __table_args__ = (
        Index("idx_academic_sessions_template_id", "template_id"),
        Index("idx_academic_sessions_active", "is_active"),
        Index("idx_academic_sessions_archived_at", "archived_at"),
        {"schema": "exam_system"},  # Ensure table is created in the correct schema
    )


class CourseInstructor(Base, TimestampMixin):
    __tablename__ = "course_instructors"

    course_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        primary_key=True,
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("staff.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Relationships to the main tables
    course: Mapped["Course"] = relationship(back_populates="instructor_associations")
    staff: Mapped["Staff"] = relationship(back_populates="course_associations")


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    faculty_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("faculties.id"), nullable=False
    )
    is_active: Mapped[Optional[bool]] = mapped_column(
        Boolean, default=True, nullable=True
    )

    faculty: Mapped["Faculty"] = relationship("Faculty", back_populates="departments")
    programmes: Mapped[List["Programme"]] = relationship(
        "Programme", back_populates="department"
    )
    staff: Mapped[List["Staff"]] = relationship("Staff", back_populates="department")
    courses: Mapped[List["Course"]] = relationship(
        "Course", back_populates="department"
    )
    exam_departments: Mapped[List["ExamDepartment"]] = relationship(
        "ExamDepartment", back_populates="department", cascade="all, delete-orphan"
    )
    exams = association_proxy("exam_departments", "exam")


class Faculty(Base, TimestampMixin):
    __tablename__ = "faculties"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[Optional[bool]] = mapped_column(
        Boolean, default=True, nullable=True
    )

    departments: Mapped[List["Department"]] = relationship(
        "Department", back_populates="faculty"
    )


class Programme(Base):
    __tablename__ = "programmes"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)
    degree_type: Mapped[str] = mapped_column(String, nullable=False)
    duration_years: Mapped[int] = mapped_column(Integer, nullable=False)
    department_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False
    )
    is_active: Mapped[Optional[bool]] = mapped_column(
        Boolean, default=True, nullable=True
    )

    department: Mapped["Department"] = relationship(
        "Department", back_populates="programmes"
    )
    students: Mapped[List["Student"]] = relationship(
        "Student", back_populates="programme"
    )


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    credit_units: Mapped[int] = mapped_column(Integer, nullable=False)
    course_level: Mapped[int] = mapped_column(Integer, nullable=False)
    semester: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_practical: Mapped[Optional[bool]] = mapped_column(
        Boolean, default=False, nullable=True
    )
    morning_only: Mapped[Optional[bool]] = mapped_column(
        Boolean, default=False, nullable=True
    )
    exam_duration_minutes: Mapped[Optional[int]] = mapped_column(
        Integer, default=180, nullable=True
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False
    )
    is_active: Mapped[Optional[bool]] = mapped_column(
        Boolean, default=True, nullable=True
    )
    # REMOVED: The old instructor_id column is no longer needed.

    department: Mapped["Department"] = relationship(
        "Department", back_populates="courses"
    )
    exams: Mapped[List["Exam"]] = relationship("Exam", back_populates="course")
    registrations: Mapped[List["CourseRegistration"]] = relationship(
        "CourseRegistration", back_populates="course"
    )

    # NEW: Relationship to handle multiple instructors via the association model.
    instructor_associations: Mapped[List["CourseInstructor"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )
    instructors: AssociationProxy[List["Staff"]] = association_proxy(
        "instructor_associations", "staff"
    )


# MODIFIED: Student model holds permanent info
class Student(Base, TimestampMixin):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    matric_number: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    entry_year: Mapped[int] = mapped_column(Integer, nullable=False)
    special_needs: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    programme_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("programmes.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )

    programme: Mapped["Programme"] = relationship(
        "Programme", back_populates="students"
    )
    user: Mapped[Optional["User"]] = relationship("User")
    registrations: Mapped[List["CourseRegistration"]] = relationship(
        "CourseRegistration", back_populates="student"
    )
    enrollments: Mapped[List["StudentEnrollment"]] = relationship(
        "StudentEnrollment", back_populates="student"
    )


# NEW: StudentEnrollment model for session-specific data
class StudentEnrollment(Base):
    __tablename__ = "student_enrollments"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("students.id"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("academic_sessions.id"), nullable=False
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    student_type: Mapped[str | None] = mapped_column(
        String, default="regular", nullable=True
    )
    is_active: Mapped[bool | None] = mapped_column(Boolean, default=True, nullable=True)

    student: Mapped["Student"] = relationship("Student", back_populates="enrollments")
    session: Mapped["AcademicSession"] = relationship(
        "AcademicSession", back_populates="student_enrollments"
    )

    __table_args__ = (
        UniqueConstraint("student_id", "session_id", name="student_session_key"),
    )


class CourseRegistration(Base):
    __tablename__ = "course_registrations"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("students.id"), nullable=False
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("academic_sessions.id"), nullable=False
    )
    registration_type: Mapped[str] = mapped_column(
        String, default="normal", nullable=False
    )
    registered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now(), nullable=True
    )

    student: Mapped["Student"] = relationship("Student", back_populates="registrations")
    course: Mapped["Course"] = relationship("Course", back_populates="registrations")
    session: Mapped["AcademicSession"] = relationship(
        "AcademicSession", back_populates="registrations"
    )
