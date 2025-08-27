#C:\Users\fresh\OneDrive\Dokumen\thesis\proj\CODE\adaptive-exam-timetabling\backend\app\services\notification\websocket_manager.py
import json
import logging
from typing import Dict, Set, Any, AsyncGenerator, Optional, cast
from uuid import UUID
from datetime import datetime
from fastapi import WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.models import TimetableJob
from app.core import Settings as settings

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
        self._redis: Optional[Redis] = None
        
    async def get_redis(self) -> Redis:
        if not self._redis:
            self._redis = Redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
        assert self._redis is not None
        return self._redis

    async def connect_job_updates(
        self, 
        websocket: WebSocket, 
        job_id: str, 
        user_id: str
    ) -> None:
        """Connect client to job updates."""
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
            'job_id': job_id,
            'user_id': user_id,
            'connected_at': datetime.utcnow(),
            'type': 'job_updates'
        }
        
        logger.info(f"WebSocket connected for job {job_id}, user {user_id}")
    
    async def disconnect(self, websocket: WebSocket) -> None:
        """Disconnect client and cleanup."""
        try:
            metadata = self.connection_metadata.get(websocket, {})
            job_id = metadata.get('job_id')
            user_id = metadata.get('user_id')
            
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
            'type': 'job_update',
            'job_id': job_id,
            'timestamp': datetime.utcnow().isoformat(),
            **message
        }
        
        message_json = json.dumps(message_data)
        disconnected = set()
        
        # Send to all connected clients
        for websocket in self.job_connections[job_id].copy():
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected:
            await self.disconnect(websocket)
    
    async def send_user_notification(
        self, 
        user_id: str, 
        notification: Dict[str, Any]
    ) -> None:
        """Send notification to all connections for a user."""
        if user_id not in self.user_connections:
            return
        
        message_data = {
            'type': 'notification',
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat(),
            **notification
        }
        
        message_json = json.dumps(message_data)
        disconnected = set()
        
        for websocket in self.user_connections[user_id].copy():
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send notification to WebSocket: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected:
            await self.disconnect(websocket)
    
    async def broadcast_system_message(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connected clients."""
        message_data = {
            'type': 'system_message',
            'timestamp': datetime.utcnow().isoformat(),
            **message
        }
        
        message_json = json.dumps(message_data)
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
            except Exception as e:
                logger.warning(f"Failed to broadcast message: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected:
            await self.disconnect(websocket)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        total_connections = sum(len(conns) for conns in self.job_connections.values())
        total_connections += sum(len(conns) for conns in self.user_connections.values())
        
        return {
            'total_connections': total_connections,
            'job_subscriptions': len(self.job_connections),
            'user_subscriptions': len(self.user_connections),
            'active_jobs': list(self.job_connections.keys()),
            'connected_users': list(self.user_connections.keys())
        }


# Global connection manager instance
connection_manager = ConnectionManager()


async def subscribe_job(
    job_id: str, 
    user_id: str, 
    db: AsyncSession
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Subscribe to job updates via Redis pub/sub.
    This is used by the WebSocket endpoint.
    """
    redis = await connection_manager.get_redis()
    channel_name = f"job_updates_{job_id}"
    pubsub = None
    
    try:
        # Subscribe to Redis channel
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel_name)
        
        # Send initial job status
        initial_status = await get_initial_job_status(job_id, db)
        if initial_status:
            yield initial_status
        
        # Listen for updates
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    
                    # Validate user can access this job
                    if await user_can_access_job(user_id, job_id, db):
                        yield data
                    else:
                        logger.warning(f"User {user_id} denied access to job {job_id}")
                        break
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in Redis message: {e}")
                except Exception as e:
                    logger.error(f"Error processing job update: {e}")
                    
    except Exception as e:
        logger.error(f"Error in job subscription for {job_id}: {e}")
    finally:
        if pubsub is not None:
            await pubsub.unsubscribe(channel_name)
            await pubsub.close()


async def publish_job_update(
    job_id: str, 
    update_data: Dict[str, Any]
) -> None:
    """Publish job update to Redis and WebSocket clients."""
    try:
        # Send via WebSocket
        await connection_manager.send_job_update(job_id, update_data)
        
        # Publish to Redis for distributed systems
        redis = await connection_manager.get_redis()
        channel_name = f"job_updates_{job_id}"
        message = json.dumps(update_data)
        await redis.publish(channel_name, message)
        
        logger.debug(f"Published update for job {job_id}: {update_data}")
        
    except Exception as e:
        logger.error(f"Failed to publish job update for {job_id}: {e}")


async def get_initial_job_status(job_id: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
    """Get initial job status for new WebSocket connections."""
    try:
        query = select(TimetableJob).where(TimetableJob.id == UUID(job_id))
        result = await db.execute(query)
        job = result.scalar_one_or_none()
        
        if not job:
            return None
        
        # Convert SQLAlchemy DateTime to ISO string
        # At runtime, job.started_at is actually a Python datetime object
        started_at_iso = None
        if job.started_at is not None:
            # Cast to datetime to satisfy type checker
            started_at_datetime = cast(datetime, job.started_at)
            started_at_iso = started_at_datetime.isoformat()
        
        return {
            'status': job.status,
            'progress': job.progress_percentage,
            'phase': job.solver_phase,
            'message': getattr(job, 'status_message', ''),
            'started_at': started_at_iso,
            'estimated_completion': None  # Could calculate based on progress
        }
        
    except Exception as e:
        logger.error(f"Failed to get initial job status for {job_id}: {e}")
        return None


async def user_can_access_job(user_id: str, job_id: str, db: AsyncSession) -> bool:
    """Check if user can access job updates."""
    try:
        # Simple implementation - expand based on your access control
        query = select(TimetableJob).where(
            TimetableJob.id == UUID(job_id),
            TimetableJob.initiated_by == UUID(user_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none() is not None
        
    except Exception as e:
        logger.error(f"Error checking job access for user {user_id}, job {job_id}: {e}")
        return False
