# backend/app/api/v1/routes/roles.py
"""API endpoints for Role-Based Access Control (RBAC)."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.user_management.authorization_service import AuthorizationService
from ....services.data_retrieval import DataRetrievalService
from ....schemas.role import (
    RoleAssignment,
    UserRolesResponse,
    PermissionCheckResponse,
    RolePermissionsUpdate,
    RoleWithPermissionsRead,
)
from ....schemas.system import GenericResponse

router = APIRouter()


@router.get("/", response_model=List[RoleWithPermissionsRead])
async def get_all_roles(
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Get all roles and their associated permissions."""
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    service = DataRetrievalService(db)
    roles = await service.get_all_roles_with_permissions()
    return roles if roles else []


@router.put("/{role_name}/permissions", response_model=GenericResponse)
async def update_role_permissions(
    role_name: str,
    payload: RolePermissionsUpdate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Update the permissions for a specific role."""
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    service = AuthorizationService(db)
    result = await service.update_role_permissions(
        role_name=role_name,
        permissions=payload.permissions,
        admin_user_id=user.id,
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Failed to update permissions.")
        )

    return GenericResponse(
        success=True,
        message="Role permissions updated successfully.",
        data=result.get("role"),
    )


@router.post("/assign", response_model=GenericResponse)
async def assign_role(
    assignment: RoleAssignment,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Assign a role to a user."""
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    service = AuthorizationService(db)
    result = await service.assign_role_to_user(
        user_id=assignment.user_id, role_name=assignment.role_name
    )
    if not result.get("success", True):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Failed to assign role")
        )
    return GenericResponse(success=True, data=result)


@router.get("/users/{user_id}", response_model=UserRolesResponse)
async def get_user_roles(
    user_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Get all roles assigned to a specific user."""
    service = AuthorizationService(db)
    roles = await service.get_user_roles(user_id)
    return UserRolesResponse(user_id=user_id, roles=roles)


@router.get("/check/{user_id}/{permission}", response_model=PermissionCheckResponse)
async def check_permission(
    user_id: UUID,
    permission: str,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Check if a user has a specific permission."""
    service = AuthorizationService(db)
    has_permission = await service.check_user_permission(user_id, permission)
    return PermissionCheckResponse(
        user_id=user_id, permission=permission, has_permission=has_permission
    )
