# backend/app/services/data_retrieval/data_retrieval_service.py
"""
A unified service for retrieving pre-structured data sets from the database
by calling dedicated PostgreSQL functions. This service covers all read-only
data aggregation and retrieval functions.
"""

import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class DataRetrievalService:
    """A unified interface for all data retrieval PostgreSQL functions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _execute_pg_function(
        self, function_name: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Generic helper to execute a PostgreSQL data retrieval function."""
        params = params or {}
        logger.info(f"Executing PG function '{function_name}' with params: {params}")
        try:
            param_keys = ", ".join(":" + k for k in params.keys())
            query_str = (
                f"SELECT exam_system.{function_name}({param_keys})"
                if params
                else f"SELECT exam_system.{function_name}()"
            )
            query = text(query_str)
            result = await self.session.execute(query, params)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                f"Failed to execute PG function '{function_name}': {e}", exc_info=True
            )
            raise

    # --- Core Entity & List Retrieval ---
    async def get_entity_by_id(
        self, entity_type: str, entity_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Calls `get_entity_by_id`."""
        return await self._execute_pg_function(
            "get_entity_by_id", {"p_entity_type": entity_type, "p_entity_id": entity_id}
        )

    async def get_paginated_entities(
        self, entity_type: str, page: int, page_size: int
    ) -> Optional[Dict[str, Any]]:
        """Calls `get_paginated_entities`."""
        return await self._execute_pg_function(
            "get_paginated_entities",
            {"p_entity_type": entity_type, "p_page": page, "p_page_size": page_size},
        )

    async def get_all_entities_as_json(
        self, entity_type: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Calls `get_entity_data_as_json`."""
        return await self._execute_pg_function(
            "get_entity_data_as_json", {"p_entity_type": entity_type}
        )

    # --- Timetable, Scheduling & Scenario Data ---
    async def get_full_timetable(self, version_id: UUID) -> Optional[Dict[str, Any]]:
        """Calls `get_full_timetable`."""
        return await self._execute_pg_function(
            "get_full_timetable", {"p_version_id": version_id}
        )

    async def get_full_timetable_with_details(
        self, version_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Calls `get_full_timetable_with_details`."""
        return await self._execute_pg_function(
            "get_full_timetable_with_details", {"p_version_id": version_id}
        )

    async def get_timetable_conflicts(
        self, version_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Calls `get_timetable_conflicts`."""
        return await self._execute_pg_function(
            "get_timetable_conflicts", {"p_version_id": version_id}
        )

    async def get_scheduling_dataset(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        """Calls `get_scheduling_dataset` using a job_id."""
        return await self._execute_pg_function(
            "get_scheduling_dataset",
            {"p_job_id": job_id},
        )

    async def get_all_scenarios(self, page: int, page_size: int) -> Dict[str, Any]:
        """Calls `get_all_scenarios`."""
        return await self._execute_pg_function(
            "get_all_scenarios", {"p_page": page, "p_page_size": page_size}
        )

    async def get_scenarios_for_session(self, session_id: UUID) -> Dict[str, Any]:
        """Calls `get_scenarios_for_session`."""
        return await self._execute_pg_function(
            "get_scenarios_for_session", {"p_session_id": session_id}
        )

    async def get_scenario_comparison_details(
        self, scenario_ids: List[UUID]
    ) -> Dict[str, Any]:
        """Calls `get_scenario_comparison_details`."""
        return await self._execute_pg_function(
            "get_scenario_comparison_details", {"p_scenario_ids": scenario_ids}
        )

    async def get_latest_version_metadata(
        self, session_id: Optional[UUID] = None
    ) -> Optional[Dict[str, Any]]:
        """Calls `get_latest_version_metadata`."""
        params = {"p_session_id": session_id} if session_id else {}
        return await self._execute_pg_function("get_latest_version_metadata", params)

    # --- User-Specific Portal & Schedule Data ---
    async def get_portal_data(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Calls the master `get_portal_data` DB function."""
        result = await self._execute_pg_function(
            "get_portal_data", {"p_user_id": user_id}
        )
        if result is None or (isinstance(result, dict) and result.get("error")):
            return None
        return result

    async def get_student_schedule(
        self, student_id: UUID, job_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Calls `get_student_schedule` using a job_id."""
        return await self._execute_pg_function(
            "get_student_schedule",
            {"p_student_id": student_id, "p_job_id": job_id},
        )

    async def get_room_schedule(
        self, room_id: UUID, job_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Calls `get_room_schedule` using a job_id."""
        return await self._execute_pg_function(
            "get_room_schedule",
            {"p_room_id": room_id, "p_job_id": job_id},
        )

    async def get_invigilator_schedule(
        self, staff_id: UUID, job_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Calls `get_invigilator_schedule` using a job_id."""
        return await self._execute_pg_function(
            "get_invigilator_schedule",
            {"p_staff_id": staff_id, "p_job_id": job_id},
        )

    async def get_instructor_schedule(
        self, staff_id: UUID, job_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Calls `get_instructor_schedule` using a job_id."""
        return await self._execute_pg_function(
            "get_instructor_schedule",
            {"p_staff_id": staff_id, "p_job_id": job_id},
        )

    async def get_student_portal_data(
        self, user_id: UUID, session_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Calls `get_student_portal_data`."""
        return await self._execute_pg_function(
            "get_student_portal_data",
            {"p_user_id": user_id, "p_session_id": session_id},
        )

    async def get_staff_portal_data(
        self, user_id: UUID, session_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Calls `get_staff_portal_data`."""
        return await self._execute_pg_function(
            "get_staff_portal_data", {"p_user_id": user_id, "p_session_id": session_id}
        )

    async def get_student_conflict_reports(self, user_id: UUID) -> Dict[str, Any]:
        """Calls `get_student_conflict_reports`."""
        return await self._execute_pg_function(
            "get_student_conflict_reports", {"p_user_id": user_id}
        )

    async def get_staff_change_requests(self, user_id: UUID) -> Dict[str, Any]:
        """Calls `get_staff_change_requests`."""
        return await self._execute_pg_function(
            "get_staff_change_requests", {"p_user_id": user_id}
        )

    # --- User & Role Management Data ---
    async def get_all_users_json(self) -> Optional[List[Dict[str, Any]]]:
        """Calls `get_all_users_json`."""
        return await self._execute_pg_function("get_all_users_json")

    async def get_active_users_json(self) -> Optional[List[Dict[str, Any]]]:
        """Calls `get_active_users_json`."""
        return await self._execute_pg_function("get_active_users_json")

    async def get_users_by_role_json(
        self, role_name: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Calls `get_users_by_role_json`."""
        return await self._execute_pg_function(
            "get_users_by_role_json", {"p_role_name": role_name}
        )

    async def get_user_role_id(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Calls `get_user_role_id` to get the specific role ID (staff, student) for a user."""
        return await self._execute_pg_function(
            "get_user_role_id", {"p_user_id": user_id}
        )

    async def get_user_management_data(
        self,
        page: int = 1,
        page_size: int = 10,
        search_term: Optional[str] = None,
        role_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calls `get_user_management_data`."""
        return await self._execute_pg_function(
            "get_user_management_data",
            {
                "p_page": page,
                "p_page_size": page_size,
                "p_search_term": search_term,
                "p_role_filter": role_filter,
                "p_status_filter": status_filter,
            },
        )

    async def get_all_roles_with_permissions(self) -> Optional[List[Dict[str, Any]]]:
        """Calls `get_all_roles_with_permissions`."""
        return await self._execute_pg_function("get_all_roles_with_permissions")

    async def get_user_presets(
        self, user_id: UUID, preset_type: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Calls `get_user_presets`."""
        params = {"p_user_id": str(user_id)}
        if preset_type:
            params["p_preset_type"] = preset_type
        return await self._execute_pg_function("get_user_presets", params)

    # --- Dashboard, Analytics & KPI Data ---
    async def get_dashboard_kpis(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        """Calls `get_dashboard_kpis`."""
        return await self._execute_pg_function(
            "get_dashboard_kpis", {"p_session_id": session_id}
        )

    async def get_dashboard_analytics(self, session_id: UUID) -> Dict[str, Any]:
        """Calls `get_dashboard_analytics`."""
        return await self._execute_pg_function(
            "get_dashboard_analytics", {"p_session_id": session_id}
        )

    async def get_scheduling_overview(self, session_id: UUID) -> Dict[str, Any]:
        """Calls `get_scheduling_overview`."""
        return await self._execute_pg_function(
            "get_scheduling_overview", {"p_session_id": session_id}
        )

    async def get_scheduling_data_summary(self, session_id: UUID) -> Dict[str, Any]:
        """Calls `get_scheduling_data_summary`."""
        return await self._execute_pg_function(
            "get_scheduling_data_summary", {"p_session_id": session_id}
        )

    # --- System & Job Status ---
    async def get_active_academic_session(self) -> Optional[Dict[str, Any]]:
        """Calls `get_active_academic_session`."""
        return await self._execute_pg_function("get_active_academic_session")

    async def get_latest_successful_timetable_job(
        self, session_id: UUID
    ) -> Optional[UUID]:
        """Calls `get_latest_successful_timetable_job`."""
        return await self._execute_pg_function(
            "get_latest_successful_timetable_job", {"p_session_id": session_id}
        )

    async def get_published_timetable_version(self, session_id: UUID) -> Optional[UUID]:
        """Calls `get_published_timetable_version`."""
        return await self._execute_pg_function(
            "get_published_timetable_version", {"p_session_id": session_id}
        )

    async def get_timetable_job_results(self, job_id: UUID) -> Dict[str, Any]:
        """Calls `get_timetable_job_results`."""
        return await self._execute_pg_function(
            "get_timetable_job_results", {"p_job_id": job_id}
        )

    # --- History & Auditing ---
    async def get_audit_history(
        self,
        page: int,
        page_size: int,
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Calls `get_audit_history`."""
        return await self._execute_pg_function(
            "get_audit_history",
            {
                "p_page": page,
                "p_page_size": page_size,
                "p_entity_type": entity_type,
                "p_entity_id": entity_id,
            },
        )

    async def get_history_page_data(
        self, page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """Calls `get_history_page_data`."""
        return await self._execute_pg_function(
            "get_history_page_data", {"p_page": page, "p_page_size": page_size}
        )

    # --- Configuration Retrieval ---
    async def get_default_system_configuration(self) -> Optional[UUID]:
        """Calls `get_default_system_configuration`."""
        return await self._execute_pg_function("get_default_system_configuration")

    async def get_system_configuration_details(self, config_id: UUID) -> Dict[str, Any]:
        """Calls `get_system_configuration_details`."""
        return await self._execute_pg_function(
            "get_system_configuration_details", {"p_config_id": config_id}
        )

    # --- Notification & Administrative Data ---
    async def get_users_for_timetable_notification(
        self, version_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Calls `get_users_for_timetable_notification`."""
        return await self._execute_pg_function(
            "get_users_for_timetable_notification", {"p_version_id": version_id}
        )

    async def update_timetable_job_results(
        self, job_id: UUID, results_data: Dict[str, Any]
    ) -> None:
        """
        Updates the results for a specific timetable job by calling the `update_job_results` function.
        """
        logger.info(f"Updating timetable job '{job_id}' with completion data.")
        try:
            query = text(
                "SELECT exam_system.update_job_results(:p_job_id, :p_results_data)"
            )
            await self.session.execute(
                query,
                {
                    "p_job_id": job_id,
                    "p_results_data": json.dumps(results_data, default=str),
                },
            )
            await self.session.commit()
            logger.info(
                f"Successfully updated timetable job '{job_id}' via function call."
            )
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Failed to update timetable job '{job_id}': {e}", exc_info=True
            )
            raise

    async def get_admin_notifications(
        self, status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calls `get_admin_notifications`."""
        return await self._execute_pg_function(
            "get_admin_notifications", {"p_status": status}
        )
