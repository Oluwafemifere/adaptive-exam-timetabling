# backend/app/core/auth.py

from datetime import datetime, timedelta
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..config import get_settings
from ..core.security import verify_password, create_access_token, decode_access_token
from ..database import get_db

# Import only the User model, as the role assignment tables are removed
from ..models import User

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """Authenticates a user by checking their email and password against the DB."""
    # The query is now simpler as we no longer need to join role tables.
    query = select(User).where(User.email == email)

    result = await db.execute(query)
    user = result.scalars().first()

    if not user or not user.password_hash:
        return None

    if not verify_password(password, user.password_hash):
        return None

    # Update the last_login timestamp upon successful authentication
    user.last_login = datetime.utcnow()
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def create_token_for_user(user: User) -> dict:
    """Creates an access token for a given user, including their role."""
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    # --- FIX: The user.role attribute is now a string, not an enum. ---
    # We can use it directly without accessing a '.value' property.
    role = user.role if user.role else None

    # The role is now stored as a single string in the JWT's 'role' claim
    additional_claims = {"role": role}

    token = create_access_token(
        subject=str(user.id),
        expires_delta=access_token_expires,
        additional_claims=additional_claims,
    )

    # This dictionary must match the `Token` schema in `schemas/auth.py`
    return {"access_token": token, "token_type": "bearer", "role": role}


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    """Retrieves a user from the database by their ID."""
    try:
        user_uuid = UUID(user_id)
        # The query is simplified as roles are no longer a separate table.
        query = select(User).where(User.id == user_uuid)
        result = await db.execute(query)
        return result.scalars().first()
    except (ValueError, TypeError):
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """
    Decodes JWT, validates, and returns the current active user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = await get_user_by_id(db, user_id=user_id)

    if user is None or not user.is_active:
        raise credentials_exception

    return user
