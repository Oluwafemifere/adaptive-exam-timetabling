# backend/app/services/session_setup_service.py
"""Service for handling the multi-step exam session setup process."""

import logging
import json
from typing import Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import date, time

logger = logging.getLogger(__name__)


class SessionSetupService:
    """Orchestrates the creation and validation of a new exam session."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def setup_new_exam_session(
        self,
        user_id: UUID,
        session_name: str,
        start_date: date,
        end_date: date,
        slot_generation_mode: str,
        time_slots: List[Dict[str, time]],
    ) -> Dict[str, Any]:
        """
        Calls the `setup_new_exam_session` DB function to create the session and its custom timeslots.
        """
        logger.info(f"User {user_id} is setting up a new exam session: {session_name}")
        try:
            query = text(
                """
                SELECT exam_system.setup_new_exam_session(
                    :p_user_id, :p_session_name, :p_start_date, :p_end_date,
                    :p_slot_generation_mode, :p_time_slots
                )
                """
            )
            # The JSONB parameter needs to be a valid JSON string
            time_slots_json = json.dumps(
                [
                    {
                        "name": ts.get(
                            "name", f"Slot {i+1}"
                        ),  # Add name for robustness
                        "start_time": ts["start_time"].isoformat(),
                        "end_time": ts["end_time"].isoformat(),
                    }
                    for i, ts in enumerate(time_slots)
                ]
            )

            result = await self.session.execute(
                query,
                {
                    "p_user_id": user_id,
                    "p_session_name": session_name,
                    "p_start_date": start_date,
                    "p_end_date": end_date,
                    "p_slot_generation_mode": slot_generation_mode,
                    "p_time_slots": time_slots_json,
                },
            )
            await self.session.commit()
            return result.scalar_one()
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error setting up new exam session: {e}", exc_info=True)
            return {"success": False, "message": f"Database error: {e}"}

    async def get_session_setup_summary_and_validate(
        self, session_id: UUID
    ) -> Dict[str, Any]:
        """
        Calls the `get_session_setup_summary_and_validate` DB function to get review data.
        """
        logger.info(f"Fetching setup summary for session_id: {session_id}")
        try:
            query = text(
                "SELECT exam_system.get_session_setup_summary_and_validate(:p_session_id)"
            )
            result = await self.session.execute(query, {"p_session_id": session_id})
            return result.scalar_one()
        except Exception as e:
            logger.error(f"Error fetching session setup summary: {e}", exc_info=True)
            return {"success": False, "message": f"Database error: {e}"}

    # --- START OF THE FIX ---
    # This is the method that was missing.
    async def process_all_staged_data(self, session_id: UUID) -> Dict[str, Any]:
        """
        Calls the database function to process all staged data for a given session.
        """
        logger.info(
            f"Triggering final processing for all staged data in session {session_id}"
        )
        try:
            # This function calls all the individual process_staging_* functions in the DB
            # in the correct dependency order.
            query = text("SELECT exam_system.process_all_staged_data(:p_session_id)")

            result = await self.session.execute(query, {"p_session_id": session_id})
            await self.session.commit()

            # The DB function returns a JSONB object with a success message
            db_response = result.scalar_one()

            return db_response
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Error processing staged data for session {session_id}: {e}",
                exc_info=True,
            )
            return {
                "success": False,
                "message": f"A database error occurred during final processing: {e}",
            }

    # --- END OF THE FIX ---
