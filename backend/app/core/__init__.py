# NEW version in backend/app/core/__init__.py

# Explicitly point to the correct, top-level config
from ..config import get_settings
from .security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from .auth import authenticate_user, get_current_user, create_token_for_user
from .exceptions import (
    AppError,
    SchedulingError,
    InfeasibleProblemError,
    JobNotFoundError,
    JobAccessDeniedError,
)


__all__ = [
    "get_settings",  # Export the function, not a settings instance
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "authenticate_user",
    "get_current_user",
    "create_token_for_user",
    "AppError",
    "SchedulingError",
    "InfeasibleProblemError",
    "JobNotFoundError",
    "JobAccessDeniedError",
]
