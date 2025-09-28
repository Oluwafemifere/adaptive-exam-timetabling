# FIXED VERSION - Academic Data Service with proper student retrieval

import logging
from typing import Dict, List, Optional, cast
from uuid import UUID
from datetime import date as ddate, datetime as ddatetime
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...models.academic import (
    AcademicSession,
    Department,
    Faculty,
    Programme,
    Course,
    Student,
    CourseRegistration,
)

logger = logging.getLogger(__name__)


class AcademicData:
    """Service for retrieving academic-related data"""

    def __init__(self, session: AsyncSession):
        self.session = session
        logger.debug("AcademicData service initialized with session")

    async def get_all_academic_sessions(self) -> List[Dict]:
        """Get all academic sessions"""
        logger.info("Retrieving all academic sessions")

        try:
            stmt = select(AcademicSession).order_by(AcademicSession.start_date.desc())
            result = await self.session.execute(stmt)
            sessions = result.scalars().all()

            logger.info(f"Retrieved {len(sessions)} academic sessions")
            return [
                {
                    "id": session.id,
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
        except Exception as e:
            logger.error(
                f"Error retrieving all academic sessions: {str(e)}", exc_info=True
            )
            raise

    async def get_active_academic_sessions(self) -> List[Dict]:
        """Get only active academic sessions"""
        logger.info("Retrieving active academic sessions")

        try:
            stmt = (
                select(AcademicSession)
                .where(AcademicSession.is_active.is_(True))
                .order_by(AcademicSession.start_date.desc())
            )
            result = await self.session.execute(stmt)
            sessions = result.scalars().all()

            logger.info(f"Retrieved {len(sessions)} active academic sessions")
            return [
                {
                    "id": session.id,
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
        except Exception as e:
            logger.error(
                f"Error retrieving active academic sessions: {str(e)}", exc_info=True
            )
            raise

    async def get_students_for_session(self, session_id: UUID) -> List[Dict]:
        """FIXED - Get all active students (not limited to those with registrations in this session)

        This fixes the issue where only 42 students were retrieved instead of all eligible students.
        """
        logger.info(f"Retrieving all active students for session {session_id}")

        try:
            # Get all active students with their programme and department details
            stmt = (
                select(Student)
                .options(
                    selectinload(Student.programme)
                    .selectinload(Programme.department)
                    .selectinload(Department.faculty)
                )
                .where(Student.is_active.is_(True))
                .order_by(Student.matric_number)
            )

            result = await self.session.execute(stmt)
            students = result.scalars().all()

            logger.info(
                f"Retrieved {len(students)} active students for session {session_id}"
            )

            return [
                {
                    "id": student.id,
                    "matric_number": student.matric_number,
                    "firstname": student.first_name,
                    "lastname": student.last_name,
                    "entry_year": student.entry_year,
                    "current_level": student.current_level,
                    "student_type": student.student_type,
                    "special_needs": student.special_needs or "",
                    "programme_id": student.programme_id,
                    "programme_name": (
                        student.programme.name if student.programme else None
                    ),
                    "programme_code": (
                        student.programme.code if student.programme else None
                    ),
                    "department_id": (
                        student.programme.department.id
                        if student.programme and student.programme.department
                        else None
                    ),
                    "department_name": (
                        student.programme.department.name
                        if student.programme and student.programme.department
                        else None
                    ),
                    "faculty_name": (
                        student.programme.department.faculty.name
                        if student.programme
                        and student.programme.department
                        and student.programme.department.faculty
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
        except Exception as e:
            logger.error(
                f"Error retrieving students for session {session_id}: {str(e)}",
                exc_info=True,
            )
            raise

    async def get_students_with_registrations_for_session(
        self, session_id: UUID
    ) -> List[Dict]:
        """Alternative method: Get only students who have registrations in this session

        This was the original flawed logic - kept as alternative method.
        """
        logger.info(f"Retrieving students with registrations for session {session_id}")

        try:
            # First, get distinct student IDs who have registrations in this session
            stmt = select(func.distinct(CourseRegistration.student_id)).where(
                CourseRegistration.session_id == session_id
            )
            result = await self.session.execute(stmt)
            student_ids = [row[0] for row in result.all()]

            logger.debug(
                f"Found {len(student_ids)} students with registrations in session {session_id}"
            )

            if not student_ids:
                logger.info("No students found with registrations for this session")
                return []

            # Now get complete student information with their programme and department details
            stmt = (
                select(Student)
                .options(
                    selectinload(Student.programme)
                    .selectinload(Programme.department)
                    .selectinload(Department.faculty)
                )
                .where(Student.id.in_(student_ids))
                .order_by(Student.matric_number)
            )

            result = await self.session.execute(stmt)
            students = result.scalars().all()

            logger.info(
                f"Retrieved {len(students)} students with registrations for session {session_id}"
            )

            return [
                {
                    "id": student.id,
                    "matric_number": student.matric_number,
                    "firstname": student.first_name,
                    "lastname": student.last_name,
                    "entry_year": student.entry_year,
                    "current_level": student.current_level,
                    "student_type": student.student_type,
                    "special_needs": student.special_needs or "",
                    "programme_id": student.programme_id,
                    "programme_name": (
                        student.programme.name if student.programme else None
                    ),
                    "programme_code": (
                        student.programme.code if student.programme else None
                    ),
                    "department_id": (
                        student.programme.department.id
                        if student.programme and student.programme.department
                        else None
                    ),
                    "department_name": (
                        student.programme.department.name
                        if student.programme and student.programme.department
                        else None
                    ),
                    "faculty_name": (
                        student.programme.department.faculty.name
                        if student.programme
                        and student.programme.department
                        and student.programme.department.faculty
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
        except Exception as e:
            logger.error(
                f"Error retrieving students with registrations for session {session_id}: {str(e)}",
                exc_info=True,
            )
            raise

    async def get_academic_session_by_id(self, session_id: UUID) -> Optional[Dict]:
        """Get academic session by ID"""
        logger.info(f"Retrieving academic session by ID: {session_id}")

        try:
            stmt = select(AcademicSession).where(AcademicSession.id == session_id)
            result = await self.session.execute(stmt)
            session = result.scalar_one_or_none()

            if not session:
                logger.warning(f"Academic session with ID {session_id} not found")
                return None

            logger.debug(f"Successfully retrieved academic session: {session.name}")
            return {
                "id": session.id,
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
        except Exception as e:
            logger.error(
                f"Error retrieving academic session by ID {session_id}: {str(e)}",
                exc_info=True,
            )
            raise

    async def get_all_faculties(self) -> List[Dict]:
        """Get all faculties with their departments"""
        logger.info("Retrieving all faculties with departments")

        try:
            stmt = (
                select(Faculty)
                .options(selectinload(Faculty.departments))
                .order_by(Faculty.name)
            )
            result = await self.session.execute(stmt)
            faculties = result.scalars().all()

            logger.info(f"Retrieved {len(faculties)} faculties")
            return [
                {
                    "id": faculty.id,
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
        except Exception as e:
            logger.error(f"Error retrieving all faculties: {str(e)}", exc_info=True)
            raise

    async def get_faculty_by_id(self, faculty_id: UUID) -> Optional[Dict]:
        """Get faculty by ID with departments"""
        logger.info(f"Retrieving faculty by ID: {faculty_id}")

        try:
            stmt = (
                select(Faculty)
                .options(selectinload(Faculty.departments))
                .where(Faculty.id == faculty_id)
            )
            result = await self.session.execute(stmt)
            faculty = result.scalar_one_or_none()

            if not faculty:
                logger.warning(f"Faculty with ID {faculty_id} not found")
                return None

            logger.debug(
                f"Successfully retrieved faculty: {faculty.name} with {len(faculty.departments)} departments"
            )
            return {
                "id": faculty.id,
                "code": faculty.code,
                "name": faculty.name,
                "is_active": faculty.is_active,
                "departments": [
                    {
                        "id": dept.id,
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
        except Exception as e:
            logger.error(
                f"Error retrieving faculty by ID {faculty_id}: {str(e)}", exc_info=True
            )
            raise

    async def get_all_departments(self) -> List[Dict]:
        """Get all departments with faculty information"""
        logger.info("Retrieving all departments with faculty information")

        try:
            stmt = (
                select(Department)
                .options(selectinload(Department.faculty))
                .order_by(Department.name)
            )
            result = await self.session.execute(stmt)
            departments = result.scalars().all()

            logger.info(f"Retrieved {len(departments)} departments")
            return [
                {
                    "id": dept.id,
                    "code": dept.code,
                    "name": dept.name,
                    "faculty_id": dept.faculty_id,
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
        except Exception as e:
            logger.error(f"Error retrieving all departments: {str(e)}", exc_info=True)
            raise

    async def get_departments_by_faculty(self, faculty_id: UUID) -> List[Dict]:
        """Get departments by faculty ID"""
        logger.info(f"Retrieving departments for faculty ID: {faculty_id}")

        try:
            stmt = (
                select(Department)
                .options(selectinload(Department.faculty))
                .where(Department.faculty_id == faculty_id)
                .order_by(Department.name)
            )
            result = await self.session.execute(stmt)
            departments = result.scalars().all()

            logger.info(
                f"Retrieved {len(departments)} departments for faculty {faculty_id}"
            )
            return [
                {
                    "id": dept.id,
                    "code": dept.code,
                    "name": dept.name,
                    "faculty_id": dept.faculty_id,
                    "is_active": dept.is_active,
                }
                for dept in departments
            ]
        except Exception as e:
            logger.error(
                f"Error retrieving departments for faculty {faculty_id}: {str(e)}",
                exc_info=True,
            )
            raise

    async def get_all_programmes(self) -> List[Dict]:
        """Get all programmes with department information"""
        logger.info("Retrieving all programmes with department information")

        try:
            stmt = (
                select(Programme)
                .options(
                    selectinload(Programme.department).selectinload(Department.faculty)
                )
                .order_by(Programme.name)
            )
            result = await self.session.execute(stmt)
            programmes = result.scalars().all()

            logger.info(f"Retrieved {len(programmes)} programmes")
            return [
                {
                    "id": programme.id,
                    "name": programme.name,
                    "code": programme.code,
                    "degree_type": programme.degree_type,
                    "duration_years": programme.duration_years,
                    "department_id": programme.department_id,
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
        except Exception as e:
            logger.error(f"Error retrieving all programmes: {str(e)}", exc_info=True)
            raise

    async def get_programmes_by_department(self, department_id: UUID) -> List[Dict]:
        """Get programmes by department ID"""
        logger.info(f"Retrieving programmes for department ID: {department_id}")

        try:
            stmt = (
                select(Programme)
                .where(Programme.department_id == department_id)
                .order_by(Programme.name)
            )
            result = await self.session.execute(stmt)
            programmes = result.scalars().all()

            logger.info(
                f"Retrieved {len(programmes)} programmes for department {department_id}"
            )
            return [
                {
                    "id": programme.id,
                    "name": programme.name,
                    "code": programme.code,
                    "degree_type": programme.degree_type,
                    "duration_years": programme.duration_years,
                    "is_active": programme.is_active,
                }
                for programme in programmes
            ]
        except Exception as e:
            logger.error(
                f"Error retrieving programmes for department {department_id}: {str(e)}",
                exc_info=True,
            )
            raise

    async def get_all_courses(self) -> List[Dict]:
        """Get all courses with department information"""
        logger.info("Retrieving all courses with department information")

        try:
            stmt = (
                select(Course)
                .options(selectinload(Course.department))
                .order_by(Course.code)
            )
            result = await self.session.execute(stmt)
            courses = result.scalars().all()

            logger.info(f"Retrieved {len(courses)} courses")
            return [
                {
                    "id": course.id,
                    "code": course.code,
                    "title": course.title,
                    "credit_units": course.credit_units,
                    "course_level": course.course_level,
                    "semester": course.semester,
                    "is_practical": course.is_practical,
                    "morning_only": course.morning_only,
                    "exam_duration_minutes": course.exam_duration_minutes,
                    "department_id": course.department_id,
                    "department_name": (
                        course.department.name if course.department else None
                    ),
                    "is_active": course.is_active,
                }
                for course in courses
            ]
        except Exception as e:
            logger.error(f"Error retrieving all courses: {str(e)}", exc_info=True)
            raise

    async def get_courses_by_department(self, department_id: UUID) -> List[Dict]:
        """Get courses by department ID"""
        logger.info(f"Retrieving courses for department ID: {department_id}")

        try:
            stmt = (
                select(Course)
                .where(Course.department_id == department_id)
                .order_by(Course.code)
            )
            result = await self.session.execute(stmt)
            courses = result.scalars().all()

            logger.info(
                f"Retrieved {len(courses)} courses for department {department_id}"
            )
            return [
                {
                    "id": course.id,
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
        except Exception as e:
            logger.error(
                f"Error retrieving courses for department {department_id}: {str(e)}",
                exc_info=True,
            )
            raise

    async def get_courses_by_level(self, course_level: int) -> List[Dict]:
        """Get courses by level"""
        logger.info(f"Retrieving courses for level: {course_level}")

        try:
            stmt = (
                select(Course)
                .options(selectinload(Course.department))
                .where(Course.course_level == course_level)
                .order_by(Course.code)
            )
            result = await self.session.execute(stmt)
            courses = result.scalars().all()

            logger.info(f"Retrieved {len(courses)} courses for level {course_level}")
            return [
                {
                    "id": course.id,
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
        except Exception as e:
            logger.error(
                f"Error retrieving courses for level {course_level}: {str(e)}",
                exc_info=True,
            )
            raise

    async def get_all_students(self) -> List[Dict]:
        """Get all students with programme information"""
        logger.info("Retrieving all students with programme information")

        try:
            stmt = (
                select(Student)
                .options(
                    selectinload(Student.programme).selectinload(Programme.department)
                )
                .order_by(Student.matric_number)
            )
            result = await self.session.execute(stmt)
            students = result.scalars().all()

            logger.info(f"Retrieved {len(students)} students")
            return [
                {
                    "id": student.id,
                    "matric_number": student.matric_number,
                    "entry_year": student.entry_year,
                    "current_level": student.current_level,
                    "student_type": student.student_type,
                    "special_needs": student.special_needs or "",
                    "programme_id": student.programme_id,
                    "programme_name": (
                        student.programme.name if student.programme else None
                    ),
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
        except Exception as e:
            logger.error(f"Error retrieving all students: {str(e)}", exc_info=True)
            raise

    async def get_students_by_programme(self, programme_id: UUID) -> List[Dict]:
        """Get students by programme ID"""
        logger.info(f"Retrieving students for programme ID: {programme_id}")

        try:
            stmt = (
                select(Student)
                .where(Student.programme_id == programme_id)
                .order_by(Student.matric_number)
            )
            result = await self.session.execute(stmt)
            students = result.scalars().all()

            logger.info(
                f"Retrieved {len(students)} students for programme {programme_id}"
            )
            return [
                {
                    "id": student.id,
                    "matric_number": student.matric_number,
                    "entry_year": student.entry_year,
                    "current_level": student.current_level,
                    "student_type": student.student_type,
                    "special_needs": student.special_needs or "",
                    "is_active": student.is_active,
                }
                for student in students
            ]
        except Exception as e:
            logger.error(
                f"Error retrieving students for programme {programme_id}: {str(e)}",
                exc_info=True,
            )
            raise

    async def get_students_by_level(self, current_level: int) -> List[Dict]:
        """Get students by current level"""
        logger.info(f"Retrieving students for level: {current_level}")

        try:
            stmt = (
                select(Student)
                .options(selectinload(Student.programme))
                .where(Student.current_level == current_level)
                .order_by(Student.matric_number)
            )
            result = await self.session.execute(stmt)
            students = result.scalars().all()

            logger.info(f"Retrieved {len(students)} students for level {current_level}")
            return [
                {
                    "id": student.id,
                    "matric_number": student.matric_number,
                    "entry_year": student.entry_year,
                    "current_level": student.current_level,
                    "programme_name": (
                        student.programme.name if student.programme else None
                    ),
                    "is_active": student.is_active,
                }
                for student in students
            ]
        except Exception as e:
            logger.error(
                f"Error retrieving students for level {current_level}: {str(e)}",
                exc_info=True,
            )
            raise

    async def get_registrations_for_session(self, session_id: UUID) -> List[Dict]:
        """Get all course registrations for a session"""
        logger.info(f"Retrieving course registrations for session: {session_id}")

        try:
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

            logger.info(
                f"Retrieved {len(registrations)} course registrations for session {session_id}"
            )
            return [
                {
                    "id": reg.id,
                    "student_id": reg.student_id,
                    "student_matric": (
                        reg.student.matric_number if reg.student else None
                    ),
                    "course_id": reg.course_id,
                    "course_code": reg.course.code if reg.course else None,
                    "course_title": reg.course.title if reg.course else None,
                    "session_id": reg.session_id,
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
        except Exception as e:
            logger.error(
                f"Error retrieving registrations for session {session_id}: {str(e)}",
                exc_info=True,
            )
            raise

    async def get_student_registrations(
        self, student_id: UUID, session_id: Optional[UUID] = None
    ) -> List[Dict]:
        """Get course registrations for a specific student"""
        logger.info(
            f"Retrieving course registrations for student {student_id}, session {session_id}"
        )

        try:
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
                logger.debug(f"Filtered by session ID: {session_id}")

            stmt = stmt.order_by(CourseRegistration.registered_at.desc())

            result = await self.session.execute(stmt)
            registrations = result.scalars().all()

            logger.info(
                f"Retrieved {len(registrations)} course registrations for student {student_id}"
            )
            return [
                {
                    "id": reg.id,
                    "course_id": reg.course_id,
                    "course_code": reg.course.code if reg.course else None,
                    "course_title": reg.course.title if reg.course else None,
                    "session_id": reg.session_id,
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
        except Exception as e:
            logger.error(
                f"Error retrieving student registrations for student {student_id}: {str(e)}",
                exc_info=True,
            )
            raise

    async def get_registration_statistics_by_session(self, session_id: UUID) -> Dict:
        """Get registration statistics for a session"""
        logger.info(f"Retrieving registration statistics for session: {session_id}")

        try:
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
            registration_types = {
                row.registration_type: row.count for row in type_result
            }

            stats = {
                "session_id": session_id,
                "total_registrations": total_registrations,
                "unique_students": unique_students,
                "unique_courses": unique_courses,
                "registration_by_type": registration_types,
            }

            logger.info(
                f"Retrieved registration statistics for session {session_id}: {stats}"
            )
            return stats

        except Exception as e:
            logger.error(
                f"Error retrieving registration statistics for session {session_id}: {str(e)}",
                exc_info=True,
            )
            raise

    async def search_courses(
        self, search_term: str, department_id: Optional[UUID] = None
    ) -> List[Dict]:
        """Search courses by code or title"""
        logger.info(
            f"Searching courses with term: '{search_term}', department: {department_id}"
        )

        try:
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
                logger.debug(f"Filtered search by department ID: {department_id}")

            stmt = stmt.order_by(Course.code)

            result = await self.session.execute(stmt)
            courses = result.scalars().all()

            logger.info(
                f"Found {len(courses)} courses matching search term: '{search_term}'"
            )
            return [
                {
                    "id": course.id,
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
        except Exception as e:
            logger.error(
                f"Error searching courses with term '{search_term}': {str(e)}",
                exc_info=True,
            )
            raise
