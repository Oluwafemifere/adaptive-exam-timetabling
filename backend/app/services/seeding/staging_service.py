# backend/app/services/seeding/staging_service.py

import logging
from uuid import UUID
from typing import Dict, Any, List, Optional
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class StagingService:
    """
    Provides methods to interact with the staging tables, including retrieving
    all data for a session and calling the dedicated SQL functions for
    adding, updating, and deleting individual records.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # =================================================================
    # Data Retrieval Function
    # =================================================================

    async def get_session_data(
        self, session_id: UUID
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieves all staged data for a given session ID by calling a function
        that aggregates all data into a single JSON object. This is a robust,
        atomic operation that avoids cursor-related transaction issues.

        Args:
            session_id: The UUID of the seeding session.

        Returns:
            A dictionary where keys are table names and values are lists of records.
        """
        # This single query is now the entire data-fetching logic.
        query = text("SELECT staging.get_session_data(:session_id)")
        result = await self.session.execute(query, {"session_id": session_id})

        # The function returns a single row with a single column containing the JSON object.
        # The asyncpg driver automatically decodes the JSON into a Python dict.
        session_data = result.scalar_one_or_none()

        if not session_data:
            raise RuntimeError(
                f"Could not retrieve staging data for session {session_id}."
            )

        return session_data

    # =================================================================
    # buildings Table Functions
    # =================================================================

    async def add_building(
        self, session_id: UUID, code: str, name: str, faculty_code: str
    ) -> None:
        """Calls the staging.add_building SQL function."""
        query = text(
            "SELECT staging.add_building(:session_id, :code, :name, :faculty_code)"
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "code": code,
                "name": name,
                "faculty_code": faculty_code,
            },
        )

    async def update_building(
        self, session_id: UUID, code: str, name: str, faculty_code: str
    ) -> None:
        """Calls the staging.update_building SQL function."""
        query = text(
            "SELECT staging.update_building(:session_id, :code, :name, :faculty_code)"
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "code": code,
                "name": name,
                "faculty_code": faculty_code,
            },
        )

    async def delete_building(self, session_id: UUID, code: str) -> None:
        """Calls the staging.delete_building SQL function."""
        query = text("SELECT staging.delete_building(:session_id, :code)")
        await self.session.execute(query, {"session_id": session_id, "code": code})

    # =================================================================
    # course_departments Table Functions
    # =================================================================

    async def add_course_department(
        self, session_id: UUID, course_code: str, department_code: str
    ) -> None:
        """Calls the staging.add_course_department SQL function."""
        query = text(
            "SELECT staging.add_course_department(:session_id, :course_code, :department_code)"
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "course_code": course_code,
                "department_code": department_code,
            },
        )

    async def update_course_department(
        self, session_id: UUID, course_code: str, department_code: str
    ) -> None:
        """Calls the staging.update_course_department SQL function."""
        query = text(
            "SELECT staging.update_course_department(:session_id, :course_code, :department_code)"
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "course_code": course_code,
                "department_code": department_code,
            },
        )

    async def delete_course_department(
        self, session_id: UUID, course_code: str, department_code: str
    ) -> None:
        """Calls the staging.delete_course_department SQL function."""
        query = text(
            "SELECT staging.delete_course_department(:session_id, :course_code, :department_code)"
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "course_code": course_code,
                "department_code": department_code,
            },
        )

    # =================================================================
    # course_faculties Table Functions
    # =================================================================

    async def add_course_faculty(
        self, session_id: UUID, course_code: str, faculty_code: str
    ) -> None:
        """Calls the staging.add_course_faculty SQL function."""
        query = text(
            "SELECT staging.add_course_faculty(:session_id, :course_code, :faculty_code)"
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "course_code": course_code,
                "faculty_code": faculty_code,
            },
        )

    async def update_course_faculty(
        self, session_id: UUID, course_code: str, faculty_code: str
    ) -> None:
        """Calls the staging.update_course_faculty SQL function."""
        query = text(
            "SELECT staging.update_course_faculty(:session_id, :course_code, :faculty_code)"
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "course_code": course_code,
                "faculty_code": faculty_code,
            },
        )

    async def delete_course_faculty(
        self, session_id: UUID, course_code: str, faculty_code: str
    ) -> None:
        """Calls the staging.delete_course_faculty SQL function."""
        query = text(
            "SELECT staging.delete_course_faculty(:session_id, :course_code, :faculty_code)"
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "course_code": course_code,
                "faculty_code": faculty_code,
            },
        )

    # =================================================================
    # course_instructors Table Functions
    # =================================================================

    async def add_course_instructor(
        self, session_id: UUID, staff_number: str, course_code: str
    ) -> None:
        """Calls the staging.add_course_instructor SQL function."""
        query = text(
            "SELECT staging.add_course_instructor(:session_id, :staff_number, :course_code)"
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "staff_number": staff_number,
                "course_code": course_code,
            },
        )

    async def delete_course_instructor(
        self, session_id: UUID, staff_number: str, course_code: str
    ) -> None:
        """Calls the staging.delete_course_instructor SQL function."""
        query = text(
            "SELECT staging.delete_course_instructor(:session_id, :staff_number, :course_code)"
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "staff_number": staff_number,
                "course_code": course_code,
            },
        )

    # =================================================================
    # course_registrations Table Functions
    # =================================================================

    async def add_course_registration(
        self,
        session_id: UUID,
        student_matric_number: str,
        course_code: str,
        registration_type: str = "regular",
    ) -> None:
        """Calls the staging.add_course_registration SQL function."""
        query = text(
            "SELECT staging.add_course_registration(:session_id, :student_matric_number, :course_code, :registration_type)"
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "student_matric_number": student_matric_number,
                "course_code": course_code,
                "registration_type": registration_type,
            },
        )

    async def update_course_registration(
        self,
        session_id: UUID,
        student_matric_number: str,
        course_code: str,
        registration_type: str,
    ) -> None:
        """Calls the staging.update_course_registration SQL function."""
        query = text(
            "SELECT staging.update_course_registration(:session_id, :student_matric_number, :course_code, :registration_type)"
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "student_matric_number": student_matric_number,
                "course_code": course_code,
                "registration_type": registration_type,
            },
        )

    async def delete_course_registration(
        self, session_id: UUID, student_matric_number: str, course_code: str
    ) -> None:
        """Calls the staging.delete_course_registration SQL function."""
        query = text(
            "SELECT staging.delete_course_registration(:session_id, :student_matric_number, :course_code)"
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "student_matric_number": student_matric_number,
                "course_code": course_code,
            },
        )

    # =================================================================
    # courses Table Functions
    # =================================================================

    async def add_course(
        self,
        session_id: UUID,
        code: str,
        title: str,
        credit_units: int,
        exam_duration_minutes: int,
        course_level: int,
        semester: int,
        is_practical: bool,
        morning_only: bool,
    ) -> None:
        """Calls the staging.add_course SQL function."""
        query = text(
            """
            SELECT staging.add_course(
                :session_id, :code, :title, :credit_units, :exam_duration_minutes, 
                :course_level, :semester, :is_practical, :morning_only
            )
        """
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "code": code,
                "title": title,
                "credit_units": credit_units,
                "exam_duration_minutes": exam_duration_minutes,
                "course_level": course_level,
                "semester": semester,
                "is_practical": is_practical,
                "morning_only": morning_only,
            },
        )

    async def update_course(
        self,
        session_id: UUID,
        code: str,
        title: str,
        credit_units: int,
        exam_duration_minutes: int,
        course_level: int,
        semester: int,
        is_practical: bool,
        morning_only: bool,
    ) -> None:
        """Calls the staging.update_course SQL function."""
        query = text(
            """
            SELECT staging.update_course(
                :session_id, :code, :title, :credit_units, :exam_duration_minutes, 
                :course_level, :semester, :is_practical, :morning_only
            )
        """
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "code": code,
                "title": title,
                "credit_units": credit_units,
                "exam_duration_minutes": exam_duration_minutes,
                "course_level": course_level,
                "semester": semester,
                "is_practical": is_practical,
                "morning_only": morning_only,
            },
        )

    async def delete_course(self, session_id: UUID, code: str) -> None:
        """Calls the staging.delete_course SQL function."""
        query = text("SELECT staging.delete_course(:session_id, :code)")
        await self.session.execute(query, {"session_id": session_id, "code": code})

    # =================================================================
    # departments Table Functions
    # =================================================================

    async def add_department(
        self, session_id: UUID, code: str, name: str, faculty_code: str
    ) -> None:
        """Calls the staging.add_department SQL function."""
        query = text(
            "SELECT staging.add_department(:session_id, :code, :name, :faculty_code)"
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "code": code,
                "name": name,
                "faculty_code": faculty_code,
            },
        )

    async def update_department(
        self, session_id: UUID, code: str, name: str, faculty_code: str
    ) -> None:
        """Calls the staging.update_department SQL function."""
        query = text(
            "SELECT staging.update_department(:session_id, :code, :name, :faculty_code)"
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "code": code,
                "name": name,
                "faculty_code": faculty_code,
            },
        )

    async def delete_department(self, session_id: UUID, code: str) -> None:
        """Calls the staging.delete_department SQL function."""
        query = text("SELECT staging.delete_department(:session_id, :code)")
        await self.session.execute(query, {"session_id": session_id, "code": code})

    # =================================================================
    # faculties Table Functions
    # =================================================================

    async def add_faculty(self, session_id: UUID, code: str, name: str) -> None:
        """Calls the staging.add_faculty SQL function."""
        query = text("SELECT staging.add_faculty(:session_id, :code, :name)")
        await self.session.execute(
            query, {"session_id": session_id, "code": code, "name": name}
        )

    async def update_faculty(self, session_id: UUID, code: str, name: str) -> None:
        """Calls the staging.update_faculty SQL function."""
        query = text("SELECT staging.update_faculty(:session_id, :code, :name)")
        await self.session.execute(
            query, {"session_id": session_id, "code": code, "name": name}
        )

    async def delete_faculty(self, session_id: UUID, code: str) -> None:
        """Calls the staging.delete_faculty SQL function."""
        query = text("SELECT staging.delete_faculty(:session_id, :code)")
        await self.session.execute(query, {"session_id": session_id, "code": code})

    # =================================================================
    # programmes Table Functions
    # =================================================================

    async def add_programme(
        self,
        session_id: UUID,
        code: str,
        name: str,
        department_code: str,
        degree_type: str,
        duration_years: int,
    ) -> None:
        """Calls the staging.add_programme SQL function."""
        query = text(
            """
            SELECT staging.add_programme(
                :session_id, :code, :name, :department_code, :degree_type, :duration_years
            )
        """
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "code": code,
                "name": name,
                "department_code": department_code,
                "degree_type": degree_type,
                "duration_years": duration_years,
            },
        )

    async def update_programme(
        self,
        session_id: UUID,
        code: str,
        name: str,
        department_code: str,
        degree_type: str,
        duration_years: int,
    ) -> None:
        """Calls the staging.update_programme SQL function."""
        query = text(
            """
            SELECT staging.update_programme(
                :session_id, :code, :name, :department_code, :degree_type, :duration_years
            )
        """
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "code": code,
                "name": name,
                "department_code": department_code,
                "degree_type": degree_type,
                "duration_years": duration_years,
            },
        )

    async def delete_programme(self, session_id: UUID, code: str) -> None:
        """Calls the staging.delete_programme SQL function."""
        query = text("SELECT staging.delete_programme(:session_id, :code)")
        await self.session.execute(query, {"session_id": session_id, "code": code})

    # =================================================================
    # rooms Table Functions
    # =================================================================

    async def add_room(
        self,
        session_id: UUID,
        code: str,
        name: str,
        building_code: str,
        capacity: int,
        exam_capacity: int,
        has_ac: bool,
        has_projector: bool,
        has_computers: bool,
        max_inv_per_room: int,
        room_type_code: str,
        floor_number: int,
        accessibility_features: List[str],
        notes: str,
    ) -> None:
        """Calls the staging.add_room SQL function."""
        query = text(
            """
            SELECT staging.add_room(
                :session_id, :code, :name, :building_code, :capacity, :exam_capacity,
                :has_ac, :has_projector, :has_computers, :max_inv_per_room,
                :room_type_code, :floor_number, :accessibility_features, :notes
            )
        """
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "code": code,
                "name": name,
                "building_code": building_code,
                "capacity": capacity,
                "exam_capacity": exam_capacity,
                "has_ac": has_ac,
                "has_projector": has_projector,
                "has_computers": has_computers,
                "max_inv_per_room": max_inv_per_room,
                "room_type_code": room_type_code,
                "floor_number": floor_number,
                "accessibility_features": accessibility_features,
                "notes": notes,
            },
        )

    async def update_room(
        self,
        session_id: UUID,
        code: str,
        name: str,
        building_code: str,
        capacity: int,
        exam_capacity: int,
        has_ac: bool,
        has_projector: bool,
        has_computers: bool,
        max_inv_per_room: int,
        room_type_code: str,
        floor_number: int,
        accessibility_features: List[str],
        notes: str,
    ) -> None:
        """Calls the staging.update_room SQL function."""
        query = text(
            """
            SELECT staging.update_room(
                :session_id, :code, :name, :building_code, :capacity, :exam_capacity,
                :has_ac, :has_projector, :has_computers, :max_inv_per_room,
                :room_type_code, :floor_number, :accessibility_features, :notes
            )
        """
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "code": code,
                "name": name,
                "building_code": building_code,
                "capacity": capacity,
                "exam_capacity": exam_capacity,
                "has_ac": has_ac,
                "has_projector": has_projector,
                "has_computers": has_computers,
                "max_inv_per_room": max_inv_per_room,
                "room_type_code": room_type_code,
                "floor_number": floor_number,
                "accessibility_features": accessibility_features,
                "notes": notes,
            },
        )

    async def delete_room(self, session_id: UUID, code: str) -> None:
        """Calls the staging.delete_room SQL function."""
        query = text("SELECT staging.delete_room(:session_id, :code)")
        await self.session.execute(query, {"session_id": session_id, "code": code})

    # =================================================================
    # staff Table Functions
    # =================================================================

    async def add_staff(
        self,
        session_id: UUID,
        staff_number: str,
        first_name: str,
        last_name: str,
        email: str,
        department_code: str,
        staff_type: str,
        can_invigilate: bool,
        is_instructor: bool,
        max_daily_sessions: int,
        max_consecutive_sessions: int,
        max_concurrent_exams: int,
        max_students_per_invigilator: int,
        user_email: Optional[str],
    ) -> None:
        """Calls the staging.add_staff SQL function."""
        query = text(
            """
            SELECT staging.add_staff(
                :session_id, :staff_number, :first_name, :last_name, :email, :department_code,
                :staff_type, :can_invigilate, :is_instructor, :max_daily_sessions,
                :max_consecutive_sessions, :max_concurrent_exams, :max_students_per_invigilator,
                :user_email
            )
        """
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "staff_number": staff_number,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "department_code": department_code,
                "staff_type": staff_type,
                "can_invigilate": can_invigilate,
                "is_instructor": is_instructor,
                "max_daily_sessions": max_daily_sessions,
                "max_consecutive_sessions": max_consecutive_sessions,
                "max_concurrent_exams": max_concurrent_exams,
                "max_students_per_invigilator": max_students_per_invigilator,
                "user_email": user_email,
            },
        )

    async def update_staff(
        self,
        session_id: UUID,
        staff_number: str,
        first_name: str,
        last_name: str,
        email: str,
        department_code: str,
        staff_type: str,
        can_invigilate: bool,
        is_instructor: bool,
        max_daily_sessions: int,
        max_consecutive_sessions: int,
        max_concurrent_exams: int,
        max_students_per_invigilator: int,
        user_email: Optional[str],
    ) -> None:
        """Calls the staging.update_staff SQL function."""
        query = text(
            """
            SELECT staging.update_staff(
                :session_id, :staff_number, :first_name, :last_name, :email, :department_code,
                :staff_type, :can_invigilate, :is_instructor, :max_daily_sessions,
                :max_consecutive_sessions, :max_concurrent_exams, :max_students_per_invigilator,
                :user_email
            )
        """
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "staff_number": staff_number,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "department_code": department_code,
                "staff_type": staff_type,
                "can_invigilate": can_invigilate,
                "is_instructor": is_instructor,
                "max_daily_sessions": max_daily_sessions,
                "max_consecutive_sessions": max_consecutive_sessions,
                "max_concurrent_exams": max_concurrent_exams,
                "max_students_per_invigilator": max_students_per_invigilator,
                "user_email": user_email,
            },
        )

    async def delete_staff(self, session_id: UUID, staff_number: str) -> None:
        """Calls the staging.delete_staff SQL function."""
        query = text("SELECT staging.delete_staff(:session_id, :staff_number)")
        await self.session.execute(
            query, {"session_id": session_id, "staff_number": staff_number}
        )

    # =================================================================
    # staff_unavailability Table Functions
    # =================================================================

    async def add_staff_unavailability(
        self,
        session_id: UUID,
        staff_number: str,
        unavailable_date: date,
        period_name: str,
        reason: str,
    ) -> None:
        """Calls the staging.add_staff_unavailability SQL function."""
        query = text(
            "SELECT staging.add_staff_unavailability(:session_id, :staff_number, :unavailable_date, :period_name, :reason)"
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "staff_number": staff_number,
                "unavailable_date": unavailable_date,
                "period_name": period_name,
                "reason": reason,
            },
        )

    async def update_staff_unavailability(
        self,
        session_id: UUID,
        staff_number: str,
        unavailable_date: date,
        period_name: str,
        reason: str,
    ) -> None:
        """Calls the staging.update_staff_unavailability SQL function."""
        query = text(
            "SELECT staging.update_staff_unavailability(:session_id, :staff_number, :unavailable_date, :period_name, :reason)"
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "staff_number": staff_number,
                "unavailable_date": unavailable_date,
                "period_name": period_name,
                "reason": reason,
            },
        )

    async def delete_staff_unavailability(
        self,
        session_id: UUID,
        staff_number: str,
        unavailable_date: date,
        period_name: str,
    ) -> None:
        """Calls the staging.delete_staff_unavailability SQL function."""
        query = text(
            "SELECT staging.delete_staff_unavailability(:session_id, :staff_number, :unavailable_date, :period_name)"
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "staff_number": staff_number,
                "unavailable_date": unavailable_date,
                "period_name": period_name,
            },
        )

    # =================================================================
    # students Table Functions
    # =================================================================

    async def add_student(
        self,
        session_id: UUID,
        matric_number: str,
        first_name: str,
        last_name: str,
        entry_year: int,
        programme_code: str,
        user_email: Optional[str],
    ) -> None:
        """Calls the staging.add_student SQL function."""
        query = text(
            """
            SELECT staging.add_student(
                :session_id, :matric_number, :first_name, :last_name, 
                :entry_year, :programme_code, :user_email
            )
        """
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "matric_number": matric_number,
                "first_name": first_name,
                "last_name": last_name,
                "entry_year": entry_year,
                "programme_code": programme_code,
                "user_email": user_email,
            },
        )

    async def update_student(
        self,
        session_id: UUID,
        matric_number: str,
        first_name: str,
        last_name: str,
        entry_year: int,
        programme_code: str,
        user_email: Optional[str],
    ) -> None:
        """Calls the staging.update_student SQL function."""
        query = text(
            """
            SELECT staging.update_student(
                :session_id, :matric_number, :first_name, :last_name, 
                :entry_year, :programme_code, :user_email
            )
        """
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "matric_number": matric_number,
                "first_name": first_name,
                "last_name": last_name,
                "entry_year": entry_year,
                "programme_code": programme_code,
                "user_email": user_email,
            },
        )

    async def delete_student(self, session_id: UUID, matric_number: str) -> None:
        """Calls the staging.delete_student SQL function."""
        query = text("SELECT staging.delete_student(:session_id, :matric_number)")
        await self.session.execute(
            query, {"session_id": session_id, "matric_number": matric_number}
        )
