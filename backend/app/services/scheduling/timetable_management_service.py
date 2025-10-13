# backend/app/services/scheduling/timetable_management_service.py
"""
Service for managing timetable versions, scenarios, manual edits, and publication.
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
        Records a manual edit by calling `create_manual_timetable_edit`.
        """
        logger.info(f"User {edited_by} editing exam {exam_id} in version {version_id}")
        query = text(
            "SELECT exam_system.create_manual_timetable_edit(:p_version_id, :p_exam_id, :p_edited_by, :p_new_values, :p_old_values, :p_reason)"
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
        return result.scalar_one()

    async def create_scenario_from_version(
        self,
        parent_version_id: UUID,
        scenario_name: str,
        scenario_description: Optional[str],
        user_id: UUID,
    ) -> Optional[UUID]:
        """
        Creates a new scenario by calling `create_scenario_from_version`.
        """
        logger.info(
            f"User {user_id} creating scenario '{scenario_name}' from version {parent_version_id}"
        )
        query = text(
            "SELECT exam_system.create_scenario_from_version(:p_parent_version_id, :p_scenario_name, :p_scenario_description, :p_created_by_user_id)"
        )
        result = await self.session.execute(
            query,
            {
                "p_parent_version_id": parent_version_id,
                "p_scenario_name": scenario_name,
                "p_scenario_description": scenario_description,
                "p_created_by_user_id": user_id,
            },
        )
        return result.scalar_one_or_none()

    async def delete_scenario(self, scenario_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """
        Deletes a scenario by calling `delete_scenario`.
        """
        logger.info(f"User {user_id} deleting scenario {scenario_id}")
        query = text("SELECT exam_system.delete_scenario(:p_scenario_id, :p_user_id)")
        result = await self.session.execute(
            query, {"p_scenario_id": scenario_id, "p_user_id": user_id}
        )
        return result.scalar_one()

    async def compare_scenarios(
        self, scenario_id_1: UUID, scenario_id_2: UUID
    ) -> Dict[str, Any]:
        """
        Compares two scenarios by calling the compare_scenarios database function.
        """
        logger.info(f"Comparing scenarios {scenario_id_1} and {scenario_id_2}")
        query = text(
            "SELECT exam_system.compare_scenarios(:p_scenario_id_1, :p_scenario_id_2)"
        )
        result = await self.session.execute(
            query,
            {"p_scenario_id_1": scenario_id_1, "p_scenario_id_2": scenario_id_2},
        )
        return result.scalar_one()

    async def validate_assignments(
        self, version_id: UUID, assignments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validates proposed timetable assignments by calling `validate_timetable`.
        Checks for student clashes, room overcapacity, double bookings, and invigilator conflicts.
        """
        logger.info(f"Validating timetable for version {version_id}")
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
        return result.scalar_one()

    async def publish_timetable_version(
        self, job_id: UUID, user_id: UUID
    ) -> Dict[str, Any]:
        """
        Publishes a timetable version, making it official, by calling `publish_timetable_version`.
        """
        logger.info(f"User {user_id} publishing timetable from job {job_id}")
        try:
            query = text(
                "SELECT exam_system.publish_timetable_version(:p_job_id, :p_user_id)"
            )
            result = await self.session.execute(
                query, {"p_job_id": job_id, "p_user_id": user_id}
            )
            publish_result = result.scalar_one()
            await self.session.commit()
            logger.info(f"Successfully published timetable from job {job_id}")
            return publish_result
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to publish from job {job_id}: {e}", exc_info=True)
            raise

    async def unpublish_timetable_version(
        self, version_id: UUID, user_id: UUID
    ) -> Dict[str, Any]:
        """
        Unpublishes a specific timetable version. Assumes a corresponding PG function exists.
        """
        logger.warning(f"User {user_id} un-publishing timetable version {version_id}")
        try:
            # This assumes a new PG function 'unpublish_timetable_version' exists
            # that sets is_published to false for a given version_id.
            query = text(
                "UPDATE exam_system.timetable_versions SET is_published = FALSE WHERE id = :p_version_id"
            )
            await self.session.execute(query, {"p_version_id": version_id})
            await self.session.commit()
            logger.info(f"Successfully unpublished timetable version {version_id}")
            return {"success": True, "message": "Timetable version unpublished."}
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Failed to unpublish version {version_id}: {e}", exc_info=True
            )
            raise
