# backend/app/api/v1/routes/websockets.py
from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from ....api.deps import db_session, get_current_user_for_websocket
from ....models.users import User
from ....services.notification import (
    subscribe_job,
    connection_manager,  # --- FIX: Import the connection_manager ---
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/jobs/{job_id}")
async def websocket_job_updates(
    websocket: WebSocket,
    job_id: str,
    db: AsyncSession = Depends(db_session),
    # user: User = Depends(get_current_user_for_websocket), # <-- REMOVED AUTH DEPENDENCY
):
    placeholder_user_id = "00000000-0000-0000-0000-000000000000"
    logger.warning(
        f"WebSocket for job {job_id} connected WITHOUT AUTHENTICATION. "
        f"Using placeholder user: {placeholder_user_id}"
    )

    # --- FIX: Register the connection using the manager ---
    await connection_manager.connect_job_updates(websocket, job_id, placeholder_user_id)

    try:
        # The user check is no longer needed as the dependency is removed.
        async for update in subscribe_job(job_id, placeholder_user_id, db):
            await websocket.send_json(update)
    except WebSocketDisconnect:
        # client disconnected normally
        logger.info(f"Client for job {job_id} disconnected.")
    finally:
        # --- FIX: Use the manager to disconnect and clean up ---
        await connection_manager.disconnect(websocket)


@router.websocket("/jobs/{job_id}/debug")
async def websocket_job_updates_debug(
    websocket: WebSocket,
    job_id: str,
    db: AsyncSession = Depends(db_session),
):
    """
    A completely unsecured WebSocket endpoint for debugging.
    This has NO user authentication.
    """
    logger.info(f"DEBUG: Attempting to connect to UNSECURED endpoint for job {job_id}")

    placeholder_user_id = "00000000-0000-0000-0000-000000000000"

    # --- FIX: Register the connection with the ConnectionManager ---
    await connection_manager.connect_job_updates(websocket, job_id, placeholder_user_id)
    logger.info(f"DEBUG: UNSECURED WebSocket connection ACCEPTED for job {job_id}")

    try:
        # Send an initial message to confirm the connection is live
        await websocket.send_json(
            {
                "status": "connected",
                "message": "Successfully connected to the unsecured debug endpoint.",
            }
        )

        logger.warning(
            f"DEBUG: Starting job subscription for {job_id} with placeholder user."
        )

        async for update in subscribe_job(job_id, placeholder_user_id, db):
            await websocket.send_json(update)

    except WebSocketDisconnect:
        logger.info(
            f"DEBUG: Client for job {job_id} disconnected from unsecured endpoint."
        )
    except Exception as e:
        logger.error(
            f"DEBUG: Error in unsecured websocket for job {job_id}: {e}", exc_info=True
        )
    finally:
        logger.info(f"DEBUG: Closing unsecured connection for job {job_id}")
        # --- FIX: Use the manager to disconnect and clean up ---
        await connection_manager.disconnect(websocket)
