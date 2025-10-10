# backend/app/schemas/users.py
from __future__ import annotations
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


MODEL_CONFIG = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    model_config = MODEL_CONFIG

    email: EmailStr
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    role: str


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


# NEW: Schema for the admin user creation endpoint
class AdminUserCreate(BaseModel):
    """Schema for an admin to create any type of user."""

    user_type: str = Field(
        ..., pattern="^(student|admin)$"
    )  # Must be 'student' or 'admin'
    email: EmailStr
    first_name: str
    last_name: str
    password: str = Field(..., min_length=8)

    # Required for students
    session_id: Optional[UUID] = None
    matric_number: Optional[str] = None
    programme_code: Optional[str] = None
    entry_year: Optional[int] = None


class UserUpdate(BaseModel):
    model_config = MODEL_CONFIG

    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None


class UserRead(UserBase):
    id: UUID
    last_login: Optional[datetime] = None


class UserManagementRecord(UserRead):
    # This model now correctly inherits the 'role' field from UserRead.
    # The 'assigned_roles' field has been removed as it is no longer needed.
    pass


class PaginatedUserResponse(BaseModel):
    total_items: int
    total_pages: int
    page: int
    page_size: int
    items: List[UserManagementRecord]
