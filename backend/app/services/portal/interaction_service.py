# backend/app/services/portal/interaction_service.py
"""
Service for handling user interactions like conflict reports, change requests,
and availability updates, primarily for student and staff portals.
"""

import logging
import json
from typing import Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class InteractionService:
    """Manages user-submitted data and actions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_student_conflict_report(
        self, user_id: UUID, exam_id: UUID, description: str
    ) -> Dict[str, Any]:
        """
        Creates a new conflict report for a student.
        Calls `create_student_conflict_report` and `create_conflict_report` DB functions.
        """
        logger.info(f"User {user_id} creating conflict report for exam {exam_id}")
        query = text(
            "SELECT exam_system.create_student_conflict_report(:p_user_id, :p_exam_id, :p_description)"
        )
        result = await self.session.execute(
            query,
            {"p_user_id": user_id, "p_exam_id": exam_id, "p_description": description},
        )
        return result.scalar_one()

    async def manage_conflict_report(
        self, admin_user_id: UUID, report_id: UUID, new_status: str, notes: str
    ) -> Dict[str, Any]:
        """
        Allows an admin to update a student's conflict report.
        Calls the `manage_conflict_report` DB function.
        """
        logger.info(
            f"Admin {admin_user_id} managing report {report_id} to status {new_status}"
        )
        query = text(
            "SELECT exam_system.manage_conflict_report(:p_admin_user_id, :p_report_id, :p_new_status, :p_notes)"
        )
        result = await self.session.execute(
            query,
            {
                "p_admin_user_id": admin_user_id,
                "p_report_id": report_id,
                "p_new_status": new_status,
                "p_notes": notes,
            },
        )
        return result.scalar_one()

    async def create_staff_assignment_change_request(
        self, user_id: UUID, assignment_id: UUID, reason: str, description: str
    ) -> Dict[str, Any]:
        """
        Creates a new invigilation assignment change request for a staff member.
        Calls `create_staff_assignment_change_request` and `create_assignment_change_request` DB functions.
        """
        logger.info(
            f"Staff (user {user_id}) creating change request for assignment {assignment_id}"
        )
        query = text(
            "SELECT exam_system.create_staff_assignment_change_request(:p_user_id, :p_assignment_id, :p_reason, :p_description)"
        )
        result = await self.session.execute(
            query,
            {
                "p_user_id": user_id,
                "p_assignment_id": assignment_id,
                "p_reason": reason,
                "p_description": description,
            },
        )
        return result.scalar_one()

    async def manage_assignment_change_request(
        self, admin_user_id: UUID, request_id: UUID, new_status: str, notes: str
    ) -> Dict[str, Any]:
        """
        Allows an admin to approve or deny a staff assignment change request.
        Calls the `manage_assignment_change_request` DB function.
        """
        logger.info(
            f"Admin {admin_user_id} managing change request {request_id} to status {new_status}"
        )
        query = text(
            "SELECT exam_system.manage_assignment_change_request(:p_admin_user_id, :p_request_id, :p_new_status, :p_notes)"
        )
        result = await self.session.execute(
            query,
            {
                "p_admin_user_id": admin_user_id,
                "p_request_id": request_id,
                "p_new_status": new_status,
                "p_notes": notes,
            },
        )
        return result.scalar_one()

    async def update_staff_availability(
        self, user_id: UUID, availability_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Updates a staff member's availability preferences.
        Calls the `update_staff_availability` DB function.
        """
        logger.info(f"User {user_id} updating their availability.")
        query = text(
            "SELECT exam_system.update_staff_availability(:p_user_id, :p_availability_data)"
        )
        result = await self.session.execute(
            query,
            {
                "p_user_id": user_id,
                "p_availability_data": json.dumps(availability_data, default=str),
            },
        )
        return result.scalar_one()
