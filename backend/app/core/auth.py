# backend/app/core/auth.py

from datetime import timedelta
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .config import settings  # import the singleton instead of get_settings
from .security import verify_password, create_access_token, decode_access_token
from ..database import get_db
from ..models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """Authenticates a user by checking their email and password."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    if not user or not user.password_hash:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


async def create_token_for_user(user: User) -> dict:
    """Creates an access token for a given user."""
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        subject=str(user.id),
        expires_delta=access_token_expires,
    )
    return {"access_token": token, "token_type": "bearer"}


# --- START OF FIX ---
async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    """Retrieves a user from the database by their ID."""
    try:
        user_uuid = UUID(user_id)
        result = await db.execute(select(User).where(User.id == user_uuid))
        return result.scalars().first()
    except (ValueError, TypeError):
        return None


# --- END OF FIX ---


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        raise credentials_exception

    user = await get_user_by_id(db, user_id=user_id)  # Use the new helper function

    if user is None:
        raise credentials_exception

    return user
