# backend/app/services/user_management/__init__.py
"""
User Management Services Package.

Provides services for handling user authentication (login/registration)
and authorization (roles and permissions).
"""

from .authentication_service import AuthenticationService
from .authorization_service import AuthorizationService

__all__ = [
    "AuthenticationService",
    "AuthorizationService",
]
