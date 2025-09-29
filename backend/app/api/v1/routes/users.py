# backend/app/api/v1/routes/users.py
"""API endpoints for user management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session
from ....services.user_management.authentication_service import AuthenticationService

# Import the new, complete schemas from the correct location
from ....schemas.users import UserCreate, UserRead

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(db_session),
):
    """Register a new user."""
    service = AuthenticationService(db)
    result = await service.register_user(user_in.model_dump())

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "User registration failed."),
        )

    # The result from the service contains the new user's data
    new_user = result.get("user", {})
    # Use the Pydantic model for response validation
    return UserRead.model_validate(new_user)
