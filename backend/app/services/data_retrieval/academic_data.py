# backend/app/services/data_retrieval/academic_data.py

"""
Service for retrieving academic data from the database
"""

from typing import Dict, List, Optional, cast
from uuid import UUID
from datetime import date as ddate, datetime as ddatetime
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academic import (
    AcademicSession,
    Department,
    Faculty,
    Programme,
    Course,
    Student,
    CourseRegistration,
)


class AcademicData:
    """Service for retrieving academic-related data"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # Academic Sessions
    async def get_all_academic_sessions(self) -> List[Dict]:
        """Get all academic sessions"""
        stmt = select(AcademicSession).order_by(AcademicSession.start_date.desc())
        result = await self.session.execute(stmt)
        sessions = result.scalars().all()

        return [
            {
                "id": str(session.id),
                "name": session.name,
                "semester_system": session.semester_system,
                "start_date": (
                    cast(ddate, session.start_date).isoformat()
                    if session.start_date
                    else None
                ),
                "end_date": (
                    cast(ddate, session.end_date).isoformat()
                    if session.end_date
                    else None
                ),
                "is_active": session.is_active,
                "created_at": (
                    cast(ddatetime, session.created_at).isoformat()
                    if session.created_at
                    else None
                ),
                "updated_at": (
                    cast(ddatetime, session.updated_at).isoformat()
                    if session.updated_at
                    else None
                ),
            }
            for session in sessions
        ]

    async def get_active_academic_sessions(self) -> List[Dict]:
        """Get only active academic sessions"""
        stmt = (
            select(AcademicSession)
            .where(AcademicSession.is_active.is_(True))
            .order_by(AcademicSession.start_date.desc())
        )

        result = await self.session.execute(stmt)
        sessions = result.scalars().all()

        return [
            {
                "id": str(session.id),
                "name": session.name,
                "semester_system": session.semester_system,
                "start_date": (
                    cast(ddate, session.start_date).isoformat()
                    if session.start_date
                    else None
                ),
                "end_date": (
                    cast(ddate, session.end_date).isoformat()
                    if session.end_date
                    else None
                ),
                "is_active": session.is_active,
            }
            for session in sessions
        ]

    async def get_academic_session_by_id(self, session_id: UUID) -> Optional[Dict]:
        """Get academic session by ID"""
        stmt = select(AcademicSession).where(AcademicSession.id == session_id)
        result = await self.session.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            return None

        return {
            "id": str(session.id),
            "name": session.name,
            "semester_system": session.semester_system,
            "start_date": (
                cast(ddate, session.start_date).isoformat()
                if session.start_date
                else None
            ),
            "end_date": (
                cast(ddate, session.end_date).isoformat() if session.end_date else None
            ),
            "is_active": session.is_active,
            "created_at": (
                cast(ddatetime, session.created_at).isoformat()
                if session.created_at
                else None
            ),
            "updated_at": (
                cast(ddatetime, session.updated_at).isoformat()
                if session.updated_at
                else None
            ),
        }

    # Faculties
    async def get_all_faculties(self) -> List[Dict]:
        """Get all faculties with their departments"""
        stmt = (
            select(Faculty)
            .options(selectinload(Faculty.departments))
            .order_by(Faculty.name)
        )
        result = await self.session.execute(stmt)
        faculties = result.scalars().all()

        return [
            {
                "id": str(faculty.id),
                "code": faculty.code,
                "name": faculty.name,
                "is_active": faculty.is_active,
                "department_count": len(faculty.departments),
                "created_at": (
                    cast(ddatetime, faculty.created_at).isoformat()
                    if faculty.created_at
                    else None
                ),
            }
            for faculty in faculties
        ]

    async def get_faculty_by_id(self, faculty_id: UUID) -> Optional[Dict]:
        """Get faculty by ID with departments"""
        stmt = (
            select(Faculty)
            .options(selectinload(Faculty.departments))
            .where(Faculty.id == faculty_id)
        )
        result = await self.session.execute(stmt)
        faculty = result.scalar_one_or_none()

        if not faculty:
            return None

        return {
            "id": str(faculty.id),
            "code": faculty.code,
            "name": faculty.name,
            "is_active": faculty.is_active,
            "departments": [
                {
                    "id": str(dept.id),
                    "code": dept.code,
                    "name": dept.name,
                    "is_active": dept.is_active,
                }
                for dept in faculty.departments
            ],
            "created_at": (
                cast(ddatetime, faculty.created_at).isoformat()
                if faculty.created_at
                else None
            ),
            "updated_at": (
                cast(ddatetime, faculty.updated_at).isoformat()
                if faculty.updated_at
                else None
            ),
        }

    # Departments
    async def get_all_departments(self) -> List[Dict]:
        """Get all departments with faculty information"""
        stmt = (
            select(Department)
            .options(selectinload(Department.faculty))
            .order_by(Department.name)
        )
        result = await self.session.execute(stmt)
        departments = result.scalars().all()

        return [
            {
                "id": str(dept.id),
                "code": dept.code,
                "name": dept.name,
                "faculty_id": str(dept.faculty_id),
                "faculty_name": dept.faculty.name if dept.faculty else None,
                "faculty_code": dept.faculty.code if dept.faculty else None,
                "is_active": dept.is_active,
                "created_at": (
                    cast(ddatetime, dept.created_at).isoformat()
                    if dept.created_at
                    else None
                ),
            }
            for dept in departments
        ]

    async def get_departments_by_faculty(self, faculty_id: UUID) -> List[Dict]:
        """Get departments by faculty ID"""
        stmt = (
            select(Department)
            .options(selectinload(Department.faculty))
            .where(Department.faculty_id == faculty_id)
            .order_by(Department.name)
        )
        result = await self.session.execute(stmt)
        departments = result.scalars().all()

        return [
            {
                "id": str(dept.id),
                "code": dept.code,
                "name": dept.name,
                "faculty_id": str(dept.faculty_id),
                "is_active": dept.is_active,
            }
            for dept in departments
        ]

    # Programmes
    async def get_all_programmes(self) -> List[Dict]:
        """Get all programmes with department information"""
        stmt = (
            select(Programme)
            .options(
                selectinload(Programme.department).selectinload(Department.faculty)
            )
            .order_by(Programme.name)
        )
        result = await self.session.execute(stmt)
        programmes = result.scalars().all()

        return [
            {
                "id": str(programme.id),
                "name": programme.name,
                "code": programme.code,
                "degree_type": programme.degree_type,
                "duration_years": programme.duration_years,
                "department_id": str(programme.department_id),
                "department_name": (
                    programme.department.name if programme.department else None
                ),
                "faculty_name": (
                    programme.department.faculty.name
                    if programme.department and programme.department.faculty
                    else None
                ),
                "is_active": programme.is_active,
            }
            for programme in programmes
        ]

    async def get_programmes_by_department(self, department_id: UUID) -> List[Dict]:
        """Get programmes by department ID"""
        stmt = (
            select(Programme)
            .where(Programme.department_id == department_id)
            .order_by(Programme.name)
        )
        result = await self.session.execute(stmt)
        programmes = result.scalars().all()

        return [
            {
                "id": str(programme.id),
                "name": programme.name,
                "code": programme.code,
                "degree_type": programme.degree_type,
                "duration_years": programme.duration_years,
                "is_active": programme.is_active,
            }
            for programme in programmes
        ]

    # Courses
    async def get_all_courses(self) -> List[Dict]:
        """Get all courses with department information"""
        stmt = (
            select(Course)
            .options(selectinload(Course.department))
            .order_by(Course.code)
        )
        result = await self.session.execute(stmt)
        courses = result.scalars().all()

        return [
            {
                "id": str(course.id),
                "code": course.code,
                "title": course.title,
                "credit_units": course.credit_units,
                "course_level": course.course_level,
                "semester": course.semester,
                "is_practical": course.is_practical,
                "morning_only": course.morning_only,
                "exam_duration_minutes": course.exam_duration_minutes,
                "department_id": str(course.department_id),
                "department_name": (
                    course.department.name if course.department else None
                ),
                "is_active": course.is_active,
            }
            for course in courses
        ]

    async def get_courses_by_department(self, department_id: UUID) -> List[Dict]:
        """Get courses by department ID"""
        stmt = (
            select(Course)
            .where(Course.department_id == department_id)
            .order_by(Course.code)
        )
        result = await self.session.execute(stmt)
        courses = result.scalars().all()

        return [
            {
                "id": str(course.id),
                "code": course.code,
                "title": course.title,
                "credit_units": course.credit_units,
                "course_level": course.course_level,
                "semester": course.semester,
                "is_practical": course.is_practical,
                "morning_only": course.morning_only,
                "exam_duration_minutes": course.exam_duration_minutes,
                "is_active": course.is_active,
            }
            for course in courses
        ]

    async def get_courses_by_level(self, course_level: int) -> List[Dict]:
        """Get courses by level"""
        stmt = (
            select(Course)
            .options(selectinload(Course.department))
            .where(Course.course_level == course_level)
            .order_by(Course.code)
        )
        result = await self.session.execute(stmt)
        courses = result.scalars().all()

        return [
            {
                "id": str(course.id),
                "code": course.code,
                "title": course.title,
                "credit_units": course.credit_units,
                "course_level": course.course_level,
                "department_name": (
                    course.department.name if course.department else None
                ),
                "is_practical": course.is_practical,
                "morning_only": course.morning_only,
                "exam_duration_minutes": course.exam_duration_minutes,
            }
            for course in courses
        ]

    # Students
    async def get_all_students(self) -> List[Dict]:
        """Get all students with programme information"""
        stmt = (
            select(Student)
            .options(selectinload(Student.programme).selectinload(Programme.department))
            .order_by(Student.matric_number)
        )
        result = await self.session.execute(stmt)
        students = result.scalars().all()

        return [
            {
                "id": str(student.id),
                "matric_number": student.matric_number,
                "entry_year": student.entry_year,
                "current_level": student.current_level,
                "student_type": student.student_type,
                "special_needs": student.special_needs or [],
                "programme_id": str(student.programme_id),
                "programme_name": student.programme.name if student.programme else None,
                "department_name": (
                    student.programme.department.name
                    if student.programme and student.programme.department
                    else None
                ),
                "is_active": student.is_active,
                "created_at": (
                    cast(ddatetime, student.created_at).isoformat()
                    if student.created_at
                    else None
                ),
            }
            for student in students
        ]

    async def get_students_by_programme(self, programme_id: UUID) -> List[Dict]:
        """Get students by programme ID"""
        stmt = (
            select(Student)
            .where(Student.programme_id == programme_id)
            .order_by(Student.matric_number)
        )
        result = await self.session.execute(stmt)
        students = result.scalars().all()

        return [
            {
                "id": str(student.id),
                "matric_number": student.matric_number,
                "entry_year": student.entry_year,
                "current_level": student.current_level,
                "student_type": student.student_type,
                "special_needs": student.special_needs or [],
                "is_active": student.is_active,
            }
            for student in students
        ]

    async def get_students_by_level(self, current_level: int) -> List[Dict]:
        """Get students by current level"""
        stmt = (
            select(Student)
            .options(selectinload(Student.programme))
            .where(Student.current_level == current_level)
            .order_by(Student.matric_number)
        )
        result = await self.session.execute(stmt)
        students = result.scalars().all()

        return [
            {
                "id": str(student.id),
                "matric_number": student.matric_number,
                "entry_year": student.entry_year,
                "current_level": student.current_level,
                "programme_name": student.programme.name if student.programme else None,
                "is_active": student.is_active,
            }
            for student in students
        ]

    # Course Registrations
    async def get_registrations_for_session(self, session_id: UUID) -> List[Dict]:
        """Get all course registrations for a session"""
        stmt = (
            select(CourseRegistration)
            .options(
                selectinload(CourseRegistration.student),
                selectinload(CourseRegistration.course),
                selectinload(CourseRegistration.session),
            )
            .where(CourseRegistration.session_id == session_id)
            .order_by(CourseRegistration.registered_at.desc())
        )
        result = await self.session.execute(stmt)
        registrations = result.scalars().all()

        return [
            {
                "id": str(reg.id),
                "student_id": str(reg.student_id),
                "student_matric": reg.student.matric_number if reg.student else None,
                "course_id": str(reg.course_id),
                "course_code": reg.course.code if reg.course else None,
                "course_title": reg.course.title if reg.course else None,
                "session_id": str(reg.session_id),
                "session_name": reg.session.name if reg.session else None,
                "registration_type": reg.registration_type,
                "registered_at": (
                    cast(ddatetime, reg.registered_at).isoformat()
                    if reg.registered_at
                    else None
                ),
            }
            for reg in registrations
        ]

    async def get_student_registrations(
        self, student_id: UUID, session_id: Optional[UUID] = None
    ) -> List[Dict]:
        """Get course registrations for a specific student"""
        stmt = (
            select(CourseRegistration)
            .options(
                selectinload(CourseRegistration.course),
                selectinload(CourseRegistration.session),
            )
            .where(CourseRegistration.student_id == student_id)
        )

        if session_id:
            stmt = stmt.where(CourseRegistration.session_id == session_id)

        stmt = stmt.order_by(CourseRegistration.registered_at.desc())
        result = await self.session.execute(stmt)
        registrations = result.scalars().all()

        return [
            {
                "id": str(reg.id),
                "course_id": str(reg.course_id),
                "course_code": reg.course.code if reg.course else None,
                "course_title": reg.course.title if reg.course else None,
                "session_id": str(reg.session_id),
                "session_name": reg.session.name if reg.session else None,
                "registration_type": reg.registration_type,
                "registered_at": (
                    cast(ddatetime, reg.registered_at).isoformat()
                    if reg.registered_at
                    else None
                ),
            }
            for reg in registrations
        ]

    async def get_registration_statistics_by_session(self, session_id: UUID) -> Dict:
        """Get registration statistics for a session"""
        # Total registrations
        total_stmt = select(func.count(CourseRegistration.id)).where(
            CourseRegistration.session_id == session_id
        )
        total_result = await self.session.execute(total_stmt)
        total_registrations = total_result.scalar()

        # Unique students
        students_stmt = select(
            func.count(func.distinct(CourseRegistration.student_id))
        ).where(CourseRegistration.session_id == session_id)
        students_result = await self.session.execute(students_stmt)
        unique_students = students_result.scalar()

        # Unique courses
        courses_stmt = select(
            func.count(func.distinct(CourseRegistration.course_id))
        ).where(CourseRegistration.session_id == session_id)
        courses_result = await self.session.execute(courses_stmt)
        unique_courses = courses_result.scalar()

        # Registration by type
        type_stmt = (
            select(
                CourseRegistration.registration_type,
                func.count(CourseRegistration.id).label("count"),
            )
            .where(CourseRegistration.session_id == session_id)
            .group_by(CourseRegistration.registration_type)
        )

        type_result = await self.session.execute(type_stmt)
        registration_types = {row.registration_type: row.count for row in type_result}

        return {
            "session_id": str(session_id),
            "total_registrations": total_registrations,
            "unique_students": unique_students,
            "unique_courses": unique_courses,
            "registration_by_type": registration_types,
        }

    async def search_courses(
        self, search_term: str, department_id: Optional[UUID] = None
    ) -> List[Dict]:
        """Search courses by code or title"""
        search_pattern = f"%{search_term}%"

        stmt = (
            select(Course)
            .options(selectinload(Course.department))
            .where(
                or_(
                    Course.code.ilike(search_pattern),
                    Course.title.ilike(search_pattern),
                )
            )
        )

        if department_id:
            stmt = stmt.where(Course.department_id == department_id)

        stmt = stmt.order_by(Course.code)
        result = await self.session.execute(stmt)
        courses = result.scalars().all()

        return [
            {
                "id": str(course.id),
                "code": course.code,
                "title": course.title,
                "credit_units": course.credit_units,
                "course_level": course.course_level,
                "department_name": (
                    course.department.name if course.department else None
                ),
                "is_practical": course.is_practical,
                "morning_only": course.morning_only,
            }
            for course in courses
        ]
