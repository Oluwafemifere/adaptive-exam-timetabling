# app/api/v1/routes/websockets.py
from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, current_user
from app.models.users import User
from app.services.notification.websocket_manager import subscribe_job  # async generator that yields job updates

router = APIRouter()

@router.websocket("/jobs/{job_id}")
async def websocket_job_updates(
    websocket: WebSocket,
    job_id: str,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    await websocket.accept()
    try:
        # Convert user.id (UUID) to string to match the expected type
        async for update in subscribe_job(job_id, str(user.id), db):
            await websocket.send_json(update)
    except WebSocketDisconnect:
        # client disconnected normally
        return
    finally:
        try:
            await websocket.close()
        except Exception:
            pass