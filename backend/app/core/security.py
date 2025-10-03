# backend/app/core/security.py

from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, Any
import jwt
from jwt import PyJWTError

# Use the main application settings
from ..config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hashes a plain-text password using bcrypt."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against a hashed one."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    # NEW: Added additional claims to store more data in the token
    additional_claims: Optional[dict[str, Any]] = None,
) -> str:
    """
    Creates a new JWT access token.

    Args:
        subject: The subject of the token (typically the user ID).
        expires_delta: The lifespan of the token. Defaults to settings.
        additional_claims: A dictionary of extra data to include in the payload.

    Returns:
        The encoded JWT string.
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"sub": subject, "exp": expire}

    # NEW: Add role and any other claims to the token payload
    if additional_claims:
        to_encode.update(additional_claims)

    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodes a JWT access token.

    Args:
        token: The JWT token string.

    Returns:
        The decoded payload as a dictionary, or None if validation fails.
    """
    try:
        return jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except PyJWTError:
        return None
