# C:\Users\fresh\OneDrive\Dokumen\thesis\proj\CODE\adaptive-exam-timetabling\backend\app\api\deps.py
import logging
from typing import AsyncGenerator, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status, WebSocket
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..database import get_db
from ..models.users import User

# Configure logging
logger = logging.getLogger(__name__)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get a database session."""
    async for session in get_db():
        yield session


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    """Retrieve a user from the database by their UUID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(db_session)
) -> User:
    """Dependency to get the current user from a JWT in an Authorization header."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id_str: Optional[str] = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user = await get_user_by_id(db, user_id=user_id)
    if user is None:
        raise credentials_exception
    return user


async def current_user(user: User = Depends(get_current_user)) -> User:
    """A simple wrapper dependency for getting the current user."""
    return user


async def get_current_user_for_websocket(
    websocket: WebSocket,
    db: AsyncSession = Depends(db_session),
) -> Optional[User]:
    """
    Dependency to get the current user for a WebSocket connection.
    It extracts the JWT from the 'token' query parameter.
    """
    token = websocket.query_params.get("token")
    if token is None:
        logger.warning("WebSocket connection attempt without token.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id_str: Optional[str] = payload.get("sub")
        if user_id_str is None:
            logger.warning("WebSocket token payload missing 'sub' claim.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
        user_id = UUID(user_id_str)

    except (JWTError, ValueError) as e:
        logger.warning(f"WebSocket token validation failed: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    user = await get_user_by_id(db, user_id=user_id)
    if user is None:
        logger.warning(f"WebSocket auth successful, but user %s not in DB.", user_id)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    logger.info("WebSocket authenticated successfully for user %s", user.email)
    return user
