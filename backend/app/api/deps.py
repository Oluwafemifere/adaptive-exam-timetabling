# C:\Users\fresh\OneDrive\Dokumen\thesis\proj\CODE\adaptive-exam-timetabling\backend\app\api\deps.py
from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status, WebSocket
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from ..database import get_db
from ..core.auth import get_current_user, get_user_by_id
from ..models.users import User
from ..schemas.auth import TokenData
from ..core.config import settings
from ..core.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db():
        yield session


async def current_user(user: User = Depends(get_current_user)) -> User:
    return user


async def get_current_user_for_websocket(
    websocket: WebSocket,
    db: AsyncSession = Depends(db_session),
) -> User:
    """
    Dependency to authenticate a user via WebSocket.
    Extracts the token from the 'Authorization' header.
    """
    token = None
    auth_header = None

    # Headers in WebSocket scope are a list of byte tuples
    for key, value in websocket.scope.get("headers", []):
        if key.decode("utf-8").lower() == "authorization":
            auth_header = value.decode("utf-8")
            break

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split("Bearer ")[1]

    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token"
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # --- START OF FIX ---
    # Use the existing security function for decoding
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Use the correct function to get user by ID
    user = await get_user_by_id(db, user_id=user_id)
    if user is None:
        raise credentials_exception
    # --- END OF FIX ---
    return user
