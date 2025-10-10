# backend/app/schemas/auth.py
from __future__ import annotations
from pydantic import BaseModel, Field, model_validator, ConfigDict, EmailStr
from datetime import datetime, timezone
from typing import Optional

MODEL_CONFIG = ConfigDict(from_attributes=True)


class Token(BaseModel):
    model_config = MODEL_CONFIG

    access_token: str
    token_type: str
    # NEW: Added role to the token response schema.
    role: str


class TokenData(BaseModel):
    model_config = MODEL_CONFIG

    sub: str = Field(..., description="Subject (user identifier)")
    # NEW: Added role to the decoded token data schema.
    role: Optional[str] = None
    exp: Optional[int] = Field(None, description="Expiration time as UNIX timestamp")
    exp_datetime: Optional[datetime] = Field(
        None, description="Expiration time as datetime"
    )

    @model_validator(mode="before")
    def compute_exp_datetime(cls, values: dict) -> dict:
        exp = values.get("exp")
        if exp is not None:
            values["exp_datetime"] = datetime.fromtimestamp(exp, tz=timezone.utc)
        return values

    @model_validator(mode="after")
    def check_not_expired(self) -> "TokenData":
        if self.exp_datetime and self.exp_datetime < datetime.now(timezone.utc):
            raise ValueError("Token has expired")
        return self


# --- NEW: Schemas for Self-Registration ---


class StudentSelfRegister(BaseModel):
    """Schema for a student to self-register a user account."""

    matric_number: str = Field(
        ..., description="Student's unique matriculation number."
    )
    email: EmailStr = Field(..., description="Student's email address for the account.")
    password: str = Field(
        ..., min_length=8, description="Desired password for the account."
    )


class StaffSelfRegister(BaseModel):
    """Schema for a staff member to self-register a user account."""

    staff_number: str = Field(..., description="Staff member's unique ID number.")
    email: EmailStr = Field(
        ..., description="Staff member's email address for the account."
    )
    password: str = Field(
        ..., min_length=8, description="Desired password for the account."
    )
