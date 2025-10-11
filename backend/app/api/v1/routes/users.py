# backend/app/api/v1/routes/users.py
"""API endpoints for user management."""

from typing import List, Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from pydantic import BaseModel, UUID4

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.user_management import (
    AuthenticationService,
    UserManagementService,  # --- UPDATED: Import new service ---
)
from ....services.data_retrieval.data_retrieval_service import DataRetrievalService
from ....schemas.users import (
    UserCreate,
    UserRead,
    UserUpdate,
    PaginatedUserResponse,  # --- UPDATED: Schema now includes total counts ---
    AdminUserCreate,
)
from ....schemas.system import GenericResponse

router = APIRouter()


class UserRoleIDResponse(BaseModel):
    """Response model for the user's specific role ID."""

    type: str
    id: Optional[UUID4] = None
    message: Optional[str] = None


@router.get("/me", response_model=UserRead)
async def read_users_me(current_user: User = Depends(current_user)):
    """Get the current authenticated user's details."""
    return current_user


@router.post(
    "/admin", response_model=GenericResponse, status_code=status.HTTP_201_CREATED
)
async def admin_create_user(
    user_in: AdminUserCreate,
    db: AsyncSession = Depends(db_session),
    admin_user: User = Depends(current_user),
):
    """
    (Admin only) Create a new user (student or admin).
    If creating a student, this will also enroll them in the specified session.
    """
    if not admin_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )

    service = AuthenticationService(db)
    user_data = user_in.model_dump()

    result = await service.admin_create_user(
        admin_user_id=admin_user.id, user_data=user_data
    )

    if result.get("status") != "success":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to create user."),
        )

    return GenericResponse(
        success=True,
        message=result.get("message"),
        data={"user_id": result.get("user_id"), "student_id": result.get("student_id")},
    )


@router.get("/", response_model=PaginatedUserResponse)
async def get_user_management_data(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search_term: Optional[str] = None,
    role_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve paginated, searchable, and filterable user data for management."""
    service = DataRetrievalService(db)
    result = await service.get_user_management_data(
        page, page_size, search_term, role_filter, status_filter
    )
    if not result:
        raise HTTPException(status_code=404, detail="No users found.")
    return result


@router.put("/{user_id}", response_model=GenericResponse)
async def update_user(
    user_id: UUID,
    user_in: UserUpdate,
    db: AsyncSession = Depends(db_session),
    admin_user: User = Depends(current_user),
):
    """Update a user's details (admin only)."""
    if not admin_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    # --- UPDATED: Use the new dedicated service ---
    service = UserManagementService(db)
    update_data = user_in.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided."
        )

    result = await service.update_user(user_id, update_data, admin_user.id)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error")
        )

    return GenericResponse(
        success=True, message="User updated successfully.", data=result.get("user")
    )


@router.delete("/{user_id}", response_model=GenericResponse)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(db_session),
    admin_user: User = Depends(current_user),
):
    """Delete a user (admin only)."""
    if not admin_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own user account.",
        )

    # --- UPDATED: Use the new dedicated service ---
    service = UserManagementService(db)
    result = await service.delete_user(user_id, admin_user.id)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error")
        )

    return GenericResponse(success=True, message=result.get("message"))


@router.get("/{user_id}/role", response_model=UserRoleIDResponse)
async def get_user_role_id(
    user_id: UUID,
    db: AsyncSession = Depends(db_session),
    current_user: User = Depends(current_user),
):
    """Retrieves the specific role type and ID (student or staff) for a given user."""
    service = DataRetrievalService(db)
    result = await service.get_user_role_id(user_id)

    if not result or result.get("type") == "unknown":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No specific role found for user with ID {user_id}.",
        )

    return result
