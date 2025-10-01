# backend/app/services/data_retrieval/data_retrieval_service.py

import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class DataRetrievalService:
    """
    A unified service for retrieving pre-structured data sets from the database
    by calling dedicated PostgreSQL functions. This service covers all read-only
    data aggregation functions.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _execute_pg_function(
        self, function_name: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Generic helper to execute a PostgreSQL function."""
        params = params or {}
        logger.info(f"Executing PG function '{function_name}' with params: {params}")
        try:
            # Convert dict/list params to JSON strings where necessary
            for key, value in params.items():
                if isinstance(value, (dict, list)):
                    params[key] = json.dumps(value, default=str)

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

    # --- NEWLY IMPLEMENTED METHODS ---

    async def get_entity_by_id(
        self, entity_type: str, entity_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Retrieves a single entity by its ID using a PG function."""
        return await self._execute_pg_function(
            "get_entity_by_id", {"p_entity_type": entity_type, "p_entity_id": entity_id}
        )

    async def get_paginated_entities(
        self, entity_type: str, page: int, page_size: int
    ) -> Optional[Dict[str, Any]]:
        """Retrieves a paginated list of entities using a PG function."""
        return await self._execute_pg_function(
            "get_paginated_entities",
            {"p_entity_type": entity_type, "p_page": page, "p_page_size": page_size},
        )

    async def get_timetable_results(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Retrieves timetable results JSONB by calling the get_timetable_job_results
        PostgreSQL function.
        """
        return await self._execute_pg_function(
            "get_timetable_job_results", {"p_job_id": job_id}
        )

    async def get_latest_version_metadata(
        self, session_id: Optional[UUID] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieves the ID and modification time of the latest timetable version."""
        query = text(
            """
            SELECT id, updated_at as last_modified
            FROM exam_system.timetable_jobs
            WHERE status = 'completed' AND (:session_id IS NULL OR session_id = :session_id)
            ORDER BY updated_at DESC
            LIMIT 1
            """
        )
        params = {"session_id": session_id}
        result = await self.session.execute(query, params)
        row = result.mappings().first()
        return dict(row) if row else None

    async def get_full_timetable(self, version_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Retrieves the full timetable data for a specific version.
        This now calls the new unified results function.
        """
        return await self.get_timetable_results(job_id=version_id)

    # --- ADDED METHODS ---

    # --- Authentication and Authorization ---

    async def authenticate_user(
        self, email: str, password: str
    ) -> Optional[Dict[str, Any]]:
        """Authenticates a user."""
        return await self._execute_pg_function(
            "authenticate_user", {"p_email": email, "p_password": password}
        )

    async def check_user_permission(
        self, user_id: UUID, permission: str
    ) -> Optional[bool]:
        """Checks if a user has a specific permission."""
        return await self._execute_pg_function(
            "check_user_permission", {"p_user_id": user_id, "p_permission": permission}
        )

    async def assign_role_to_user(
        self, user_id: UUID, role_name: str
    ) -> Optional[Dict[str, Any]]:
        """Assigns a role to a user."""
        return await self._execute_pg_function(
            "assign_role_to_user", {"p_user_id": user_id, "p_role_name": role_name}
        )

    async def get_user_roles(self, user_id: UUID) -> Optional[List[str]]:
        """Retrieves the roles of a user."""
        return await self._execute_pg_function("get_user_roles", {"p_user_id": user_id})

    async def register_user(
        self, user_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Registers a new user."""
        return await self._execute_pg_function(
            "register_user", {"p_user_data": user_data}
        )

    # --- Entity Management (CRUD) ---

    async def create_course(
        self, data: Dict[str, Any], user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Creates a new course."""
        return await self._execute_pg_function(
            "create_course", {"p_data": data, "p_user_id": user_id}
        )

    async def update_course(
        self, course_id: UUID, data: Dict[str, Any], user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Updates a course."""
        return await self._execute_pg_function(
            "update_course",
            {"p_course_id": course_id, "p_data": data, "p_user_id": user_id},
        )

    async def delete_course(
        self, course_id: UUID, user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Deletes a course."""
        return await self._execute_pg_function(
            "delete_course", {"p_course_id": course_id, "p_user_id": user_id}
        )

    async def create_exam(
        self, data: Dict[str, Any], user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Creates a new exam."""
        return await self._execute_pg_function(
            "create_exam", {"p_data": data, "p_user_id": user_id}
        )

    async def update_exam(
        self, exam_id: UUID, data: Dict[str, Any], user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Updates an exam."""
        return await self._execute_pg_function(
            "update_exam", {"p_exam_id": exam_id, "p_data": data, "p_user_id": user_id}
        )

    async def delete_exam(
        self, exam_id: UUID, user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Deletes an exam."""
        return await self._execute_pg_function(
            "delete_exam", {"p_exam_id": exam_id, "p_user_id": user_id}
        )

    async def create_room(
        self, data: Dict[str, Any], user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Creates a new room."""
        return await self._execute_pg_function(
            "create_room", {"p_data": data, "p_user_id": user_id}
        )

    async def update_room(
        self, room_id: UUID, data: Dict[str, Any], user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Updates a room."""
        return await self._execute_pg_function(
            "update_room", {"p_room_id": room_id, "p_data": data, "p_user_id": user_id}
        )

    async def delete_room(
        self, room_id: UUID, user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Deletes a room."""
        return await self._execute_pg_function(
            "delete_room", {"p_room_id": room_id, "p_user_id": user_id}
        )

    # --- Timetable and Scheduling Jobs ---

    async def create_timetable_job(
        self, session_id: UUID, initiated_by: UUID
    ) -> Optional[UUID]:
        """Creates a new timetable job."""
        return await self._execute_pg_function(
            "create_timetable_job",
            {"p_session_id": session_id, "p_initiated_by": initiated_by},
        )

    async def get_job_status(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        """Retrieves the status of a job."""
        return await self._execute_pg_function("get_job_status", {"p_job_id": job_id})

    async def update_job_status(
        self, job_id: UUID, status: str, set_started_at: bool = False
    ) -> None:
        """Updates the status of a job."""
        await self._execute_pg_function(
            "update_job_status",
            {
                "p_job_id": job_id,
                "p_status": status,
                "p_set_started_at": set_started_at,
            },
        )

    async def update_job_failed(self, job_id: UUID, error_message: str) -> None:
        """Updates the status of a job to failed."""
        await self._execute_pg_function(
            "update_job_failed", {"p_job_id": job_id, "p_error_message": error_message}
        )

    async def update_job_results(
        self, job_id: UUID, results_data: Dict[str, Any]
    ) -> None:
        """Updates the results of a job."""
        await self._execute_pg_function(
            "update_job_results", {"p_job_id": job_id, "p_results_data": results_data}
        )

    async def get_latest_successful_timetable_job(
        self, session_id: UUID
    ) -> Optional[UUID]:
        """Retrieves the ID of the latest successful timetable job for a session."""
        return await self._execute_pg_function(
            "get_latest_successful_timetable_job", {"p_session_id": session_id}
        )

    async def create_manual_timetable_edit(
        self,
        version_id: UUID,
        exam_id: UUID,
        edited_by: UUID,
        new_values: Dict[str, Any],
        old_values: Dict[str, Any],
        reason: str,
    ) -> Optional[Dict[str, Any]]:
        """Creates a manual edit for a timetable version."""
        return await self._execute_pg_function(
            "create_manual_timetable_edit",
            {
                "p_version_id": version_id,
                "p_exam_id": exam_id,
                "p_edited_by": edited_by,
                "p_new_values": new_values,
                "p_old_values": old_values,
                "p_reason": reason,
            },
        )

    async def validate_timetable(
        self, assignments: List[Dict[str, Any]], version_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Validates a timetable."""
        return await self._execute_pg_function(
            "validate_timetable",
            {"p_assignments": assignments, "p_version_id": version_id},
        )

    async def publish_timetable_version(self, version_id: UUID, user_id: UUID) -> None:
        """Publishes a timetable version."""
        await self._execute_pg_function(
            "publish_timetable_version",
            {"p_version_id": version_id, "p_user_id": user_id},
        )

    async def get_published_timetable_version(self, session_id: UUID) -> Optional[UUID]:
        """Retrieves the ID of the published timetable version for a session."""
        return await self._execute_pg_function(
            "get_published_timetable_version", {"p_session_id": session_id}
        )

    # --- System Configuration and Data Management ---

    async def create_or_update_system_configuration(
        self,
        user_id: UUID,
        config_name: str,
        description: str,
        is_default: bool,
        solver_parameters: Dict[str, Any],
        constraints: List[Dict[str, Any]],
        config_id: Optional[UUID] = None,
    ) -> Optional[Dict[str, Any]]:
        """Creates or updates a system configuration."""
        params = {
            "p_user_id": user_id,
            "p_config_name": config_name,
            "p_description": description,
            "p_is_default": is_default,
            "p_solver_parameters": solver_parameters,
            "p_constraints": constraints,
        }
        if config_id:
            params["p_config_id"] = config_id
        return await self._execute_pg_function(
            "create_or_update_system_configuration", params
        )

    async def get_default_system_configuration(self) -> Optional[UUID]:
        """Retrieves the ID of the default system configuration."""
        return await self._execute_pg_function("get_default_system_configuration")

    async def get_active_academic_session(self) -> Optional[Dict[str, Any]]:
        """Retrieves the active academic session."""
        return await self._execute_pg_function("get_active_academic_session")

    async def set_active_academic_session(
        self, session_id: UUID, user_id: UUID
    ) -> None:
        """Sets the active academic session."""
        await self._execute_pg_function(
            "set_active_academic_session",
            {"p_session_id": session_id, "p_user_id": user_id},
        )

    async def create_upload_session(
        self,
        user_id: UUID,
        session_id: UUID,
        upload_type: str,
        file_metadata: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Creates a new file upload session."""
        return await self._execute_pg_function(
            "create_upload_session",
            {
                "p_user_id": user_id,
                "p_session_id": session_id,
                "p_upload_type": upload_type,
                "p_file_metadata": file_metadata,
            },
        )

    async def seed_data_from_jsonb(
        self, entity_type: str, data: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Seeds data for an entity from a JSON object."""
        return await self._execute_pg_function(
            "seed_data_from_jsonb", {"p_entity_type": entity_type, "p_data": data}
        )

    # --- Reporting and Auditing ---

    async def generate_report(
        self, report_type: str, session_id: UUID, options: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generates a report."""
        return await self._execute_pg_function(
            "generate_report",
            {
                "p_report_type": report_type,
                "p_session_id": session_id,
                "p_options": options,
            },
        )

    async def log_audit_activity(
        self,
        user_id: UUID,
        action: str,
        entity_type: str,
        notes: Optional[str] = None,
        session_id: Optional[str] = None,
        entity_id: Optional[UUID] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Logs an audit activity."""
        params = {
            "p_user_id": user_id,
            "p_action": action,
            "p_entity_type": entity_type,
        }
        if notes:
            params["p_notes"] = notes
        if session_id:
            params["p_session_id"] = session_id
        if entity_id:
            params["p_entity_id"] = entity_id
        if old_values:
            params["p_old_values"] = old_values
        if new_values:
            params["p_new_values"] = new_values
        if ip_address:
            params["p_ip_address"] = ip_address
        if user_agent:
            params["p_user_agent"] = user_agent

        await self._execute_pg_function("log_audit_activity", params)

    # --- EXISTING METHODS ---

    async def get_scheduling_dataset(
        self, session_id: UUID
    ) -> Optional[Dict[str, Any]]:
        return await self._execute_pg_function(
            "get_scheduling_dataset", {"p_session_id": session_id}
        )

    async def get_student_schedule(
        self, student_id: UUID, session_id: UUID
    ) -> Optional[Dict[str, Any]]:
        return await self._execute_pg_function(
            "get_student_schedule",
            {"p_student_id": student_id, "p_session_id": session_id},
        )

    async def get_room_schedule(
        self, room_id: UUID, session_id: UUID
    ) -> Optional[Dict[str, Any]]:
        return await self._execute_pg_function(
            "get_room_schedule", {"p_room_id": room_id, "p_session_id": session_id}
        )

    async def get_invigilator_schedule(
        self, staff_id: UUID, session_id: UUID
    ) -> Optional[Dict[str, Any]]:
        return await self._execute_pg_function(
            "get_invigilator_schedule",
            {"p_staff_id": staff_id, "p_session_id": session_id},
        )

    async def get_all_entities(
        self, entity_type: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Retrieves all records for a given entity type."""
        return await self._execute_pg_function(
            "get_entity_data_as_json", {"p_entity_type": entity_type}
        )

    async def get_all_users(self) -> Optional[List[Dict[str, Any]]]:
        """Retrieves all users in the system."""
        return await self._execute_pg_function("get_all_users_json")

    async def get_active_users(self) -> Optional[List[Dict[str, Any]]]:
        """Retrieves all currently active users."""
        return await self._execute_pg_function("get_active_users_json")

    async def get_users_by_role(self, role_name: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieves users assigned to a specific role."""
        return await self._execute_pg_function(
            "get_users_by_role_json", {"p_role_name": role_name}
        )

    async def get_dashboard_kpis(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        """Retrieves Key Performance Indicators for the dashboard."""
        return await self._execute_pg_function(
            "get_dashboard_kpis", {"p_session_id": session_id}
        )

    async def get_timetable_conflicts(
        self, version_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Retrieves all identified conflicts for a timetable version."""
        # FIX: The parameter name for the PostgreSQL function was incorrect. It expects
        # 'p_version_id' to identify the timetable version, not 'p_job_id'.
        return await self._execute_pg_function(
            "get_timetable_conflicts", {"p_version_id": version_id}
        )

    async def get_users_for_notification(
        self, version_id: UUID
    ) -> Optional[List[Dict[str, Any]]]:
        """Gets a list of users who should be notified about a timetable version update."""
        return await self._execute_pg_function(
            "get_users_for_timetable_notification", {"p_version_id": version_id}
        )
