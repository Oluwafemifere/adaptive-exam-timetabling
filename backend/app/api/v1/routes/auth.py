# backend/app/api/v1/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session

# MODIFIED: Core auth functions now handle token creation with role
from ....core.auth import authenticate_user, create_token_for_user

# MODIFIED: Schema now includes the role
from ....schemas.auth import Token

router = APIRouter()


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(db_session),
):
    """
    Authenticates a user and returns an access token along with their role.
    """
    # Use the core authentication function which is more direct.
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # create_token_for_user now returns a dictionary matching the updated Token schema
    token_data = await create_token_for_user(user)
    return token_data
