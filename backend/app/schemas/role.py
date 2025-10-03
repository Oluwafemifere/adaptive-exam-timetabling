# backend/app/schemas/role.py
from uuid import UUID
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class RoleAssignment(BaseModel):
    user_id: UUID
    role_name: str


class UserRolesResponse(BaseModel):
    user_id: UUID
    roles: List[str]


class PermissionCheckResponse(BaseModel):
    user_id: UUID
    permission: str
    has_permission: bool


class RolePermissionsUpdate(BaseModel):
    permissions: List[str] = Field(
        ..., description="A list of permission strings, e.g., 'course:create'."
    )


class RoleWithPermissionsRead(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    permissions: List[str]

    class Config:
        from_attributes = True
