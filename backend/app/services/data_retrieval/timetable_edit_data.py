# backend/app/services/data_retrieval/timetable_edit_data.py

"""
Service for retrieving timetable edit data from the database
"""

from typing import Dict, List, cast, Optional, Any
from uuid import UUID
from datetime import datetime as ddatetime
from sqlalchemy import select, func, and_, or_, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.timetable_edits import TimetableEdit


class TimetableEditData:
    """Service for retrieving timetable edit-related data"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_edit(
        self,
        version_id: UUID,
        exam_id: UUID,
        edited_by: UUID,
        edit_type: str,
        old_values: Dict,
        new_values: Dict,
        reason: Optional[str] = None,
        validation_status: str = "pending",
    ) -> UUID:
        """Create a new timetable edit"""
        edit = TimetableEdit(
            version_id=version_id,
            exam_id=exam_id,
            edited_by=edited_by,
            edit_type=edit_type,
            old_values=old_values,
            new_values=new_values,
            reason=reason,
            validation_status=validation_status,
        )
        self.session.add(edit)
        await self.session.flush()
        return edit.id

    async def update_edit_status(self, edit_id: UUID, status: str) -> None:
        """Update the validation status of a timetable edit"""
        stmt = (
            update(TimetableEdit)
            .where(TimetableEdit.id == edit_id)
            .values(validation_status=status)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_all_timetable_edits(self, limit: int = 100) -> List[Dict]:
        """Get all timetable edits with pagination"""
        stmt = (
            select(TimetableEdit).order_by(TimetableEdit.created_at.desc()).limit(limit)
        )
        result = await self.session.execute(stmt)
        edits = result.scalars().all()

        return [
            {
                "id": str(edit.id),
                "version_id": str(edit.version_id),
                "exam_id": str(edit.exam_id),
                "edited_by": str(edit.edited_by),
                "edit_type": edit.edit_type,
                "old_values": edit.old_values,
                "new_values": edit.new_values,
                "reason": edit.reason,
                "validation_status": edit.validation_status,
                "created_at": (
                    cast(ddatetime, edit.created_at).isoformat()
                    if edit.created_at
                    else None
                ),
                "updated_at": (
                    cast(ddatetime, edit.updated_at).isoformat()
                    if edit.updated_at
                    else None
                ),
            }
            for edit in edits
        ]

    async def get_edits_by_version(self, version_id: UUID) -> List[Dict[str, Any]]:
        """Get timetable edits for a specific version."""
        stmt = (
            select(TimetableEdit)
            .where(TimetableEdit.version_id == version_id)
            .order_by(TimetableEdit.created_at.desc())
        )
        result = await self.session.execute(stmt)
        edits = result.scalars().all()

        out: List[Dict[str, Any]] = []
        for edit in edits:
            created_at = (
                cast(ddatetime, edit.created_at).isoformat()
                if edit.created_at
                else None
            )
            out.append(
                {
                    "id": str(edit.id),
                    "exam_id": str(edit.exam_id),
                    "edited_by": str(edit.edited_by),
                    "edit_type": edit.edit_type,
                    "old_values": edit.old_values,
                    "new_values": edit.new_values,
                    "reason": edit.reason,
                    "validation_status": edit.validation_status,
                    "created_at": created_at,
                }
            )

        return out

    async def get_edits_by_exam(self, exam_id: UUID) -> List[Dict]:
        """Get timetable edits for a specific exam"""
        stmt = (
            select(TimetableEdit)
            .where(TimetableEdit.exam_id == exam_id)
            .order_by(TimetableEdit.created_at.desc())
        )
        result = await self.session.execute(stmt)
        edits = result.scalars().all()

        return [
            {
                "id": str(edit.id),
                "version_id": str(edit.version_id),
                "edited_by": str(edit.edited_by),
                "edit_type": edit.edit_type,
                "old_values": edit.old_values,
                "new_values": edit.new_values,
                "reason": edit.reason,
                "validation_status": edit.validation_status,
                "created_at": (
                    cast(ddatetime, edit.created_at).isoformat()
                    if edit.created_at
                    else None
                ),
            }
            for edit in edits
        ]

    async def get_edits_by_user(self, user_id: UUID, limit: int = 50) -> List[Dict]:
        """Get timetable edits made by a specific user"""
        stmt = (
            select(TimetableEdit)
            .where(TimetableEdit.edited_by == user_id)
            .order_by(TimetableEdit.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        edits = result.scalars().all()

        return [
            {
                "id": str(edit.id),
                "version_id": str(edit.version_id),
                "exam_id": str(edit.exam_id),
                "edit_type": edit.edit_type,
                "old_values": edit.old_values,
                "new_values": edit.new_values,
                "reason": edit.reason,
                "validation_status": edit.validation_status,
                "created_at": (
                    cast(ddatetime, edit.created_at).isoformat()
                    if edit.created_at
                    else None
                ),
            }
            for edit in edits
        ]

    async def get_edits_by_type(self, edit_type: str, limit: int = 100) -> List[Dict]:
        """Get timetable edits by edit type"""
        stmt = (
            select(TimetableEdit)
            .where(TimetableEdit.edit_type == edit_type)
            .order_by(TimetableEdit.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        edits = result.scalars().all()

        return [
            {
                "id": str(edit.id),
                "version_id": str(edit.version_id),
                "exam_id": str(edit.exam_id),
                "edited_by": str(edit.edited_by),
                "old_values": edit.old_values,
                "new_values": edit.new_values,
                "reason": edit.reason,
                "validation_status": edit.validation_status,
                "created_at": (
                    cast(ddatetime, edit.created_at).isoformat()
                    if edit.created_at
                    else None
                ),
            }
            for edit in edits
        ]

    async def get_edits_by_validation_status(
        self, validation_status: str
    ) -> List[Dict]:
        """Get timetable edits by validation status"""
        stmt = (
            select(TimetableEdit)
            .where(TimetableEdit.validation_status == validation_status)
            .order_by(TimetableEdit.created_at.desc())
        )
        result = await self.session.execute(stmt)
        edits = result.scalars().all()

        return [
            {
                "id": str(edit.id),
                "version_id": str(edit.version_id),
                "exam_id": str(edit.exam_id),
                "edited_by": str(edit.edited_by),
                "edit_type": edit.edit_type,
                "old_values": edit.old_values,
                "new_values": edit.new_values,
                "reason": edit.reason,
                "created_at": (
                    cast(ddatetime, edit.created_at).isoformat()
                    if edit.created_at
                    else None
                ),
            }
            for edit in edits
        ]

    async def get_edit_by_id(self, edit_id: UUID) -> Optional[Dict[str, Any]]:
        """Get timetable edit by ID."""
        stmt = select(TimetableEdit).where(TimetableEdit.id == edit_id)
        result = await self.session.execute(stmt)
        edit = result.scalar_one_or_none()

        if not edit:
            return None

        created_at = (
            cast(ddatetime, edit.created_at).isoformat() if edit.created_at else None
        )
        updated_at = (
            cast(ddatetime, edit.updated_at).isoformat()
            if getattr(edit, "updated_at", None)
            else None
        )

        return {
            "id": str(edit.id),
            "version_id": str(edit.version_id),
            "exam_id": str(edit.exam_id),
            "edited_by": str(edit.edited_by),
            "edit_type": edit.edit_type,
            "old_values": edit.old_values,
            "new_values": edit.new_values,
            "reason": edit.reason,
            "validation_status": edit.validation_status,
            "created_at": created_at,
            "updated_at": updated_at,
        }

    async def get_pending_edits(self) -> List[Dict]:
        """Get pending timetable edits"""
        stmt = (
            select(TimetableEdit)
            .where(TimetableEdit.validation_status == "pending")
            .order_by(TimetableEdit.created_at.asc())
        )
        result = await self.session.execute(stmt)
        edits = result.scalars().all()

        return [
            {
                "id": str(edit.id),
                "version_id": str(edit.version_id),
                "exam_id": str(edit.exam_id),
                "edited_by": str(edit.edited_by),
                "edit_type": edit.edit_type,
                "old_values": edit.old_values,
                "new_values": edit.new_values,
                "reason": edit.reason,
                "created_at": (
                    cast(ddatetime, edit.created_at).isoformat()
                    if edit.created_at
                    else None
                ),
            }
            for edit in edits
        ]

    async def get_edit_statistics(self) -> Dict:
        """Get timetable edit statistics"""
        # Total edits
        total_stmt = select(func.count(TimetableEdit.id))
        total_result = await self.session.execute(total_stmt)
        total_edits = total_result.scalar()

        # Edits by type
        type_stmt = select(
            TimetableEdit.edit_type, func.count(TimetableEdit.id).label("count")
        ).group_by(TimetableEdit.edit_type)
        type_result = await self.session.execute(type_stmt)
        type_counts = {row.edit_type: row.count for row in type_result}

        # Edits by validation status
        status_stmt = select(
            TimetableEdit.validation_status, func.count(TimetableEdit.id).label("count")
        ).group_by(TimetableEdit.validation_status)
        status_result = await self.session.execute(status_stmt)
        status_counts = {row.validation_status: row.count for row in status_result}

        # Top users by edits
        user_stmt = (
            select(
                TimetableEdit.edited_by,
                func.count(TimetableEdit.id).label("edit_count"),
            )
            .group_by(TimetableEdit.edited_by)
            .order_by(func.count(TimetableEdit.id).desc())
            .limit(10)
        )
        user_result = await self.session.execute(user_stmt)
        top_users = [
            {"user_id": str(row.edited_by), "edit_count": row.edit_count}
            for row in user_result
        ]

        # Recent edits (last 24 hours)
        recent_stmt = select(func.count(TimetableEdit.id)).where(
            TimetableEdit.created_at >= func.now() - text("INTERVAL '24 hours'")
        )
        recent_result = await self.session.execute(recent_stmt)
        recent_edits = recent_result.scalar()

        return {
            "total_edits": total_edits,
            "type_breakdown": type_counts,
            "status_breakdown": status_counts,
            "top_users": top_users,
            "recent_edits_24h": recent_edits,
        }

    async def get_edit_activity_by_date(self, days: int = 30) -> List[Dict]:
        """Get edit activity for the last N days"""
        stmt = (
            select(
                func.date(TimetableEdit.created_at).label("edit_date"),
                func.count(TimetableEdit.id).label("edit_count"),
                TimetableEdit.edit_type,
            )
            .where(
                TimetableEdit.created_at >= func.now() - text(f"INTERVAL '{days} days'")
            )
            .group_by(func.date(TimetableEdit.created_at), TimetableEdit.edit_type)
            .order_by(func.date(TimetableEdit.created_at).desc())
        )

        result = await self.session.execute(stmt)
        activity = result.all()

        return [
            {
                "date": row.edit_date.isoformat() if row.edit_date else None,
                "edit_count": row.edit_count,
                "edit_type": row.edit_type,
            }
            for row in activity
        ]

    async def search_timetable_edits(
        self,
        search_term: Optional[str] = None,
        edit_type: Optional[str] = None,
        validation_status: Optional[str] = None,
        user_id: Optional[UUID] = None,
        exam_id: Optional[UUID] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """Search timetable edits with multiple filters"""
        stmt = select(TimetableEdit)
        conditions = []

        if search_term:
            search_pattern = f"%{search_term}%"
            conditions.append(
                or_(
                    TimetableEdit.reason.ilike(search_pattern),
                    TimetableEdit.old_values.astext.ilike(search_pattern),
                    TimetableEdit.new_values.astext.ilike(search_pattern),
                )
            )

        if edit_type:
            conditions.append(TimetableEdit.edit_type == edit_type)
        if validation_status:
            conditions.append(TimetableEdit.validation_status == validation_status)
        if user_id:
            conditions.append(TimetableEdit.edited_by == user_id)
        if exam_id:
            conditions.append(TimetableEdit.exam_id == exam_id)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(TimetableEdit.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        edits = result.scalars().all()

        return [
            {
                "id": str(edit.id),
                "version_id": str(edit.version_id),
                "exam_id": str(edit.exam_id),
                "edited_by": str(edit.edited_by),
                "edit_type": edit.edit_type,
                "reason": edit.reason,
                "validation_status": edit.validation_status,
                "created_at": (
                    cast(ddatetime, edit.created_at).isoformat()
                    if edit.created_at
                    else None
                ),
            }
            for edit in edits
        ]

        if edit_type:
            conditions.append(TimetableEdit.edit_type == edit_type)
        if validation_status:
            conditions.append(TimetableEdit.validation_status == validation_status)
        if user_id:
            conditions.append(TimetableEdit.edited_by == user_id)
        if exam_id:
            conditions.append(TimetableEdit.exam_id == exam_id)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(TimetableEdit.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        edits = result.scalars().all()

        return [
            {
                "id": str(edit.id),
                "version_id": str(edit.version_id),
                "exam_id": str(edit.exam_id),
                "edited_by": str(edit.edited_by),
                "edit_type": edit.edit_type,
                "reason": edit.reason,
                "validation_status": edit.validation_status,
                "created_at": (
                    cast(ddatetime, edit.created_at).isoformat()
                    if edit.created_at
                    else None
                ),
            }
            for edit in edits
        ]

    async def get_user_edit_summary(self, user_id: UUID) -> Dict:
        """Get edit summary for a specific user"""
        # Total edits
        total_stmt = select(func.count(TimetableEdit.id)).where(
            TimetableEdit.edited_by == user_id
        )
        total_result = await self.session.execute(total_stmt)
        total_edits = total_result.scalar()

        # Edits by type
        type_stmt = (
            select(TimetableEdit.edit_type, func.count(TimetableEdit.id).label("count"))
            .where(TimetableEdit.edited_by == user_id)
            .group_by(TimetableEdit.edit_type)
        )
        type_result = await self.session.execute(type_stmt)
        type_breakdown = {row.edit_type: row.count for row in type_result}

        # Last edit
        last_edit_stmt = (
            select(TimetableEdit.created_at)
            .where(TimetableEdit.edited_by == user_id)
            .order_by(TimetableEdit.created_at.desc())
            .limit(1)
        )
        last_edit_result = await self.session.execute(last_edit_stmt)
        last_edit = last_edit_result.scalar()

        return {
            "user_id": str(user_id),
            "total_edits": total_edits,
            "type_breakdown": type_breakdown,
            "last_edit": cast(ddatetime, last_edit).isoformat() if last_edit else None,
        }

    async def get_exam_edit_history(self, exam_id: UUID) -> List[Dict]:
        """Get complete edit history for a specific exam"""
        stmt = (
            select(TimetableEdit)
            .where(TimetableEdit.exam_id == exam_id)
            .order_by(TimetableEdit.created_at.asc())
        )
        result = await self.session.execute(stmt)
        edits = result.scalars().all()

        return [
            {
                "id": str(edit.id),
                "version_id": str(edit.version_id),
                "edited_by": str(edit.edited_by),
                "edit_type": edit.edit_type,
                "old_values": edit.old_values,
                "new_values": edit.new_values,
                "reason": edit.reason,
                "validation_status": edit.validation_status,
                "created_at": (
                    cast(ddatetime, edit.created_at).isoformat()
                    if edit.created_at
                    else None
                ),
            }
            for edit in edits
        ]

    async def get_unique_edit_types(self) -> List[str]:
        """Get list of unique edit types"""
        stmt = (
            select(TimetableEdit.edit_type).distinct().order_by(TimetableEdit.edit_type)
        )
        result = await self.session.execute(stmt)
        edit_types = result.scalars().all()
        return list(edit_types)

    async def get_recent_edits(self, limit: int = 20) -> List[Dict]:
        """Get recent timetable edits"""
        stmt = (
            select(TimetableEdit).order_by(TimetableEdit.created_at.desc()).limit(limit)
        )
        result = await self.session.execute(stmt)
        edits = result.scalars().all()

        return [
            {
                "id": str(edit.id),
                "version_id": str(edit.version_id),
                "exam_id": str(edit.exam_id),
                "edited_by": str(edit.edited_by),
                "edit_type": edit.edit_type,
                "reason": edit.reason,
                "validation_status": edit.validation_status,
                "created_at": (
                    cast(ddatetime, edit.created_at).isoformat()
                    if edit.created_at
                    else None
                ),
            }
            for edit in edits
        ]
