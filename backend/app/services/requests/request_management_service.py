# backend/app/services/requests/request_management_service.py
"""
Service for managing user-submitted requests like conflict reports and
assignment change requests.
"""
import logging
from typing import Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from ..data_retrieval.data_retrieval_service import DataRetrievalService

logger = logging.getLogger(__name__)


class RequestManagementService:
    """Handles creation and management of user requests via PG functions."""

    def __init__(self, session: AsyncSession):
        # Use DataRetrievalService's generic function executor
        self.retrieval_service = DataRetrievalService(session)

    async def create_student_conflict_report(
        self, user_id: UUID, exam_id: UUID, description: str
    ) -> Dict[str, Any]:
        """Creates a new conflict report submitted by a student."""
        return await self.retrieval_service._execute_pg_function(
            "create_student_conflict_report",
            {"p_user_id": user_id, "p_exam_id": exam_id, "p_description": description},
        )

    async def manage_conflict_report(
        self, admin_user_id: UUID, report_id: UUID, new_status: str, notes: str
    ) -> Dict[str, Any]:
        """Allows an administrator to update the status of a student conflict report."""
        return await self.retrieval_service._execute_pg_function(
            "manage_conflict_report",
            {
                "p_admin_user_id": admin_user_id,
                "p_report_id": report_id,
                "p_new_status": new_status,
                "p_notes": notes,
            },
        )

    async def create_staff_assignment_change_request(
        self, user_id: UUID, assignment_id: UUID, reason: str, description: str
    ) -> Dict[str, Any]:
        """Creates a new assignment change request submitted by a staff member."""
        return await self.retrieval_service._execute_pg_function(
            "create_staff_assignment_change_request",
            {
                "p_user_id": user_id,
                "p_assignment_id": assignment_id,
                "p_reason": reason,
                "p_description": description,
            },
        )

    async def manage_assignment_change_request(
        self, admin_user_id: UUID, request_id: UUID, new_status: str, notes: str
    ) -> Dict[str, Any]:
        """Allows an administrator to approve or deny a staff assignment change request."""
        return await self.retrieval_service._execute_pg_function(
            "manage_assignment_change_request",
            {
                "p_admin_user_id": admin_user_id,
                "p_request_id": request_id,
                "p_new_status": new_status,
                "p_notes": notes,
            },
        )
