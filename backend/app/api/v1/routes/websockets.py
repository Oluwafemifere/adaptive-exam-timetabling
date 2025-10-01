# app/api/v1/routes/websockets.py
from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from ....api.deps import db_session, get_current_user_for_websocket
from ....models.users import User
from ....services.notification import (
    subscribe_job,
)  # async generator that yields job updates

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/jobs/{job_id}")
async def websocket_job_updates(
    websocket: WebSocket,
    job_id: str,
    db: AsyncSession = Depends(db_session),
    # user: User = Depends(get_current_user_for_websocket), # <-- REMOVED AUTH DEPENDENCY
):
    # The user check is no longer needed as the dependency is removed.
    # if user is None:
    #     ...

    # --- DEVELOPMENT ONLY: Define a placeholder user ID ---
    # This is needed because subscribe_job expects a user ID.
    placeholder_user_id = "00000000-0000-0000-0000-000000000000"
    logger.warning(
        f"WebSocket for job {job_id} connected WITHOUT AUTHENTICATION. "
        f"Using placeholder user: {placeholder_user_id}"
    )

    await websocket.accept()
    try:
        # Use the placeholder ID for the subscription
        async for update in subscribe_job(job_id, placeholder_user_id, db):
            await websocket.send_json(update)
    except WebSocketDisconnect:
        # client disconnected normally
        logger.info(f"Client for job {job_id} disconnected.")
        return
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


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
    await websocket.accept()
    logger.info(f"DEBUG: UNSECURED WebSocket connection ACCEPTED for job {job_id}")

    try:
        # Send an initial message to confirm the connection is live
        await websocket.send_json(
            {
                "status": "connected",
                "message": "Successfully connected to the unsecured debug endpoint.",
            }
        )

        # Now, we use the subscription logic with a placeholder user.
        # Ensure your 'user_can_access_job' function is still modified to always return True.
        placeholder_user_id = "00000000-0000-0000-0000-000000000000"
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
        await websocket.close()
