# backend/app/schemas/users.py
from __future__ import annotations
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from uuid import UUID

MODEL_CONFIG = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    model_config = MODEL_CONFIG

    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = True


class UserCreate(UserBase):
    password: str
    is_active: bool = True
    is_superuser: bool = False


class UserRead(UserBase):
    id: UUID
