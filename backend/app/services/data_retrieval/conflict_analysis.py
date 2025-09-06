# backend/app/services/data_retrieval/conflict_analysis_service.py
"""
Service for analyzing scheduling data conflicts and utilization metrics
"""
from typing import Dict, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ...models.academic import CourseRegistration
from ...models.infrastructure import Room, Building
from ...schemas.scheduling import StaffUnavailabilityRead


class ConflictAnalysis:
    """Analyzes student registration conflicts and room utilization"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_student_conflicts(self, session_id: str) -> Dict[str, int]:
        """
        Returns number of students registered for more than one course in the same session
        """
        stmt = (
            select(
                CourseRegistration.student_id,
                func.count(CourseRegistration.course_id).label("course_count"),
            )
            .where(CourseRegistration.session_id == session_id)
            .group_by(CourseRegistration.student_id)
            .having(func.count(CourseRegistration.course_id) > 1)
        )
        result = await self.session.execute(stmt)
        return {str(row.student_id): row.course_count for row in result}

    async def get_room_utilization(self) -> Dict[str, Dict[str, float]]:
        """
        Returns utilization statistics per building:
        - total rooms
        - total capacity
        - average capacity
        """
        stmt = select(
            Building.name,
            func.count(Room.id).label("room_count"),
            func.sum(Room.capacity).label("total_capacity"),
            func.avg(Room.capacity).label("avg_capacity"),
        ).join(Room, Room.building_id == Building.id)
        result = await self.session.execute(stmt.group_by(Building.id))
        data = {}
        for name, count, total, avg in result:
            data[name] = {
                "room_count": count,
                "total_capacity": float(total or 0),
                "average_capacity": float(avg or 0),
            }
        return data
