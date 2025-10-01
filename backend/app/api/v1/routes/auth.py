# backend\app\api\v1\routes\auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session
from ....core.auth import authenticate_user, create_token_for_user
from ....schemas.auth import Token
from ....services.data_retrieval import DataRetrievalService
from ....core.security import verify_password
from ....core.auth import create_token_for_user

router = APIRouter()


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(db_session),
):
    # This route uses the core authentication function
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_data = await create_token_for_user(user)
    return token_data


# --- NEWLY ADDED ROUTE ---


@router.post("/token/service", response_model=Token, include_in_schema=False)
async def login_for_access_token_with_service(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(db_session),
):
    """
    An alternative login endpoint to demonstrate usage of the
    `DataRetrievalService.authenticate_user` method.
    """
    service = DataRetrievalService(db)
    user_data = await service.authenticate_user(
        email=form_data.username, password=form_data.password
    )

    if not user_data or not user_data.get("id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Note: This is a simplified user object for token creation
    from ....models.users import User

    user = User(**user_data)
    token_data = await create_token_for_user(user)
    return token_data
