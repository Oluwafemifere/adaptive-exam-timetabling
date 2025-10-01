# backend/app/services/scheduling/timetable_management_service.py

"""
Service for managing timetable versions, manual edits, and validation.
"""
import logging
import json
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class TimetableManagementService:
    """Handles operations related to timetable versions and modifications."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_manual_edit(
        self,
        version_id: UUID,
        exam_id: UUID,
        edited_by: UUID,
        new_values: Dict[str, Any],
        old_values: Dict[str, Any],
        reason: str,
    ) -> Dict[str, Any]:
        """
        Records a manual edit made to a timetable version.

        Args:
            version_id: The ID of the timetable version being edited.
            exam_id: The ID of the exam being moved or changed.
            edited_by: The ID of the user making the change.
            new_values: A JSON object describing the new state (e.g., new room/time).
            old_values: A JSON object describing the original state.
            reason: The justification for the manual edit.

        Returns:
            The result of the operation from the database.
        """
        logger.info(
            f"User {edited_by} is manually editing exam {exam_id} in version {version_id}"
        )
        try:
            query = text(
                """
                SELECT exam_system.create_manual_timetable_edit(
                    :p_version_id, :p_exam_id, :p_edited_by,
                    :p_new_values, :p_old_values, :p_reason
                )
                """
            )
            result = await self.session.execute(
                query,
                {
                    "p_version_id": version_id,
                    "p_exam_id": exam_id,
                    "p_edited_by": edited_by,
                    "p_new_values": json.dumps(new_values, default=str),
                    "p_old_values": json.dumps(old_values, default=str),
                    "p_reason": reason,
                },
            )
            edit_result = result.scalar_one()
            await self.session.commit()
            return edit_result
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating manual timetable edit: {e}", exc_info=True)
            return {"success": False, "error": "Failed to record manual edit."}

    async def validate_assignments(
        self, assignments: List[Dict[str, Any]], version_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Validates a set of timetable assignments against constraint rules.
        """
        logger.info(f"Validating assignments for timetable version {version_id}")
        query = text(
            "SELECT exam_system.validate_timetable(:p_assignments, :p_version_id)"
        )
        result = await self.session.execute(
            query,
            {
                "p_assignments": json.dumps(assignments, default=str),
                "p_version_id": version_id,
            },
        )
        return result.scalar_one_or_none()
