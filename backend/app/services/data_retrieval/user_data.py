# backend/app/services/data_retrieval/user_data.py

"""
Service for retrieving user and system data from the database
"""

from typing import Dict, List, Optional, cast
from uuid import UUID
from datetime import datetime as ddatetime
from sqlalchemy import select, func, and_, or_, not_  # Added not_ import
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.users import (
    User,
    UserRole,
    UserRoleAssignment,
    UserNotification,
    SystemConfiguration,
    SystemEvent,
)


class UserData:
    """Service for retrieving user and system-related data"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # Users
    async def get_all_users(self) -> List[Dict]:
        """Get all users with their roles"""
        stmt = (
            select(User)
            .options(selectinload(User.roles).selectinload(UserRoleAssignment.role))
            .order_by(User.email)
        )
        result = await self.session.execute(stmt)
        users = result.scalars().all()

        return [
            {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "last_login": (
                    cast(ddatetime, user.last_login).isoformat()
                    if user.last_login
                    else None
                ),
                "roles": [
                    {
                        "role_id": str(assignment.role_id),
                        "role_name": assignment.role.name if assignment.role else None,
                        "faculty_id": (
                            str(assignment.faculty_id)
                            if assignment.faculty_id
                            else None
                        ),
                        "department_id": (
                            str(assignment.department_id)
                            if assignment.department_id
                            else None
                        ),
                        "assigned_at": (
                            cast(ddatetime, assignment.assigned_at).isoformat()
                            if assignment.assigned_at
                            else None
                        ),
                    }
                    for assignment in user.roles
                ],
                "created_at": (
                    cast(ddatetime, user.created_at).isoformat()
                    if user.created_at
                    else None
                ),
                "updated_at": (
                    cast(ddatetime, user.updated_at).isoformat()
                    if user.updated_at
                    else None
                ),
            }
            for user in users
        ]

    async def get_active_users(self) -> List[Dict]:
        """Get only active users"""
        stmt = (
            select(User)
            .options(selectinload(User.roles).selectinload(UserRoleAssignment.role))
            .where(User.is_active)
            .order_by(User.email)
        )
        result = await self.session.execute(stmt)
        users = result.scalars().all()

        return [
            {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "is_superuser": user.is_superuser,
                "last_login": (
                    cast(ddatetime, user.last_login).isoformat()
                    if user.last_login
                    else None
                ),
                "role_count": len(user.roles),
            }
            for user in users
        ]

    async def get_user_by_id(self, user_id: UUID) -> Optional[Dict]:
        """Get user by ID with complete role information"""
        stmt = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(UserRoleAssignment.role),
                selectinload(User.notifications),
            )
            .where(User.id == user_id)
        )
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return None

        return {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "last_login": (
                cast(ddatetime, user.last_login).isoformat()
                if user.last_login
                else None
            ),
            "roles": [
                {
                    "assignment_id": str(assignment.id),
                    "role_id": str(assignment.role_id),
                    "role_name": assignment.role.name if assignment.role else None,
                    "role_description": (
                        assignment.role.description if assignment.role else None
                    ),
                    "faculty_id": (
                        str(assignment.faculty_id) if assignment.faculty_id else None
                    ),
                    "department_id": (
                        str(assignment.department_id)
                        if assignment.department_id
                        else None
                    ),
                    "assigned_at": (
                        cast(ddatetime, assignment.assigned_at).isoformat()
                        if assignment.assigned_at
                        else None
                    ),
                }
                for assignment in user.roles
            ],
            "notification_count": len(user.notifications),
            "unread_notification_count": len(
                [n for n in user.notifications if not n.is_read]
            ),
            "created_at": (
                cast(ddatetime, user.created_at).isoformat()
                if user.created_at
                else None
            ),
            "updated_at": (
                cast(ddatetime, user.updated_at).isoformat()
                if user.updated_at
                else None
            ),
        }

    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        stmt = (
            select(User)
            .options(selectinload(User.roles).selectinload(UserRoleAssignment.role))
            .where(User.email == email)
        )
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return None

        return {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "last_login": (
                cast(ddatetime, user.last_login).isoformat()
                if user.last_login
                else None
            ),
            "roles": [
                {
                    "role_id": str(assignment.role_id),
                    "role_name": assignment.role.name if assignment.role else None,
                    "faculty_id": (
                        str(assignment.faculty_id) if assignment.faculty_id else None
                    ),
                    "department_id": (
                        str(assignment.department_id)
                        if assignment.department_id
                        else None
                    ),
                }
                for assignment in user.roles
            ],
        }

    # User Roles
    async def get_all_user_roles(self) -> List[Dict]:
        """Get all user roles with assignment counts"""
        stmt = (
            select(UserRole)
            .options(selectinload(UserRole.assignments))
            .order_by(UserRole.name)
        )
        result = await self.session.execute(stmt)
        roles = result.scalars().all()

        return [
            {
                "id": str(role.id),
                "name": role.name,
                "description": role.description,
                "permissions": role.permissions,
                "assignment_count": len(role.assignments),
                "created_at": (
                    cast(ddatetime, role.created_at).isoformat()
                    if role.created_at
                    else None
                ),
                "updated_at": (
                    cast(ddatetime, role.updated_at).isoformat()
                    if role.updated_at
                    else None
                ),
            }
            for role in roles
        ]

    async def get_role_by_id(self, role_id: UUID) -> Optional[Dict]:
        """Get role by ID with assignments"""
        stmt = (
            select(UserRole)
            .options(
                selectinload(UserRole.assignments).selectinload(UserRoleAssignment.user)
            )
            .where(UserRole.id == role_id)
        )
        result = await self.session.execute(stmt)
        role = result.scalar_one_or_none()

        if not role:
            return None

        return {
            "id": str(role.id),
            "name": role.name,
            "description": role.description,
            "permissions": role.permissions,
            "assignments": [
                {
                    "assignment_id": str(assignment.id),
                    "user_id": str(assignment.user_id),
                    "user_email": assignment.user.email if assignment.user else None,
                    "user_name": (
                        f"{assignment.user.first_name} {assignment.user.last_name}"
                        if assignment.user
                        else None
                    ),
                    "faculty_id": (
                        str(assignment.faculty_id) if assignment.faculty_id else None
                    ),
                    "department_id": (
                        str(assignment.department_id)
                        if assignment.department_id
                        else None
                    ),
                    "assigned_at": (
                        cast(ddatetime, assignment.assigned_at).isoformat()
                        if assignment.assigned_at
                        else None
                    ),
                }
                for assignment in role.assignments
            ],
            "created_at": (
                cast(ddatetime, role.created_at).isoformat()
                if role.created_at
                else None
            ),
            "updated_at": (
                cast(ddatetime, role.updated_at).isoformat()
                if role.updated_at
                else None
            ),
        }

    # User Role Assignments
    async def get_user_role_assignments(
        self, user_id: Optional[UUID] = None, role_id: Optional[UUID] = None
    ) -> List[Dict]:
        """Get user role assignments with filters"""
        stmt = select(UserRoleAssignment).options(
            selectinload(UserRoleAssignment.user), selectinload(UserRoleAssignment.role)
        )

        if user_id:
            stmt = stmt.where(UserRoleAssignment.user_id == user_id)
        if role_id:
            stmt = stmt.where(UserRoleAssignment.role_id == role_id)

        stmt = stmt.order_by(UserRoleAssignment.assigned_at.desc())
        result = await self.session.execute(stmt)
        assignments = result.scalars().all()

        return [
            {
                "id": str(assignment.id),
                "user_id": str(assignment.user_id),
                "user_email": assignment.user.email if assignment.user else None,
                "user_name": (
                    f"{assignment.user.first_name} {assignment.user.last_name}"
                    if assignment.user
                    else None
                ),
                "role_id": str(assignment.role_id),
                "role_name": assignment.role.name if assignment.role else None,
                "faculty_id": (
                    str(assignment.faculty_id) if assignment.faculty_id else None
                ),
                "department_id": (
                    str(assignment.department_id) if assignment.department_id else None
                ),
                "assigned_at": (
                    cast(ddatetime, assignment.assigned_at).isoformat()
                    if assignment.assigned_at
                    else None
                ),
            }
            for assignment in assignments
        ]

    # User Notifications
    async def get_user_notifications(
        self, user_id: UUID, is_read: Optional[bool] = None
    ) -> List[Dict]:
        """Get notifications for a user"""
        stmt = (
            select(UserNotification)
            .options(selectinload(UserNotification.event))
            .where(UserNotification.user_id == user_id)
        )

        if is_read is not None:
            stmt = stmt.where(UserNotification.is_read == is_read)

        stmt = stmt.order_by(UserNotification.created_at.desc())
        result = await self.session.execute(stmt)
        notifications = result.scalars().all()

        return [
            {
                "id": str(notification.id),
                "event_id": str(notification.event_id),
                "event_title": notification.event.title if notification.event else None,
                "event_message": (
                    notification.event.message if notification.event else None
                ),
                "event_type": (
                    notification.event.event_type if notification.event else None
                ),
                "priority": notification.event.priority if notification.event else None,
                "is_read": notification.is_read,
                "read_at": (
                    cast(ddatetime, notification.read_at).isoformat()
                    if notification.read_at
                    else None
                ),
                "created_at": (
                    cast(ddatetime, notification.created_at).isoformat()
                    if notification.created_at
                    else None
                ),
            }
            for notification in notifications
        ]

    async def get_notification_statistics(self, user_id: UUID) -> Dict:
        """Get notification statistics for a user"""
        # Total notifications
        total_stmt = select(func.count(UserNotification.id)).where(
            UserNotification.user_id == user_id
        )
        total_result = await self.session.execute(total_stmt)
        total_notifications = total_result.scalar() or 0

        # Unread notifications
        unread_stmt = select(func.count(UserNotification.id)).where(
            and_(UserNotification.user_id == user_id, not_(UserNotification.is_read))
        )
        unread_result = await self.session.execute(unread_stmt)
        unread_notifications = unread_result.scalar() or 0

        return {
            "user_id": str(user_id),
            "total_notifications": total_notifications,
            "unread_notifications": unread_notifications,
            "read_notifications": total_notifications - unread_notifications,
        }

    # System Configurations
    async def get_all_system_configurations(self) -> List[Dict]:
        """Get all system configurations"""
        stmt = (
            select(SystemConfiguration)
            .options(selectinload(SystemConfiguration.constraints))
            .order_by(SystemConfiguration.created_at.desc())
        )
        result = await self.session.execute(stmt)
        configurations = result.scalars().all()

        return [
            {
                "id": str(config.id),
                "name": config.name,
                "description": config.description,
                "created_by": str(config.created_by),
                "is_default": config.is_default,
                "constraint_count": len(config.constraints),
                "created_at": (
                    cast(ddatetime, config.created_at).isoformat()
                    if config.created_at
                    else None
                ),
                "updated_at": (
                    cast(ddatetime, config.updated_at).isoformat()
                    if config.updated_at
                    else None
                ),
            }
            for config in configurations
        ]

    async def get_default_system_configuration(self) -> Optional[Dict]:
        """Get the default system configuration"""
        stmt = (
            select(SystemConfiguration)
            .options(selectinload(SystemConfiguration.constraints))
            .where(SystemConfiguration.is_default)
        )
        result = await self.session.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            return None

        return {
            "id": str(config.id),
            "name": config.name,
            "description": config.description,
            "created_by": str(config.created_by),
            "is_default": config.is_default,
            "constraints": [
                {
                    "constraint_id": str(constraint.constraint_id),
                    "custom_parameters": constraint.custom_parameters,
                    "weight": (
                        float(constraint.weight)  # type: ignore
                        if constraint.weight is not None
                        else 0.0
                    ),
                    "is_enabled": constraint.is_enabled,
                }
                for constraint in config.constraints
            ],
            "created_at": (
                cast(ddatetime, config.created_at).isoformat()
                if config.created_at
                else None
            ),
            "updated_at": (
                cast(ddatetime, config.updated_at).isoformat()
                if config.updated_at
                else None
            ),
        }

    async def get_system_configuration_by_id(self, config_id: UUID) -> Optional[Dict]:
        """Get system configuration by ID"""
        stmt = (
            select(SystemConfiguration)
            .options(
                selectinload(SystemConfiguration.constraints),
                selectinload(SystemConfiguration.jobs),
            )
            .where(SystemConfiguration.id == config_id)
        )
        result = await self.session.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            return None

        return {
            "id": str(config.id),
            "name": config.name,
            "description": config.description,
            "created_by": str(config.created_by),
            "is_default": config.is_default,
            "constraints": [
                {
                    "id": str(constraint.id),
                    "constraint_id": str(constraint.constraint_id),
                    "custom_parameters": constraint.custom_parameters,
                    "weight": (
                        float(constraint.weight)  # type: ignore
                        if constraint.weight is not None
                        else 0.0
                    ),
                    "is_enabled": constraint.is_enabled,
                }
                for constraint in config.constraints
            ],
            "job_count": len(config.jobs),
            "created_at": (
                cast(ddatetime, config.created_at).isoformat()
                if config.created_at
                else None
            ),
            "updated_at": (
                cast(ddatetime, config.updated_at).isoformat()
                if config.updated_at
                else None
            ),
        }

    # System Events
    async def get_system_events(
        self, event_type: Optional[str] = None, is_resolved: Optional[bool] = None
    ) -> List[Dict]:
        """Get system events with filters"""
        stmt = select(SystemEvent).order_by(SystemEvent.created_at.desc())

        if event_type:
            stmt = stmt.where(SystemEvent.event_type == event_type)
        if is_resolved is not None:
            stmt = stmt.where(SystemEvent.is_resolved == is_resolved)

        result = await self.session.execute(stmt)
        events = result.scalars().all()

        return [
            {
                "id": str(event.id),
                "title": event.title,
                "message": event.message,
                "event_type": event.event_type,
                "priority": event.priority,
                "entity_type": event.entity_type,
                "entity_id": str(event.entity_id) if event.entity_id else None,
                "event_metadata": event.event_metadata,
                "affected_users": [str(uid) for uid in (event.affected_users or [])],
                "is_resolved": event.is_resolved,
                "resolved_by": str(event.resolved_by) if event.resolved_by else None,
                "resolved_at": (
                    cast(ddatetime, event.resolved_at).isoformat()
                    if event.resolved_at
                    else None
                ),
                "created_at": (
                    cast(ddatetime, event.created_at).isoformat()
                    if event.created_at
                    else None
                ),
            }
            for event in events
        ]

    async def get_system_event_by_id(self, event_id: UUID) -> Optional[Dict]:
        """Get system event by ID"""
        stmt = (
            select(SystemEvent)
            .options(selectinload(SystemEvent.notifications))
            .where(SystemEvent.id == event_id)
        )
        result = await self.session.execute(stmt)
        event = result.scalar_one_or_none()

        if not event:
            return None

        return {
            "id": str(event.id),
            "title": event.title,
            "message": event.message,
            "event_type": event.event_type,
            "priority": event.priority,
            "entity_type": event.entity_type,
            "entity_id": str(event.entity_id) if event.entity_id else None,
            "event_metadata": event.event_metadata,
            "affected_users": [str(uid) for uid in (event.affected_users or [])],
            "is_resolved": event.is_resolved,
            "resolved_by": str(event.resolved_by) if event.resolved_by else None,
            "resolved_at": (
                cast(ddatetime, event.resolved_at).isoformat()
                if event.resolved_at
                else None
            ),
            "notification_count": len(event.notifications),
            "created_at": (
                cast(ddatetime, event.created_at).isoformat()
                if event.created_at
                else None
            ),
            "updated_at": (
                cast(ddatetime, event.updated_at).isoformat()
                if event.updated_at
                else None
            ),
        }

    async def get_unresolved_events_count(self) -> int:
        """Get count of unresolved system events"""
        stmt = select(func.count(SystemEvent.id)).where(not_(SystemEvent.is_resolved))
        result = await self.session.execute(stmt)
        count = result.scalar()
        return count or 0

    # Search and utility functions
    async def search_users(self, search_term: str) -> List[Dict]:
        """Search users by email, first name, or last name"""
        search_pattern = f"%{search_term}%"

        stmt = (
            select(User)
            .where(
                or_(
                    User.email.ilike(search_pattern),
                    User.first_name.ilike(search_pattern),
                    User.last_name.ilike(search_pattern),
                )
            )
            .order_by(User.email)
        )
        result = await self.session.execute(stmt)
        users = result.scalars().all()

        return [
            {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
            }
            for user in users
        ]

    async def get_users_by_role(self, role_name: str) -> List[Dict]:
        """Get users by role name"""
        stmt = (
            select(User)
            .join(UserRoleAssignment, UserRoleAssignment.user_id == User.id)
            .join(UserRole, UserRole.id == UserRoleAssignment.role_id)
            .where(UserRole.name == role_name)
            .order_by(User.email)
        )
        result = await self.session.execute(stmt)
        users = result.scalars().all()

        return [
            {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
            }
            for user in users
        ]
