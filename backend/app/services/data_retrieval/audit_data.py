# backend/app/services/data_retrieval/audit_data.py

"""
Service for retrieving audit log data from the database
"""

from typing import Dict, List, Optional, cast
from uuid import UUID
from datetime import datetime as ddatetime, date as ddate
from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import ProgrammingError
from ...models.audit_logs import AuditLog


class AuditData:
    """Service for retrieving audit log data"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_audit_logs(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get all audit logs with pagination"""
        stmt = (
            select(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        try:
            result = await self.session.execute(stmt)
            logs = result.scalars().all()
        except ProgrammingError:
            return []

        return [
            {
                "id": str(log.id),
                "user_id": str(log.user_id) if log.user_id else None,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": str(log.entity_id) if log.entity_id else None,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "ip_address": str(log.ip_address) if log.ip_address else None,
                "user_agent": log.user_agent,
                "session_id": log.session_id,
                "notes": log.notes,
                "created_at": (
                    cast(ddatetime, log.created_at).isoformat()
                    if log.created_at
                    else None
                ),
            }
            for log in logs
        ]

    async def get_audit_logs_by_user(
        self, user_id: UUID, limit: int = 50
    ) -> List[Dict]:
        """Get audit logs for a specific user"""
        stmt = (
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        logs = result.scalars().all()

        return [
            {
                "id": str(log.id),
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": str(log.entity_id) if log.entity_id else None,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "ip_address": str(log.ip_address) if log.ip_address else None,
                "notes": log.notes,
                "created_at": (
                    cast(ddatetime, log.created_at).isoformat()
                    if log.created_at
                    else None
                ),
            }
            for log in logs
        ]

    async def get_audit_logs_by_entity(
        self, entity_type: str, entity_id: Optional[UUID] = None
    ) -> List[Dict]:
        """Get audit logs for a specific entity type and optionally entity ID"""
        stmt = select(AuditLog).where(AuditLog.entity_type == entity_type)

        if entity_id:
            stmt = stmt.where(AuditLog.entity_id == entity_id)

        stmt = stmt.order_by(AuditLog.created_at.desc())
        result = await self.session.execute(stmt)
        logs = result.scalars().all()

        return [
            {
                "id": str(log.id),
                "user_id": str(log.user_id) if log.user_id else None,
                "action": log.action,
                "entity_id": str(log.entity_id) if log.entity_id else None,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "ip_address": str(log.ip_address) if log.ip_address else None,
                "user_agent": log.user_agent,
                "created_at": (
                    cast(ddatetime, log.created_at).isoformat()
                    if log.created_at
                    else None
                ),
            }
            for log in logs
        ]

    async def get_audit_logs_by_action(
        self, action: str, limit: int = 100
    ) -> List[Dict]:
        """Get audit logs by action type"""
        stmt = (
            select(AuditLog)
            .where(AuditLog.action == action)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        logs = result.scalars().all()

        return [
            {
                "id": str(log.id),
                "user_id": str(log.user_id) if log.user_id else None,
                "entity_type": log.entity_type,
                "entity_id": str(log.entity_id) if log.entity_id else None,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "ip_address": str(log.ip_address) if log.ip_address else None,
                "notes": log.notes,
                "created_at": (
                    cast(ddatetime, log.created_at).isoformat()
                    if log.created_at
                    else None
                ),
            }
            for log in logs
        ]

    async def get_audit_logs_by_date_range(
        self, start_date: ddate, end_date: ddate, limit: int = 200
    ) -> List[Dict]:
        """Get audit logs within a date range"""
        stmt = (
            select(AuditLog)
            .where(
                and_(
                    func.date(AuditLog.created_at) >= start_date,
                    func.date(AuditLog.created_at) <= end_date,
                )
            )
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        logs = result.scalars().all()

        return [
            {
                "id": str(log.id),
                "user_id": str(log.user_id) if log.user_id else None,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": str(log.entity_id) if log.entity_id else None,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "ip_address": str(log.ip_address) if log.ip_address else None,
                "created_at": (
                    cast(ddatetime, log.created_at).isoformat()
                    if log.created_at
                    else None
                ),
            }
            for log in logs
        ]

    async def get_audit_log_by_id(self, log_id: UUID) -> Optional[Dict]:
        """Get specific audit log by ID"""
        stmt = select(AuditLog).where(AuditLog.id == log_id)
        result = await self.session.execute(stmt)
        log = result.scalar_one_or_none()

        if not log:
            return None

        return {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": str(log.entity_id) if log.entity_id else None,
            "old_values": log.old_values,
            "new_values": log.new_values,
            "ip_address": str(log.ip_address) if log.ip_address else None,
            "user_agent": log.user_agent,
            "session_id": log.session_id,
            "notes": log.notes,
            "created_at": (
                cast(ddatetime, log.created_at).isoformat() if log.created_at else None
            ),
            "updated_at": (
                cast(ddatetime, log.updated_at).isoformat() if log.updated_at else None
            ),
        }

    async def get_audit_statistics(self) -> Dict:
        """Get audit log statistics"""
        # Total logs
        total_stmt = select(func.count(AuditLog.id))
        total_result = await self.session.execute(total_stmt)
        total_logs = total_result.scalar()

        # Logs by action
        action_stmt = select(
            AuditLog.action, func.count(AuditLog.id).label("count")
        ).group_by(AuditLog.action)
        action_result = await self.session.execute(action_stmt)
        action_counts = {row.action: row.count for row in action_result}

        # Logs by entity type
        entity_stmt = select(
            AuditLog.entity_type, func.count(AuditLog.id).label("count")
        ).group_by(AuditLog.entity_type)
        entity_result = await self.session.execute(entity_stmt)
        entity_counts = {row.entity_type: row.count for row in entity_result}

        # Top users by activity
        user_stmt = (
            select(AuditLog.user_id, func.count(AuditLog.id).label("activity_count"))
            .where(AuditLog.user_id.isnot(None))
            .group_by(AuditLog.user_id)
            .order_by(func.count(AuditLog.id).desc())
            .limit(10)
        )
        user_result = await self.session.execute(user_stmt)
        top_users = [
            {"user_id": str(row.user_id), "activity_count": row.activity_count}
            for row in user_result
        ]

        # Recent activity (last 24 hours)
        recent_stmt = select(func.count(AuditLog.id)).where(
            AuditLog.created_at >= func.now() - text("INTERVAL '24 hours'")
        )
        recent_result = await self.session.execute(recent_stmt)
        recent_activity = recent_result.scalar()

        return {
            "total_logs": total_logs,
            "action_breakdown": action_counts,
            "entity_breakdown": entity_counts,
            "top_users": top_users,
            "recent_activity_24h": recent_activity,
        }

    async def search_audit_logs(
        self,
        search_term: str,
        entity_type: Optional[str] = None,
        action: Optional[str] = None,
        user_id: Optional[UUID] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """Search audit logs with multiple filters"""
        search_pattern = f"%{search_term}%"

        # Create search conditions
        search_conditions = [
            AuditLog.notes.ilike(search_pattern),
            AuditLog.user_agent.ilike(search_pattern),
        ]

        # Build the query
        stmt = select(AuditLog).where(or_(*search_conditions))

        if entity_type:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)

        stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        logs = result.scalars().all()

        return [
            {
                "id": str(log.id),
                "user_id": str(log.user_id) if log.user_id else None,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": str(log.entity_id) if log.entity_id else None,
                "notes": log.notes,
                "ip_address": str(log.ip_address) if log.ip_address else None,
                "created_at": (
                    cast(ddatetime, log.created_at).isoformat()
                    if log.created_at
                    else None
                ),
            }
            for log in logs
        ]

    async def log_activity(
        self,
        user_id: UUID,
        action: str,
        entity_type: str,
        entity_id: Optional[UUID] = None,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict:
        """Log an activity to the audit log"""
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            notes=notes,
            created_at=ddatetime.utcnow(),
        )

        self.session.add(audit_log)
        await self.session.flush()

        return {
            "id": audit_log.id,
            "user_id": str(audit_log.user_id),
            "action": audit_log.action,
            "entity_type": audit_log.entity_type,
            "entity_id": str(audit_log.entity_id) if audit_log.entity_id else None,
            "created_at": audit_log.created_at.isoformat(),
        }

    async def get_user_activity_summary(self, user_id: UUID) -> Dict:
        """Get activity summary for a specific user"""
        # Total actions
        total_stmt = select(func.count(AuditLog.id)).where(AuditLog.user_id == user_id)
        total_result = await self.session.execute(total_stmt)
        total_actions = total_result.scalar()

        # Actions by type
        action_stmt = (
            select(AuditLog.action, func.count(AuditLog.id).label("count"))
            .where(AuditLog.user_id == user_id)
            .group_by(AuditLog.action)
        )
        action_result = await self.session.execute(action_stmt)
        action_breakdown = {row.action: row.count for row in action_result}

        # Entities modified
        entity_stmt = (
            select(AuditLog.entity_type, func.count(AuditLog.id).label("count"))
            .where(AuditLog.user_id == user_id)
            .group_by(AuditLog.entity_type)
        )
        entity_result = await self.session.execute(entity_stmt)
        entity_breakdown = {row.entity_type: row.count for row in entity_result}

        # Last activity
        last_activity_stmt = (
            select(AuditLog.created_at)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(1)
        )
        last_activity_result = await self.session.execute(last_activity_stmt)
        last_activity = last_activity_result.scalar()

        return {
            "user_id": str(user_id),
            "total_actions": total_actions,
            "action_breakdown": action_breakdown,
            "entity_breakdown": entity_breakdown,
            "last_activity": (
                cast(ddatetime, last_activity).isoformat() if last_activity else None
            ),
        }

    async def get_entity_change_history(
        self, entity_type: str, entity_id: UUID
    ) -> List[Dict]:
        """Get complete change history for a specific entity"""
        stmt = (
            select(AuditLog)
            .where(
                and_(
                    AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id
                )
            )
            .order_by(AuditLog.created_at.asc())
        )
        result = await self.session.execute(stmt)
        logs = result.scalars().all()

        return [
            {
                "id": str(log.id),
                "user_id": str(log.user_id) if log.user_id else None,
                "action": log.action,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "notes": log.notes,
                "ip_address": str(log.ip_address) if log.ip_address else None,
                "created_at": (
                    cast(ddatetime, log.created_at).isoformat()
                    if log.created_at
                    else None
                ),
            }
            for log in logs
        ]

    async def get_unique_actions(self) -> List[str]:
        """Get list of unique actions in audit logs"""
        stmt = select(AuditLog.action).distinct().order_by(AuditLog.action)
        result = await self.session.execute(stmt)
        actions = result.scalars().all()
        return list(actions)

    async def get_unique_entity_types(self) -> List[str]:
        """Get list of unique entity types in audit logs"""
        stmt = select(AuditLog.entity_type).distinct().order_by(AuditLog.entity_type)
        result = await self.session.execute(stmt)
        entity_types = result.scalars().all()
        return list(entity_types)
