# backend/app/api/v1/routes/users.py
"""API endpoints for user management."""
from typing import List, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.user_management.authentication_service import AuthenticationService
from ....services.data_retrieval.data_retrieval_service import DataRetrievalService
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

    new_user = result.get("user", {})
    return UserRead.model_validate(new_user)


@router.get("/", response_model=List[Dict[str, Any]])
async def list_all_users(
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),  # Should be admin
):
    """Retrieve a list of all users in the system."""
    service = DataRetrievalService(db)
    return await service.get_all_users() or []


@router.get("/active", response_model=List[Dict[str, Any]])
async def list_active_users(
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve a list of all currently active users."""
    service = DataRetrievalService(db)
    return await service.get_active_users() or []


@router.get("/role/{role_name}", response_model=List[Dict[str, Any]])
async def list_users_by_role(
    role_name: str,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve all users assigned to a specific role."""
    service = DataRetrievalService(db)
    return await service.get_users_by_role(role_name) or []
