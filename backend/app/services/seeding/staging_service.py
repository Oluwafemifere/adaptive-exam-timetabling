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
    Provides methods to interact with the staging tables. This service layer
    supports partial updates by fetching the existing record, merging the
    changes, and then calling the database function with the full payload.
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
        that aggregates all data into a single JSON object.
        """
        query = text("SELECT staging.get_session_data(:session_id)")
        result = await self.session.execute(query, {"session_id": session_id})
        session_data = result.scalar_one_or_none()
        if not session_data:
            raise RuntimeError(
                f"Could not retrieve staging data for session {session_id}."
            )
        return session_data

    # =================================================================
    # Private Helper for Partial Updates
    # =================================================================

    async def _get_single_record(
        self, table: str, session_id: UUID, pks: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Fetches a single record from a staging table by its primary key(s)."""
        conditions = " AND ".join([f"{key} = :{key}" for key in pks.keys()])
        query = text(
            f"SELECT * FROM staging.{table} WHERE session_id = :session_id AND {conditions}"
        )

        params = {"session_id": session_id, **pks}
        result = await self.session.execute(query, params)
        record = result.mappings().first()
        return dict(record) if record else None

    # =================================================================
    # buildings Table Functions
    # =================================================================

    async def add_building(self, session_id: UUID, **data: Any) -> None:
        query = text(
            "SELECT staging.add_building(:session_id, :code, :name, :faculty_code)"
        )
        await self.session.execute(query, {"session_id": session_id, **data})

    async def update_building(
        self, session_id: UUID, code: str, **update_data: Any
    ) -> None:
        """Performs a partial update on a staged building."""
        existing = await self._get_single_record(
            "buildings", session_id, {"code": code}
        )
        if not existing:
            raise ValueError(f"Building with code '{code}' not found.")

        merged_data = {**existing, **update_data}
        query = text(
            "SELECT staging.update_building(:session_id, :code, :name, :faculty_code)"
        )
        await self.session.execute(query, merged_data)

    async def delete_building(self, session_id: UUID, code: str) -> None:
        query = text("SELECT staging.delete_building(:session_id, :code)")
        await self.session.execute(query, {"session_id": session_id, "code": code})

    # =================================================================
    # course_departments Table Functions
    # =================================================================

    async def add_course_department(self, session_id: UUID, **data: Any) -> None:
        query = text(
            "SELECT staging.add_course_department(:session_id, :course_code, :department_code)"
        )
        await self.session.execute(query, {"session_id": session_id, **data})

    async def update_course_department(
        self,
        session_id: UUID,
        course_code: str,
        old_department_code: str,
        **update_data: Any,
    ) -> None:
        """Handles updates for the course-department link table by deleting and re-adding."""
        new_department_code = update_data.get("department_code")
        if not new_department_code:
            raise ValueError("new_department_code must be provided for the update.")

        query = text(
            "SELECT staging.update_course_department(:session_id, :course_code, :old_department_code, :new_department_code)"
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "course_code": course_code,
                "old_department_code": old_department_code,
                "new_department_code": new_department_code,
            },
        )

    async def delete_course_department(
        self, session_id: UUID, course_code: str, department_code: str
    ) -> None:
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

    async def add_course_faculty(self, session_id: UUID, **data: Any) -> None:
        query = text(
            "SELECT staging.add_course_faculty(:session_id, :course_code, :faculty_code)"
        )
        await self.session.execute(query, {"session_id": session_id, **data})

    async def update_course_faculty(
        self,
        session_id: UUID,
        course_code: str,
        old_faculty_code: str,
        **update_data: Any,
    ) -> None:
        """Handles updates for the course-faculty link table by deleting and re-adding."""
        new_faculty_code = update_data.get("faculty_code")
        if not new_faculty_code:
            raise ValueError("new_faculty_code must be provided for the update.")

        query = text(
            "SELECT staging.update_course_faculty(:session_id, :course_code, :old_faculty_code, :new_faculty_code)"
        )
        await self.session.execute(
            query,
            {
                "session_id": session_id,
                "course_code": course_code,
                "old_faculty_code": old_faculty_code,
                "new_faculty_code": new_faculty_code,
            },
        )

    async def delete_course_faculty(
        self, session_id: UUID, course_code: str, faculty_code: str
    ) -> None:
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
    async def add_course_instructor(self, session_id: UUID, **data: Any) -> None:
        query = text(
            "SELECT staging.add_course_instructor(:session_id, :staff_number, :course_code)"
        )
        await self.session.execute(query, {"session_id": session_id, **data})

    async def delete_course_instructor(
        self, session_id: UUID, staff_number: str, course_code: str
    ) -> None:
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
    async def add_course_registration(self, session_id: UUID, **data: Any) -> None:
        query = text(
            "SELECT staging.add_course_registration(:session_id, :student_matric_number, :course_code, :registration_type)"
        )
        await self.session.execute(query, {"session_id": session_id, **data})

    async def update_course_registration(
        self,
        session_id: UUID,
        student_matric_number: str,
        course_code: str,
        **update_data: Any,
    ) -> None:
        existing = await self._get_single_record(
            "course_registrations",
            session_id,
            {
                "student_matric_number": student_matric_number,
                "course_code": course_code,
            },
        )
        if not existing:
            raise ValueError(
                f"Registration for student '{student_matric_number}' in course '{course_code}' not found."
            )
        merged_data = {**existing, **update_data}
        query = text(
            "SELECT staging.update_course_registration(:session_id, :student_matric_number, :course_code, :registration_type)"
        )
        await self.session.execute(query, merged_data)

    async def delete_course_registration(
        self, session_id: UUID, student_matric_number: str, course_code: str
    ) -> None:
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
    async def add_course(self, session_id: UUID, **data: Any) -> None:
        query = text(
            "SELECT staging.add_course(:session_id, :code, :title, :credit_units, :exam_duration_minutes, :course_level, :semester, :is_practical, :morning_only)"
        )
        await self.session.execute(query, {"session_id": session_id, **data})

    async def update_course(
        self, session_id: UUID, code: str, **update_data: Any
    ) -> None:
        existing = await self._get_single_record("courses", session_id, {"code": code})
        if not existing:
            raise ValueError(f"Course with code '{code}' not found.")
        merged_data = {**existing, **update_data}
        query = text(
            "SELECT staging.update_course(:session_id, :code, :title, :credit_units, :exam_duration_minutes, :course_level, :semester, :is_practical, :morning_only)"
        )
        await self.session.execute(query, merged_data)

    async def delete_course(self, session_id: UUID, code: str) -> None:
        query = text("SELECT staging.delete_course(:session_id, :code)")
        await self.session.execute(query, {"session_id": session_id, "code": code})

    # =================================================================
    # departments Table Functions
    # =================================================================
    async def add_department(self, session_id: UUID, **data: Any) -> None:
        query = text(
            "SELECT staging.add_department(:session_id, :code, :name, :faculty_code)"
        )
        await self.session.execute(query, {"session_id": session_id, **data})

    async def update_department(
        self, session_id: UUID, code: str, **update_data: Any
    ) -> None:
        existing = await self._get_single_record(
            "departments", session_id, {"code": code}
        )
        if not existing:
            raise ValueError(f"Department with code '{code}' not found.")
        merged_data = {**existing, **update_data}
        query = text(
            "SELECT staging.update_department(:session_id, :code, :name, :faculty_code)"
        )
        await self.session.execute(query, merged_data)

    async def delete_department(self, session_id: UUID, code: str) -> None:
        query = text("SELECT staging.delete_department(:session_id, :code)")
        await self.session.execute(query, {"session_id": session_id, "code": code})

    # =================================================================
    # faculties Table Functions
    # =================================================================
    async def add_faculty(self, session_id: UUID, **data: Any) -> None:
        query = text("SELECT staging.add_faculty(:session_id, :code, :name)")
        await self.session.execute(query, {"session_id": session_id, **data})

    async def update_faculty(
        self, session_id: UUID, code: str, **update_data: Any
    ) -> None:
        existing = await self._get_single_record(
            "faculties", session_id, {"code": code}
        )
        if not existing:
            raise ValueError(f"Faculty with code '{code}' not found.")
        merged_data = {**existing, **update_data}
        query = text("SELECT staging.update_faculty(:session_id, :code, :name)")
        await self.session.execute(query, merged_data)

    async def delete_faculty(self, session_id: UUID, code: str) -> None:
        query = text("SELECT staging.delete_faculty(:session_id, :code)")
        await self.session.execute(query, {"session_id": session_id, "code": code})

    # =================================================================
    # programmes Table Functions
    # =================================================================
    async def add_programme(self, session_id: UUID, **data: Any) -> None:
        query = text(
            "SELECT staging.add_programme(:session_id, :code, :name, :department_code, :degree_type, :duration_years)"
        )
        await self.session.execute(query, {"session_id": session_id, **data})

    async def update_programme(
        self, session_id: UUID, code: str, **update_data: Any
    ) -> None:
        existing = await self._get_single_record(
            "programmes", session_id, {"code": code}
        )
        if not existing:
            raise ValueError(f"Programme with code '{code}' not found.")
        merged_data = {**existing, **update_data}
        query = text(
            "SELECT staging.update_programme(:session_id, :code, :name, :department_code, :degree_type, :duration_years)"
        )
        await self.session.execute(query, merged_data)

    async def delete_programme(self, session_id: UUID, code: str) -> None:
        query = text("SELECT staging.delete_programme(:session_id, :code)")
        await self.session.execute(query, {"session_id": session_id, "code": code})

    # =================================================================
    # rooms Table Functions
    # =================================================================
    async def add_room(self, session_id: UUID, **data: Any) -> None:
        query = text(
            "SELECT staging.add_room(:session_id, :code, :name, :building_code, :capacity, :exam_capacity, :has_ac, :has_projector, :has_computers, :max_inv_per_room, :room_type_code, :floor_number, :accessibility_features, :notes)"
        )
        await self.session.execute(query, {"session_id": session_id, **data})

    async def update_room(
        self, session_id: UUID, code: str, **update_data: Any
    ) -> None:
        existing = await self._get_single_record("rooms", session_id, {"code": code})
        if not existing:
            raise ValueError(f"Room with code '{code}' not found.")
        merged_data = {**existing, **update_data}
        query = text(
            "SELECT staging.update_room(:session_id, :code, :name, :building_code, :capacity, :exam_capacity, :has_ac, :has_projector, :has_computers, :max_inv_per_room, :room_type_code, :floor_number, :accessibility_features, :notes)"
        )
        await self.session.execute(query, merged_data)

    async def delete_room(self, session_id: UUID, code: str) -> None:
        query = text("SELECT staging.delete_room(:session_id, :code)")
        await self.session.execute(query, {"session_id": session_id, "code": code})

    # =================================================================
    # staff Table Functions
    # =================================================================
    async def add_staff(self, session_id: UUID, **data: Any) -> None:
        query = text(
            "SELECT staging.add_staff(:session_id, :staff_number, :first_name, :last_name, :email, :department_code, :staff_type, :can_invigilate, :is_instructor, :max_daily_sessions, :max_consecutive_sessions, :max_concurrent_exams, :max_students_per_invigilator, :user_email)"
        )
        await self.session.execute(query, {"session_id": session_id, **data})

    async def update_staff(
        self, session_id: UUID, staff_number: str, **update_data: Any
    ) -> None:
        existing = await self._get_single_record(
            "staff", session_id, {"staff_number": staff_number}
        )
        if not existing:
            raise ValueError(f"Staff with number '{staff_number}' not found.")
        merged_data = {**existing, **update_data}
        query = text(
            "SELECT staging.update_staff(:session_id, :staff_number, :first_name, :last_name, :email, :department_code, :staff_type, :can_invigilate, :is_instructor, :max_daily_sessions, :max_consecutive_sessions, :max_concurrent_exams, :max_students_per_invigilator, :user_email)"
        )
        await self.session.execute(query, merged_data)

    async def delete_staff(self, session_id: UUID, staff_number: str) -> None:
        query = text("SELECT staging.delete_staff(:session_id, :staff_number)")
        await self.session.execute(
            query, {"session_id": session_id, "staff_number": staff_number}
        )

    # =================================================================
    # staff_unavailability Table Functions
    # =================================================================
    async def add_staff_unavailability(self, session_id: UUID, **data: Any) -> None:
        query = text(
            "SELECT staging.add_staff_unavailability(:session_id, :staff_number, :unavailable_date, :period_name, :reason)"
        )
        await self.session.execute(query, {"session_id": session_id, **data})

    async def update_staff_unavailability(
        self,
        session_id: UUID,
        staff_number: str,
        unavailable_date: date,
        period_name: str,
        **update_data: Any,
    ) -> None:
        existing = await self._get_single_record(
            "staff_unavailability",
            session_id,
            {
                "staff_number": staff_number,
                "unavailable_date": unavailable_date,
                "period_name": period_name,
            },
        )
        if not existing:
            raise ValueError("Staff unavailability record not found.")
        merged_data = {**existing, **update_data}
        query = text(
            "SELECT staging.update_staff_unavailability(:session_id, :staff_number, :unavailable_date, :period_name, :reason)"
        )
        await self.session.execute(query, merged_data)

    async def delete_staff_unavailability(
        self,
        session_id: UUID,
        staff_number: str,
        unavailable_date: date,
        period_name: str,
    ) -> None:
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
    async def add_student(self, session_id: UUID, **data: Any) -> None:
        query = text(
            "SELECT staging.add_student(:session_id, :matric_number, :first_name, :last_name, :entry_year, :programme_code, :user_email)"
        )
        await self.session.execute(query, {"session_id": session_id, **data})

    async def update_student(
        self, session_id: UUID, matric_number: str, **update_data: Any
    ) -> None:
        existing = await self._get_single_record(
            "students", session_id, {"matric_number": matric_number}
        )
        if not existing:
            raise ValueError(f"Student with matric number '{matric_number}' not found.")
        merged_data = {**existing, **update_data}
        query = text(
            "SELECT staging.update_student(:session_id, :matric_number, :first_name, :last_name, :entry_year, :programme_code, :user_email)"
        )
        await self.session.execute(query, merged_data)

    async def delete_student(self, session_id: UUID, matric_number: str) -> None:
        query = text("SELECT staging.delete_student(:session_id, :matric_number)")
        await self.session.execute(
            query, {"session_id": session_id, "matric_number": matric_number}
        )
