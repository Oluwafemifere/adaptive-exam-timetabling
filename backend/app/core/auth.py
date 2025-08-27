#C:\Users\fresh\OneDrive\Dokumen\thesis\proj\CODE\adaptive-exam-timetabling\backend\app\core\auth.py
from datetime import timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .config import Settings
from .security import verify_password, create_access_token
from ..database import get_db
from ..models import User
from ..schemas import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """Validate email and password, return User if valid."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user or not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Retrieve and validate the current user from the JWT token."""
    from .security import decode_access_token

    
    payload = decode_access_token(token)
    try:
       token_data = TokenData(**(payload or {}))
    except Exception:
         raise HTTPException(
             status_code=status.HTTP_401_UNAUTHORIZED,
             detail="Could not validate credentials"
         )

    email = token_data.sub
    user = await authenticate_user(db, email, password="")  # password not re-checked here
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user


async def create_token_for_user(user: User):
    """Create access token for authenticated user."""
    access_token_expires = timedelta(minutes=Settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(subject=user.email, expires_delta=access_token_expires)
    return {"access_token": token, "token_type": "bearer"}
