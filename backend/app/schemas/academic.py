# app/models/academic.py
"""
Academic-related database models for the Adaptive Exam Timetabling System.
Includes models for students, courses, registrations, faculties, departments, and programmes.
"""

from sqlalchemy import Column, String, Integer, Boolean, Date, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship, backref, Mapped, mapped_column, DeclarativeBase
from sqlalchemy.sql import func
import uuid
from typing import List, Optional
from datetime import datetime


# Modern SQLAlchemy 2.x approach for Base class
class Base(DeclarativeBase):
    pass


class AcademicSession(Base):
    """Academic session/year model."""
    __tablename__ = 'academic_sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    semester_system = Column(String, nullable=False)  # "Two Semester", "Three Semester", etc.
    is_active = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    exams = relationship("Exam", back_populates="academic_session", cascade="all, delete-orphan")
    registrations = relationship("CourseRegistration", back_populates="academic_session", cascade="all, delete-orphan")
    timetable_jobs = relationship("TimetableJob", back_populates="academic_session", cascade="all, delete-orphan")
    staff_unavailability = relationship("StaffUnavailability", back_populates="academic_session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AcademicSession(name='{self.name}', active={self.is_active})>"


class Faculty(Base):
    """Faculty/School model."""
    __tablename__ = 'faculties'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    departments = relationship("Department", back_populates="faculty", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Faculty(name='{self.name}', code='{self.code}')>"


class Department(Base):
    """Department model."""
    __tablename__ = 'departments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False, unique=True, index=True)
    faculty_id = Column(UUID(as_uuid=True), ForeignKey('faculties.id'), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    faculty = relationship("Faculty", back_populates="departments")
    programmes = relationship("Programme", back_populates="department", cascade="all, delete-orphan")
    courses = relationship("Course", back_populates="department", cascade="all, delete-orphan")
    staff = relationship("Staff", back_populates="department")
    
    def __repr__(self):
        return f"<Department(name='{self.name}', code='{self.code}')>"


class Programme(Base):
    """Academic programme model."""
    __tablename__ = 'programmes'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)  # Not unique as different departments might have similar codes
    department_id = Column(UUID(as_uuid=True), ForeignKey('departments.id'), nullable=False)
    degree_type = Column(String, nullable=False)  # Bachelor, Masters, PhD, etc.
    duration_years = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    department = relationship("Department", back_populates="programmes")
    students = relationship("Student", back_populates="programme", cascade="all, delete-orphan")
    
    # Unique constraint on code within department
    __table_args__ = (
        UniqueConstraint('code', 'department_id', name='unique_programme_code_per_department'),
        Index('idx_programme_department', 'department_id'),
    )
    
    def __repr__(self):
        return f"<Programme(name='{self.name}', code='{self.code}', type='{self.degree_type}')>"


class Course(Base):
    """Course model."""
    __tablename__ = 'courses'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String, nullable=False, unique=True, index=True)
    title = Column(String, nullable=False)
    credit_units = Column(Integer, nullable=False)
    course_level = Column(Integer, nullable=False)  # 100, 200, 300, etc.
    semester = Column(Integer)  # 1 for first semester, 2 for second, null for both
    department_id = Column(UUID(as_uuid=True), ForeignKey('departments.id'), nullable=False)
    exam_duration_minutes = Column(Integer, default=180)  # Default 3 hours
    is_practical = Column(Boolean, default=False)
    morning_only = Column(Boolean, default=False)  # If true, must be scheduled in morning
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    department = relationship("Department", back_populates="courses")
    registrations = relationship("CourseRegistration", back_populates="course", cascade="all, delete-orphan")
    exams = relationship("Exam", back_populates="course", cascade="all, delete-orphan")
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_course_level', 'course_level'),
        Index('idx_course_semester', 'semester'),
        Index('idx_course_department', 'department_id'),
    )
    
    def __repr__(self):
        return f"<Course(code='{self.code}', title='{self.title}', level={self.course_level})>"


class Student(Base):
    """Student model."""
    __tablename__ = 'students'
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    matric_number: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    programme_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('programmes.id'), nullable=False)
    current_level: Mapped[int] = mapped_column(Integer, nullable=False)  # 100, 200, 300, etc.
    entry_year: Mapped[int] = mapped_column(Integer, nullable=False)
    student_type: Mapped[str] = mapped_column(String, default='regular')  # regular, part-time, sandwich, etc.
    special_needs: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))  # Array of special accommodations
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    programme = relationship("Programme", back_populates="students")
    user = relationship("User", backref=backref("student_profile", uselist=False))
    registrations = relationship("CourseRegistration", back_populates="student", cascade="all, delete-orphan")
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_student_programme', 'programme_id'),
        Index('idx_student_level', 'current_level'),
        Index('idx_student_entry_year', 'entry_year'),
    )
    
    def __repr__(self):
        return f"<Student(matric='{self.matric_number}', level={self.current_level})>"


class Staff(Base):
    """Staff model for invigilators and other staff."""
    __tablename__ = 'staff'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_number = Column(String, nullable=False, unique=True, index=True)
    staff_type = Column(String, nullable=False)  # academic, administrative, technical, support
    position = Column(String)  # Professor, Lecturer, HOD, etc.
    department_id = Column(UUID(as_uuid=True), ForeignKey('departments.id'))
    can_invigilate = Column(Boolean, default=False)
    max_daily_sessions = Column(Integer, default=2)  # Maximum invigilation sessions per day
    max_consecutive_sessions = Column(Integer, default=2)  # Maximum consecutive sessions
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), unique=True)  # Optional link to user account
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    department = relationship("Department", back_populates="staff")
    user = relationship("User", backref=backref("staff_profile", uselist=False))
    invigilator_assignments = relationship("ExamInvigilator", back_populates="staff", cascade="all, delete-orphan")
    unavailability = relationship("StaffUnavailability", back_populates="staff", cascade="all, delete-orphan")
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_staff_department', 'department_id'),
        Index('idx_staff_can_invigilate', 'can_invigilate'),
        Index('idx_staff_type', 'staff_type'),
    )
    
    def __repr__(self):
        return f"<Staff(number='{self.staff_number}', type='{self.staff_type}')>"


class CourseRegistration(Base):
    """Course registration model linking students to courses per session."""
    __tablename__ = 'course_registrations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey('students.id'), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey('courses.id'), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey('academic_sessions.id'), nullable=False)
    registration_type = Column(String, default='regular')  # regular, carryover, repeat
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    student = relationship("Student", back_populates="registrations")
    course = relationship("Course", back_populates="registrations")
    academic_session = relationship("AcademicSession", back_populates="registrations")
    
    # Unique constraint to prevent duplicate registrations
    __table_args__ = (
        UniqueConstraint('student_id', 'course_id', 'session_id', name='unique_student_course_session'),
        Index('idx_registration_student', 'student_id'),
        Index('idx_registration_course', 'course_id'),
        Index('idx_registration_session', 'session_id'),
    )
    
    def __repr__(self):
        return f"<CourseRegistration(student_id='{self.student_id}', course_id='{self.course_id}')>"


class StaffUnavailability(Base):
    """Staff unavailability model for tracking when staff cannot invigilate."""
    __tablename__ = 'staff_unavailability'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_id = Column(UUID(as_uuid=True), ForeignKey('staff.id'), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey('academic_sessions.id'), nullable=False)
    unavailable_date = Column(Date, nullable=False)
    time_slot_id = Column(UUID(as_uuid=True), ForeignKey('time_slots.id'))  # Specific time slot or all day
    reason = Column(String)  # Optional reason for unavailability
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    staff = relationship("Staff", back_populates="unavailability")
    academic_session = relationship("AcademicSession", back_populates="staff_unavailability")
    time_slot = relationship("TimeSlot")
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_unavailability_staff_date', 'staff_id', 'unavailable_date'),
        Index('idx_unavailability_session', 'session_id'),
    )
    
    def __repr__(self):
        return f"<StaffUnavailability(staff_id='{self.staff_id}', date='{self.unavailable_date}')>"
