# backend/app/services/data_management/database_seeder.py
"""
Refactored database seeding service that generates data and uses the
DataUploadService to interact with the database via the seed_data_from_jsonb function.
"""

import logging
from typing import Dict, Any, List
from uuid import UUID
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from ...models import AcademicSession  # Keep model for read/check operations
from ..uploads.data_upload_service import DataUploadService
from ..System.system_service import SystemService


logger = logging.getLogger(__name__)


class DatabaseSeeder:
    """
    Generates structured data for seeding and uses the DataUploadService
    to populate the database, ensuring all business logic is handled by DB functions.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.upload_service = DataUploadService(session)
        self.seeded_counts: Dict[str, int] = {}
        self.system_service = SystemService(session)

    async def seed_for_scheduling_engine(
        self, session_id: UUID, validation_mode: bool = True
    ) -> Dict[str, Any]:
        """
        Orchestrates the seeding of a clean, consistent dataset for the scheduling engine.
        """
        try:
            logger.info(
                f"Starting scheduling engine data seeding for session {session_id}"
            )

            # Ensure the academic session exists
            await self._ensure_academic_session(session_id)

            # ... (rest of the method remains the same)
            faculties_data = self._generate_faculties()
            departments_data = self._generate_departments(faculties_data)
            programmes_data = self._generate_programmes(departments_data)
            courses_data = self._generate_courses(departments_data)
            students_data = self._generate_students(programmes_data)
            registrations_data = self._generate_registrations(
                students_data, courses_data, session_id
            )
            staff_data = self._generate_staff(departments_data)

            await self.upload_service.seed_entity_data("faculties", faculties_data)
            await self.upload_service.seed_entity_data("departments", departments_data)
            await self.upload_service.seed_entity_data("programmes", programmes_data)
            await self.upload_service.seed_entity_data("courses", courses_data)
            await self.upload_service.seed_entity_data("students", students_data)
            await self.upload_service.seed_entity_data(
                "course_registrations", registrations_data
            )
            await self.upload_service.seed_entity_data("staff", staff_data)

            logger.info(
                "Data seeding complete. Exams should be generated from registrations as a next step."
            )

            validation_result = (
                await self._validate_seeded_data(session_id)
                if validation_mode
                else {"valid": True, "issues": []}
            )

            result = {
                "success": True,
                "session_id": str(session_id),
                "validation": validation_result,
            }

            logger.info("✅ Scheduling engine seeding orchestration completed.")
            return result

        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Seeding orchestration failed: {e}", exc_info=True)
            raise

    # --- Data Generation Methods (Business logic for creating test data) ---
    # These methods now only return lists of dictionaries, not ORM objects.

    def _generate_faculties(self) -> List[Dict[str, Any]]:
        return [
            {"name": "Engineering", "code": "ENG", "is_active": True},
            {"name": "Science", "code": "SCI", "is_active": True},
        ]

    def _generate_departments(self, faculties: List[Dict]) -> List[Dict[str, Any]]:
        faculty_map = {f["code"]: f["name"] for f in faculties}
        return [
            {
                "name": "Computer Engineering",
                "code": "CPE",
                "faculty_code": "ENG",
                "is_active": True,
            },
            {
                "name": "Computer Science",
                "code": "CSC",
                "faculty_code": "SCI",
                "is_active": True,
            },
        ]

    def _generate_programmes(self, departments: List[Dict]) -> List[Dict[str, Any]]:
        return [
            {
                "name": "B.Eng Computer Engineering",
                "code": "BCPE",
                "department_code": "CPE",
                "degree_type": "undergraduate",
                "duration_years": 5,
                "is_active": True,
            },
            {
                "name": "B.Sc Computer Science",
                "code": "BCSC",
                "department_code": "CSC",
                "degree_type": "undergraduate",
                "duration_years": 4,
                "is_active": True,
            },
        ]

    def _generate_courses(self, departments: List[Dict]) -> List[Dict[str, Any]]:
        return [
            {
                "code": "CPE101",
                "title": "Introduction to Engineering",
                "credit_units": 3,
                "course_level": 100,
                "department_code": "CPE",
                "is_active": True,
            },
            {
                "code": "CSC101",
                "title": "Introduction to Computing",
                "credit_units": 3,
                "course_level": 100,
                "department_code": "CSC",
                "is_active": True,
            },
            {
                "code": "MTH101",
                "title": "Calculus I",
                "credit_units": 4,
                "course_level": 100,
                "department_code": "CSC",
                "is_active": True,
                "morning_only": True,
            },
        ]

    def _generate_students(self, programmes: List[Dict]) -> List[Dict[str, Any]]:
        students = []
        for i, prog in enumerate(programmes):
            for j in range(10):  # 10 students per programme
                students.append(
                    {
                        "matric_number": f"BU/2024/{prog['code']}/{j+1:03d}",
                        "first_name": f"StudentFirst{i}{j}",
                        "last_name": f"StudentLast{i}{j}",
                        "entry_year": 2024,
                        "programme_code": prog["code"],
                    }
                )
        return students

    def _generate_registrations(
        self, students: List[Dict], courses: List[Dict], session_id: UUID
    ) -> List[Dict[str, Any]]:
        registrations = []
        for student in students:
            # Simple logic: register for all 100-level courses
            for course in courses:
                if course["course_level"] == 100:
                    registrations.append(
                        {
                            "student_matric_number": student["matric_number"],
                            "course_code": course["code"],
                            "session_id": str(session_id),
                        }
                    )
        return registrations

    def _generate_staff(self, departments: List[Dict]) -> List[Dict[str, Any]]:
        return [
            {
                "staff_number": "CPE001",
                "first_name": "Ahmed",
                "last_name": "Ibrahim",
                "department_code": "CPE",
                "staff_type": "academic",
                "can_invigilate": True,
                "email": "ahmed.i@example.com",
            },
            {
                "staff_number": "CSC001",
                "first_name": "Khadija",
                "last_name": "Musa",
                "department_code": "CSC",
                "staff_type": "academic",
                "can_invigilate": True,
                "email": "khadija.m@example.com",
            },
        ]

    async def _ensure_academic_session(self, session_id: UUID) -> None:
        """Checks if session exists; creates if not using the DB function."""
        stmt = select(AcademicSession).where(AcademicSession.id == session_id)
        result = await self.session.execute(stmt)
        if result.scalar_one_or_none():
            logger.info(f"Using existing academic session: {session_id}")
            return

        # Use the SystemService to call the create_academic_session function
        session_name = f"Test Session {datetime.now().strftime('%Y-%m')}"
        start_date = date(2024, 9, 1)
        end_date = date(2025, 8, 31)

        # Note: timeslot_template_id would be required if not nullable. Assuming it is for seeding.
        response = await self.system_service.create_academic_session(
            p_name=session_name,
            p_start_date=start_date,
            p_end_date=end_date,
            p_timeslot_template_id=None,  # Or a valid UUID if available/required
        )
        if response.get("success"):
            logger.info(f"Created new academic session: {session_name}")
        else:
            error_msg = response.get(
                "error", "Failed to create academic session via DB function"
            )
            logger.error(error_msg)
            raise Exception(error_msg)

    async def _validate_seeded_data(self, session_id: UUID) -> Dict[str, Any]:
        """Validate the seeded data for scheduling engine compatibility (read-only checks)."""
        # This function remains largely the same as it performs read-only validation.
        # It's an acceptable use of direct SQL for verification purposes.
        issues = []
        try:
            courses_without_students_q = await self.session.execute(
                text(
                    """
                SELECT COUNT(*) FROM exam_system.courses c
                WHERE NOT EXISTS (
                    SELECT 1 FROM exam_system.course_registrations cr
                    WHERE cr.course_id = c.id AND cr.session_id = :session_id
                )"""
                ),
                {"session_id": str(session_id)},
            )
            empty_courses = courses_without_students_q.scalar()
            assert empty_courses
            if empty_courses > 0:
                issues.append(f"{empty_courses} courses have no student registrations")

            return {"valid": len(issues) == 0, "issues": issues}
        except Exception as e:
            return {"valid": False, "issues": [f"Validation error: {str(e)}"]}
