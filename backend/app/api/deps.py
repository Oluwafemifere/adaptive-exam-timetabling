from typing import AsyncGenerator
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.auth import get_current_user
from app.models.users import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db():
        yield session

async def current_user(user: User = Depends(get_current_user)) -> User:
    return user
