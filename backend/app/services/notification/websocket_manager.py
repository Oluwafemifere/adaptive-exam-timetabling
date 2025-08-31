# backend/app/services/notification/websocket_manager.py

"""
WebSocket manager for real-time updates with proper error handling,
authentication, and connection management.
"""

import json
import logging
from typing import Dict, Set, Any, AsyncGenerator, Optional, Union
from uuid import UUID
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self) -> None:
        # Active connections by job_id -> set of websockets
        self.job_connections: Dict[str, Set[WebSocket]] = {}
        # User connections by user_id -> set of websockets
        self.user_connections: Dict[str, Set[WebSocket]] = {}
        # Connection metadata
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        self._redis: Optional[Any] = None

    async def get_redis(self) -> Optional[Any]:
        """Get Redis connection if available"""
        if self._redis is None:
            try:
                from app.core.config import settings

                if hasattr(settings, "REDIS_URL") and settings.REDIS_URL:
                    from redis.asyncio import Redis

                    self._redis = Redis.from_url(
                        settings.REDIS_URL, encoding="utf-8", decode_responses=True
                    )
                    # Test connection
                    await self._redis.ping()
                else:
                    logger.warning("Redis URL not configured")
                    return None
            except Exception as e:
                logger.warning(f"Redis not available: {e}")
                return None
        return self._redis

    async def connect_job_updates(
        self, websocket: WebSocket, job_id: str, user_id: str
    ) -> None:
        """Connect client to job updates."""
        try:
            await websocket.accept()

            # Add to job connections
            if job_id not in self.job_connections:
                self.job_connections[job_id] = set()
            self.job_connections[job_id].add(websocket)

            # Add to user connections
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(websocket)

            # Store metadata
            self.connection_metadata[websocket] = {
                "job_id": job_id,
                "user_id": user_id,
                "connected_at": datetime.now(timezone.utc),
                "type": "job_updates",
            }

            logger.info(f"WebSocket connected for job {job_id}, user {user_id}")

        except Exception as e:
            logger.error(f"Failed to connect WebSocket: {e}")
            try:
                await websocket.close()
            except Exception:
                pass

    async def disconnect(self, websocket: WebSocket) -> None:
        """Disconnect client and cleanup."""
        try:
            metadata = self.connection_metadata.get(websocket, {})
            job_id = metadata.get("job_id")
            user_id = metadata.get("user_id")

            # Remove from job connections
            if job_id and job_id in self.job_connections:
                self.job_connections[job_id].discard(websocket)
                if not self.job_connections[job_id]:
                    del self.job_connections[job_id]

            # Remove from user connections
            if user_id and user_id in self.user_connections:
                self.user_connections[user_id].discard(websocket)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]

            # Remove metadata
            if websocket in self.connection_metadata:
                del self.connection_metadata[websocket]

            logger.info(f"WebSocket disconnected for job {job_id}, user {user_id}")

        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")

    async def send_job_update(self, job_id: str, message: Dict[str, Any]) -> None:
        """Send update to all connections watching a job."""
        if job_id not in self.job_connections:
            return

        # Prepare message
        message_data = {
            "type": "job_update",
            "job_id": job_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **message,
        }

        message_json = json.dumps(message_data, default=str)
        disconnected = set()

        # Send to all connected clients
        for websocket in self.job_connections[job_id].copy():
            try:
                await websocket.send_text(message_json)
            except WebSocketDisconnect:
                disconnected.add(websocket)
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket: {e}")
                disconnected.add(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            await self.disconnect(websocket)

    async def send_user_notification(
        self, user_id: str, notification: Dict[str, Any]
    ) -> None:
        """Send notification to all connections for a user."""
        if user_id not in self.user_connections:
            return

        message_data = {
            "type": "notification",
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **notification,
        }

        message_json = json.dumps(message_data, default=str)
        disconnected = set()

        for websocket in self.user_connections[user_id].copy():
            try:
                await websocket.send_text(message_json)
            except WebSocketDisconnect:
                disconnected.add(websocket)
            except Exception as e:
                logger.warning(f"Failed to send notification to WebSocket: {e}")
                disconnected.add(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            await self.disconnect(websocket)

    async def broadcast_system_message(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connected clients."""
        message_data = {
            "type": "system_message",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **message,
        }

        message_json = json.dumps(message_data, default=str)
        all_connections = set()

        # Collect all connections
        for connections in self.job_connections.values():
            all_connections.update(connections)
        for connections in self.user_connections.values():
            all_connections.update(connections)

        disconnected = set()
        for websocket in all_connections:
            try:
                await websocket.send_text(message_json)
            except WebSocketDisconnect:
                disconnected.add(websocket)
            except Exception as e:
                logger.warning(f"Failed to broadcast message: {e}")
                disconnected.add(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            await self.disconnect(websocket)

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        total_job_connections = sum(
            len(conns) for conns in self.job_connections.values()
        )
        total_user_connections = sum(
            len(conns) for conns in self.user_connections.values()
        )

        return {
            "total_job_connections": total_job_connections,
            "total_user_connections": total_user_connections,
            "job_subscriptions": len(self.job_connections),
            "user_subscriptions": len(self.user_connections),
            "active_jobs": list(self.job_connections.keys()),
            "connected_users": list(self.user_connections.keys()),
        }


# Global connection manager instance
connection_manager = ConnectionManager()


async def subscribe_job(
    job_id: str, user_id: str, db: AsyncSession
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Subscribe to job updates via Redis pub/sub or in-memory.
    This is used by the WebSocket endpoint.
    """
    redis = await connection_manager.get_redis()
    channel_name = f"job_updates_{job_id}"
    pubsub = None

    try:
        # Send initial job status
        initial_status = await get_initial_job_status(job_id, db)
        if initial_status:
            yield initial_status

        if redis:
            # Use Redis pub/sub if available
            pubsub = redis.pubsub()
            await pubsub.subscribe(channel_name)

            # Listen for updates
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        # Validate user can access this job
                        if await user_can_access_job(user_id, job_id, db):
                            yield data
                        else:
                            logger.warning(
                                f"User {user_id} denied access to job {job_id}"
                            )
                            break
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in Redis message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing job update: {e}")
        else:
            # Fallback: poll for updates (simplified)
            import asyncio

            while True:
                await asyncio.sleep(5)  # Poll every 5 seconds
                status = await get_initial_job_status(job_id, db)
                if status:
                    yield status

    except Exception as e:
        logger.error(f"Error in job subscription for {job_id}: {e}")
    finally:
        if pubsub is not None:
            try:
                await pubsub.unsubscribe(channel_name)
                await pubsub.close()
            except Exception as e:
                logger.error(f"Error closing Redis pubsub: {e}")


async def publish_job_update(job_id: str, update_data: Dict[str, Any]) -> None:
    """
    Publish job update to WebSocket clients and Redis if available.
    """
    try:
        logger.info(
            f"Job {job_id} update: "
            f"status={update_data.get('status', 'N/A')}, "
            f"progress={update_data.get('progress', 0)}%, "
            f"phase={update_data.get('phase', 'N/A')}, "
            f"message={update_data.get('message', 'N/A')}"
        )

        # Send via WebSocket manager
        await connection_manager.send_job_update(job_id, update_data)

        # Send via Redis if available
        redis = await connection_manager.get_redis()
        if redis:
            channel_name = f"job_updates_{job_id}"
            message = json.dumps(update_data, default=str)
            await redis.publish(channel_name, message)

    except Exception as e:
        logger.error(f"Failed to publish job update for {job_id}: {e}")


async def get_initial_job_status(
    job_id: str, db: AsyncSession
) -> Optional[Dict[str, Any]]:
    """Get initial job status for new WebSocket connections."""
    try:
        from app.models import TimetableJob

        job_uuid = UUID(job_id)
        query = select(TimetableJob).where(TimetableJob.id == job_uuid)
        result = await db.execute(query)
        job = result.scalar_one_or_none()

        if not job:
            return None

        # Convert datetime objects to ISO format strings safely
        def safe_isoformat(dt: Any) -> Optional[str]:
            if dt is None:
                return None
            if hasattr(dt, "isoformat"):
                return dt.isoformat()
            return str(dt)

        return {
            "status": job.status or "unknown",
            "progress": job.progress_percentage or 0,
            "phase": job.solver_phase or "",
            "message": getattr(job, "status_message", ""),
            "started_at": safe_isoformat(job.started_at),
            "estimated_completion": None,  # Could calculate based on progress
        }

    except (ValueError, TypeError) as e:
        logger.error(f"Invalid job_id format {job_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to get initial job status for {job_id}: {e}")
        return None


async def user_can_access_job(user_id: str, job_id: str, db: AsyncSession) -> bool:
    """Check if user can access job updates."""
    try:
        from app.models import TimetableJob

        job_uuid = UUID(job_id)
        user_uuid = UUID(user_id)

        # Simple implementation - users can access their own jobs
        query = select(TimetableJob).where(
            TimetableJob.id == job_uuid, TimetableJob.initiated_by == user_uuid
        )

        result = await db.execute(query)
        job = result.scalar_one_or_none()
        return job is not None

    except (ValueError, TypeError) as e:
        logger.error(f"Invalid UUID format - user: {user_id}, job: {job_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error checking job access for user {user_id}, job {job_id}: {e}")
        return False


async def notify_job_completed(job_id: str, result: Dict[str, Any]) -> None:
    """Notify that a job has completed"""
    await publish_job_update(
        job_id,
        {
            "status": "completed" if result.get("success") else "failed",
            "progress": 100,
            "phase": "completed",
            "message": (
                "Job completed successfully"
                if result.get("success")
                else f"Job failed: {result.get('error', 'Unknown error')}"
            ),
            "result": result,
        },
    )


async def notify_job_cancelled(job_id: str, reason: str = "Cancelled by user") -> None:
    """Notify that a job has been cancelled"""
    await publish_job_update(
        job_id,
        {"status": "cancelled", "progress": 0, "phase": "cancelled", "message": reason},
    )


async def notify_job_error(job_id: str, error_message: str) -> None:
    """Notify that a job has encountered an error"""
    await publish_job_update(
        job_id,
        {
            "status": "failed",
            "progress": 0,
            "phase": "error",
            "message": f"Job failed: {error_message}",
        },
    )
