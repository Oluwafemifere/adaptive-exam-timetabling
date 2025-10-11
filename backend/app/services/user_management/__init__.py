# backend/app/services/user_management/__init__.py
"""
User Management Services Package.

Provides services for handling user authentication (login/registration),
authorization (roles and permissions), and general user management (updates/deletions).
"""

from .authentication_service import AuthenticationService
from .authorization_service import AuthorizationService
from .user_management_service import UserManagementService
from .user_profile_service import UserProfileService


__all__ = [
    "AuthenticationService",
    "AuthorizationService",
    "UserManagementService",
    "UserProfileService",
]
