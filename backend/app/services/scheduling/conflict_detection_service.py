# backend/app/services/scheduling/conflict_detection_service.py
"""
Service for detecting conflicts in a timetable.
Delegates complex conflict validation logic to a dedicated PostgreSQL function.
"""

import logging
from typing import Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json

logger = logging.getLogger(__name__)


class ConflictDetectionService:
    """Provides an interface for timetable conflict detection using DB functions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_for_conflicts(
        self, timetable_assignments: List[Dict[str, Any]], version_id: UUID
    ) -> Dict[str, Any]:
        """
        Checks a proposed set of timetable assignments for any conflicts by calling
        the `validate_timetable` function.
        """
        logger.info(f"Checking for conflicts in timetable version {version_id}")
        try:
            query = text(
                "SELECT exam_system.validate_timetable(:p_assignments, :p_version_id)"
            )
            result = await self.session.execute(
                query,
                {
                    "p_assignments": json.dumps(timetable_assignments, default=str),
                    "p_version_id": version_id,
                },
            )
            return result.scalar_one_or_none() or {"success": False, "conflicts": []}
        except Exception as e:
            logger.error(f"Error during conflict detection: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def update_and_get_conflicts(self, version_id: UUID) -> Dict[str, Any]:
        """
        Recalculates, stores, and then returns all scheduling conflicts for a version
        by calling the `update_and_get_timetable_conflicts` function.
        """
        logger.info(f"Recalculating and retrieving conflicts for version {version_id}")
        try:
            query = text(
                "SELECT exam_system.update_and_get_timetable_conflicts(:p_version_id)"
            )
            result = await self.session.execute(query, {"p_version_id": version_id})
            return result.scalar_one_or_none() or {"success": False, "conflicts": []}
        except Exception as e:
            logger.error(f"Error updating and getting conflicts: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
