# backend/app/schemas/roles.py
from uuid import UUID
from pydantic import BaseModel
from typing import List


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
