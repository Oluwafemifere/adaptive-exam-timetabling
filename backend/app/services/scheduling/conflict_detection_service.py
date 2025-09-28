# backend/app/services/scheduling/conflict_detection_service.py
"""
Service for detecting conflicts in a timetable.
Delegates complex conflict validation logic to a dedicated PostgreSQL function.
"""

import logging
from typing import Dict, Any, List
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import json

logger = logging.getLogger(__name__)


class ConflictDetectionService:
    """Provides an interface for timetable conflict detection."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_for_conflicts(
        self, timetable_assignments: List[Dict[str, Any]], version_id: UUID
    ) -> Dict[str, Any]:
        """
        Checks a proposed set of timetable assignments for any conflicts.

        Args:
            timetable_assignments: A list of assignment dictionaries, each containing
                                   exam_id, room_id, exam_date, time_slot_period, etc.
            version_id: The ID of the timetable version these assignments belong to.

        Returns:
            A dictionary containing a list of identified conflicts.
        """
        try:
            logger.info(f"Checking for conflicts in timetable version {version_id}")
            assignments_json = json.dumps(timetable_assignments, default=str)

            query = text(
                """
                SELECT exam_system.validate_timetable(
                    p_assignments => :assignments,
                    p_version_id => :version_id
                )
                """
            )
            result = await self.session.execute(
                query, {"assignments": assignments_json, "version_id": version_id}
            )

            conflict_result = result.scalar_one_or_none()

            if conflict_result:
                logger.info(
                    f"Found {len(conflict_result.get('conflicts', []))} conflicts for version {version_id}"
                )
                return conflict_result
            else:
                logger.warning(
                    f"Conflict check for version {version_id} returned no result."
                )
                return {
                    "success": False,
                    "conflicts": [
                        {"type": "system", "message": "Conflict check failed to run."}
                    ],
                }

        except Exception as e:
            logger.error(
                f"Error during conflict detection for version {version_id}: {e}",
                exc_info=True,
            )
            return {
                "success": False,
                "conflicts": [
                    {"type": "system", "message": f"An internal error occurred: {e}"}
                ],
            }
