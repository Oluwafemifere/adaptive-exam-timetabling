# backend/app/services/data_retrieval/infrastructure_data.py

"""
Service for retrieving infrastructure data from the database
"""

from typing import Dict, List, Optional, cast
from uuid import UUID
from datetime import datetime as ddatetime
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import case

from ...models.infrastructure import (
    Building,
    RoomType,
    Room,
    ExamRoom,
    ExamAllowedRoom,
)


class InfrastructureData:
    """Service for retrieving infrastructure-related data"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # Buildings
    async def get_all_buildings(self) -> List[Dict]:
        """Get all buildings with room counts"""
        stmt = (
            select(Building)
            .options(selectinload(Building.rooms))
            .order_by(Building.name)
        )

        result = await self.session.execute(stmt)
        buildings = result.scalars().all()

        return [
            {
                "id": str(building.id),
                "code": building.code,
                "name": building.name,
                "is_active": building.is_active,
                "room_count": len(building.rooms),
                "active_room_count": len([r for r in building.rooms if r.is_active]),
                "total_capacity": sum(
                    [r.capacity for r in building.rooms if r.is_active]
                ),
                "total_exam_capacity": sum(
                    [
                        r.exam_capacity or r.capacity
                        for r in building.rooms
                        if r.is_active
                    ]
                ),
                "created_at": (
                    cast(ddatetime, building.created_at).isoformat()
                    if building.created_at
                    else None
                ),
                "updated_at": (
                    cast(ddatetime, building.updated_at).isoformat()
                    if building.updated_at
                    else None
                ),
            }
            for building in buildings
        ]

    async def get_active_buildings(self) -> List[Dict]:
        """Get only active buildings"""
        stmt = (
            select(Building)
            .options(selectinload(Building.rooms))
            .where(Building.is_active)
            .order_by(Building.name)
        )

        result = await self.session.execute(stmt)
        buildings = result.scalars().all()

        return [
            {
                "id": str(building.id),
                "code": building.code,
                "name": building.name,
                "room_count": len([r for r in building.rooms if r.is_active]),
                "total_capacity": sum(
                    [r.capacity for r in building.rooms if r.is_active]
                ),
            }
            for building in buildings
        ]

    async def get_building_by_id(self, building_id: UUID) -> Optional[Dict]:
        """Get building by ID with detailed room information"""
        stmt = (
            select(Building)
            .options(selectinload(Building.rooms).selectinload(Room.room_type))
            .where(Building.id == building_id)
        )

        result = await self.session.execute(stmt)
        building = result.scalar_one_or_none()

        if not building:
            return None

        return {
            "id": str(building.id),
            "code": building.code,
            "name": building.name,
            "is_active": building.is_active,
            "rooms": [
                {
                    "id": str(room.id),
                    "code": room.code,
                    "name": room.name,
                    "capacity": room.capacity,
                    "exam_capacity": room.exam_capacity or room.capacity,
                    "floor_number": room.floor_number,
                    "room_type_name": room.room_type.name if room.room_type else None,
                    "has_projector": room.has_projector,
                    "has_ac": room.has_ac,
                    "has_computers": room.has_computers,
                    "overbookable": room.overbookable,
                    "max_inv_per_room": room.max_inv_per_room,
                    "adjacency_pairs": room.adjacency_pairs,
                    "is_active": room.is_active,
                }
                for room in building.rooms
            ],
            "created_at": (
                cast(ddatetime, building.created_at).isoformat()
                if building.created_at
                else None
            ),
            "updated_at": (
                cast(ddatetime, building.updated_at).isoformat()
                if building.updated_at
                else None
            ),
        }

    # Room Types
    async def get_all_room_types(self) -> List[Dict]:
        """Get all room types with room counts"""
        stmt = (
            select(RoomType)
            .options(selectinload(RoomType.rooms))
            .order_by(RoomType.name)
        )

        result = await self.session.execute(stmt)
        room_types = result.scalars().all()

        return [
            {
                "id": str(room_type.id),
                "name": room_type.name,
                "description": room_type.description,
                "is_active": room_type.is_active,
                "room_count": len(room_type.rooms),
                "active_room_count": len([r for r in room_type.rooms if r.is_active]),
            }
            for room_type in room_types
        ]

    async def get_active_room_types(self) -> List[Dict]:
        """Get only active room types"""
        stmt = select(RoomType).where(RoomType.is_active).order_by(RoomType.name)
        result = await self.session.execute(stmt)
        room_types = result.scalars().all()

        return [
            {
                "id": str(room_type.id),
                "name": room_type.name,
                "description": room_type.description,
            }
            for room_type in room_types
        ]

    # Rooms
    async def get_all_rooms(self) -> List[Dict]:
        """Get all rooms with building and type information"""
        stmt = (
            select(Room)
            .options(selectinload(Room.building), selectinload(Room.room_type))
            .order_by(Room.code)
        )

        result = await self.session.execute(stmt)
        rooms = result.scalars().all()

        return [
            {
                "id": str(room.id),
                "code": room.code,
                "name": room.name,
                "building_id": str(room.building_id),
                "building_name": room.building.name if room.building else None,
                "building_code": room.building.code if room.building else None,
                "room_type_id": str(room.room_type_id) if room.room_type_id else None,
                "room_type_name": room.room_type.name if room.room_type else None,
                "capacity": room.capacity,
                "exam_capacity": room.exam_capacity or room.capacity,
                "floor_number": room.floor_number,
                "has_projector": room.has_projector,
                "has_ac": room.has_ac,
                "has_computers": room.has_computers,
                "accessibility_features": room.accessibility_features or [],
                "overbookable": room.overbookable,
                "max_inv_per_room": room.max_inv_per_room,
                "adjacency_pairs": room.adjacency_pairs,
                "is_active": room.is_active,
                "notes": room.notes,
                "created_at": (
                    cast(ddatetime, room.created_at).isoformat()
                    if room.created_at
                    else None
                ),
                "updated_at": (
                    cast(ddatetime, room.updated_at).isoformat()
                    if room.updated_at
                    else None
                ),
            }
            for room in rooms
        ]

    async def get_active_rooms(self) -> List[Dict]:
        """Get only active rooms"""
        stmt = (
            select(Room)
            .options(selectinload(Room.building), selectinload(Room.room_type))
            .where(Room.is_active)
            .order_by(Room.code)
        )

        result = await self.session.execute(stmt)
        rooms = result.scalars().all()

        return [
            {
                "id": str(room.id),
                "code": room.code,
                "name": room.name,
                "building_name": room.building.name if room.building else None,
                "room_type_name": room.room_type.name if room.room_type else None,
                "capacity": room.capacity,
                "exam_capacity": room.exam_capacity or room.capacity,
                "floor_number": room.floor_number,
                "has_projector": room.has_projector,
                "has_ac": room.has_ac,
                "has_computers": room.has_computers,
                "accessibility_features": room.accessibility_features or [],
                "overbookable": room.overbookable,
                "max_inv_per_room": room.max_inv_per_room,
                "adjacency_pairs": room.adjacency_pairs,
            }
            for room in rooms
        ]

    async def get_rooms_by_building(self, building_id: UUID) -> List[Dict]:
        """Get rooms by building ID"""
        stmt = (
            select(Room)
            .options(selectinload(Room.room_type))
            .where(Room.building_id == building_id)
            .order_by(Room.code)
        )

        result = await self.session.execute(stmt)
        rooms = result.scalars().all()

        return [
            {
                "id": str(room.id),
                "code": room.code,
                "name": room.name,
                "room_type_name": room.room_type.name if room.room_type else None,
                "capacity": room.capacity,
                "exam_capacity": room.exam_capacity or room.capacity,
                "floor_number": room.floor_number,
                "has_projector": room.has_projector,
                "has_ac": room.has_ac,
                "has_computers": room.has_computers,
                "accessibility_features": room.accessibility_features or [],
                "overbookable": room.overbookable,
                "max_inv_per_room": room.max_inv_per_room,
                "adjacency_pairs": room.adjacency_pairs,
                "is_active": room.is_active,
                "notes": room.notes,
            }
            for room in rooms
        ]

    async def get_rooms_by_type(self, room_type_id: UUID) -> List[Dict]:
        """Get rooms by room type ID"""
        stmt = (
            select(Room)
            .options(selectinload(Room.building))
            .where(Room.room_type_id == room_type_id)
            .order_by(Room.code)
        )

        result = await self.session.execute(stmt)
        rooms = result.scalars().all()

        return [
            {
                "id": str(room.id),
                "code": room.code,
                "name": room.name,
                "building_name": room.building.name if room.building else None,
                "capacity": room.capacity,
                "exam_capacity": room.exam_capacity or room.capacity,
                "floor_number": room.floor_number,
                "has_projector": room.has_projector,
                "has_ac": room.has_ac,
                "has_computers": room.has_computers,
                "overbookable": room.overbookable,
                "max_inv_per_room": room.max_inv_per_room,
                "is_active": room.is_active,
            }
            for room in rooms
        ]

    async def get_room_by_id(self, room_id: UUID) -> Optional[Dict]:
        """Get room by ID with complete information"""
        stmt = (
            select(Room)
            .options(
                selectinload(Room.building),
                selectinload(Room.room_type),
                selectinload(Room.exam_rooms),
                selectinload(Room.allowed_exams),
            )
            .where(Room.id == room_id)
        )

        result = await self.session.execute(stmt)
        room = result.scalar_one_or_none()

        if not room:
            return None

        return {
            "id": str(room.id),
            "code": room.code,
            "name": room.name,
            "building_id": str(room.building_id),
            "building_name": room.building.name if room.building else None,
            "building_code": room.building.code if room.building else None,
            "room_type_id": str(room.room_type_id) if room.room_type_id else None,
            "room_type_name": room.room_type.name if room.room_type else None,
            "capacity": room.capacity,
            "exam_capacity": room.exam_capacity or room.capacity,
            "floor_number": room.floor_number,
            "has_projector": room.has_projector,
            "has_ac": room.has_ac,
            "has_computers": room.has_computers,
            "accessibility_features": room.accessibility_features or [],
            "overbookable": room.overbookable,
            "max_inv_per_room": room.max_inv_per_room,
            "adjacency_pairs": room.adjacency_pairs,
            "is_active": room.is_active,
            "notes": room.notes,
            "exam_assignment_count": len(room.exam_rooms),
            "allowed_exam_count": len(room.allowed_exams),
            "created_at": (
                cast(ddatetime, room.created_at).isoformat()
                if room.created_at
                else None
            ),
            "updated_at": (
                cast(ddatetime, room.updated_at).isoformat()
                if room.updated_at
                else None
            ),
        }

    # Room filtering and search
    async def get_rooms_with_features(
        self,
        has_projector: Optional[bool] = None,
        has_ac: Optional[bool] = None,
        has_computers: Optional[bool] = None,
        min_capacity: Optional[int] = None,
        building_id: Optional[UUID] = None,
        overbookable: Optional[bool] = None,
    ) -> List[Dict]:
        """Get rooms with specific features"""
        stmt = (
            select(Room)
            .options(selectinload(Room.building), selectinload(Room.room_type))
            .where(Room.is_active)
        )

        if has_projector is not None:
            stmt = stmt.where(Room.has_projector == has_projector)
        if has_ac is not None:
            stmt = stmt.where(Room.has_ac == has_ac)
        if has_computers is not None:
            stmt = stmt.where(Room.has_computers == has_computers)
        if min_capacity is not None:
            stmt = stmt.where(Room.exam_capacity >= min_capacity)
        if building_id is not None:
            stmt = stmt.where(Room.building_id == building_id)
        if overbookable is not None:
            stmt = stmt.where(Room.overbookable == overbookable)

        stmt = stmt.order_by(Room.capacity.desc())

        result = await self.session.execute(stmt)
        rooms = result.scalars().all()

        return [
            {
                "id": str(room.id),
                "code": room.code,
                "name": room.name,
                "building_name": room.building.name if room.building else None,
                "room_type_name": room.room_type.name if room.room_type else None,
                "capacity": room.capacity,
                "exam_capacity": room.exam_capacity or room.capacity,
                "has_projector": room.has_projector,
                "has_ac": room.has_ac,
                "has_computers": room.has_computers,
                "accessibility_features": room.accessibility_features or [],
                "overbookable": room.overbookable,
                "max_inv_per_room": room.max_inv_per_room,
                "adjacency_pairs": room.adjacency_pairs,
            }
            for room in rooms
        ]

    async def search_rooms(self, search_term: str) -> List[Dict]:
        """Search rooms by code or name"""
        search_pattern = f"%{search_term}%"
        stmt = (
            select(Room)
            .options(selectinload(Room.building), selectinload(Room.room_type))
            .where(
                and_(
                    Room.is_active,
                    or_(
                        Room.code.ilike(search_pattern), Room.name.ilike(search_pattern)
                    ),
                )
            )
            .order_by(Room.code)
        )

        result = await self.session.execute(stmt)
        rooms = result.scalars().all()

        return [
            {
                "id": str(room.id),
                "code": room.code,
                "name": room.name,
                "building_name": room.building.name if room.building else None,
                "room_type_name": room.room_type.name if room.room_type else None,
                "capacity": room.capacity,
                "exam_capacity": room.exam_capacity or room.capacity,
                "overbookable": room.overbookable,
                "max_inv_per_room": room.max_inv_per_room,
            }
            for room in rooms
        ]

    # Exam Room Assignments
    async def get_exam_room_assignments(
        self, exam_id: Optional[UUID] = None, room_id: Optional[UUID] = None
    ) -> List[Dict]:
        """Get exam room assignments with filters"""
        stmt = select(ExamRoom).options(
            selectinload(ExamRoom.exam),
            selectinload(ExamRoom.room).selectinload(Room.building),
        )

        if exam_id is not None:
            stmt = stmt.where(ExamRoom.exam_id == exam_id)
        if room_id is not None:
            stmt = stmt.where(ExamRoom.room_id == room_id)

        result = await self.session.execute(stmt)
        assignments = result.scalars().all()

        return [
            {
                "id": str(assignment.id),
                "exam_id": str(assignment.exam_id),
                "room_id": str(assignment.room_id),
                "room_code": assignment.room.code if assignment.room else None,
                "room_name": assignment.room.name if assignment.room else None,
                "building_name": (
                    assignment.room.building.name
                    if assignment.room and assignment.room.building
                    else None
                ),
                "allocated_capacity": assignment.allocated_capacity,
                "is_primary": assignment.is_primary,
                "seating_arrangement": assignment.seating_arrangement,
            }
            for assignment in assignments
        ]

    # Exam Allowed Rooms
    async def get_exam_allowed_rooms(
        self, exam_id: Optional[UUID] = None, room_id: Optional[UUID] = None
    ) -> List[Dict]:
        """Get exam allowed room assignments with filters"""
        stmt = select(ExamAllowedRoom).options(
            selectinload(ExamAllowedRoom.exam),
            selectinload(ExamAllowedRoom.room).selectinload(Room.building),
        )

        if exam_id is not None:
            stmt = stmt.where(ExamAllowedRoom.exam_id == exam_id)
        if room_id is not None:
            stmt = stmt.where(ExamAllowedRoom.room_id == room_id)

        result = await self.session.execute(stmt)
        assignments = result.scalars().all()

        return [
            {
                "exam_id": str(assignment.exam_id),
                "room_id": str(assignment.room_id),
                "room_code": assignment.room.code if assignment.room else None,
                "room_name": assignment.room.name if assignment.room else None,
                "building_name": (
                    assignment.room.building.name
                    if assignment.room and assignment.room.building
                    else None
                ),
                "exam_code": (
                    assignment.exam.course.code
                    if assignment.exam and assignment.exam.course
                    else None
                ),
            }
            for assignment in assignments
        ]

    # Statistics and utilization
    async def get_building_statistics(self) -> List[Dict]:
        stmt = (
            select(
                Building.id,
                Building.name,
                Building.code,
                func.count(Room.id).label("total_rooms"),
                func.count(func.nullif(Room.is_active, False)).label("active_rooms"),
                func.sum(case((Room.is_active, Room.capacity), else_=0)).label(
                    "total_capacity"
                ),
                func.sum(
                    case(
                        (
                            Room.is_active,
                            func.coalesce(Room.exam_capacity, Room.capacity),
                        ),
                        else_=0,
                    )
                ).label("total_exam_capacity"),
                func.count(
                    func.nullif(Room.overbookable & Room.is_active, False)
                ).label("overbookable_rooms"),
                func.avg(
                    case((Room.is_active, Room.max_inv_per_room), else_=None)
                ).label("avg_max_inv_per_room"),
            )
            .outerjoin(Room, Room.building_id == Building.id)
            .group_by(Building.id, Building.name, Building.code)
            .order_by(Building.name)
        )

        result = await self.session.execute(stmt)
        stats = result.all()

        return [
            {
                "building_id": str(stat.id),
                "building_name": stat.name,
                "building_code": stat.code,
                "total_rooms": stat.total_rooms or 0,
                "active_rooms": stat.active_rooms or 0,
                "total_capacity": int(stat.total_capacity or 0),
                "total_exam_capacity": int(stat.total_exam_capacity or 0),
                "overbookable_rooms": stat.overbookable_rooms or 0,
                "avg_max_inv_per_room": float(stat.avg_max_inv_per_room or 0),
            }
            for stat in stats
        ]

    async def get_room_type_statistics(self) -> List[Dict]:
        stmt = (
            select(
                RoomType.id,
                RoomType.name,
                func.count(Room.id).label("total_rooms"),
                func.count(func.nullif(Room.is_active, False)).label("active_rooms"),
                func.avg(case((Room.is_active, Room.capacity), else_=None)).label(
                    "avg_capacity"
                ),
                func.sum(case((Room.is_active, Room.capacity), else_=0)).label(
                    "total_capacity"
                ),
                func.count(
                    func.nullif(Room.overbookable & Room.is_active, False)
                ).label("overbookable_count"),
            )
            .outerjoin(Room, Room.room_type_id == RoomType.id)
            .group_by(RoomType.id, RoomType.name)
            .order_by(RoomType.name)
        )

        result = await self.session.execute(stmt)
        stats = result.all()

        return [
            {
                "room_type_id": str(stat.id),
                "room_type_name": stat.name,
                "total_rooms": stat.total_rooms or 0,
                "active_rooms": stat.active_rooms or 0,
                "average_capacity": float(stat.avg_capacity or 0),
                "total_capacity": int(stat.total_capacity or 0),
                "overbookable_count": stat.overbookable_count or 0,
            }
            for stat in stats
        ]

    async def get_room_utilization_summary(self) -> Dict:
        total_stmt = select(
            func.count(Room.id).label("total_rooms"),
            func.count(func.nullif(Room.is_active, False)).label("active_rooms"),
            func.sum(case((Room.is_active, Room.capacity), else_=0)).label(
                "total_capacity"
            ),
            func.sum(
                case(
                    (Room.is_active, func.coalesce(Room.exam_capacity, Room.capacity)),
                    else_=0,
                )
            ).label("total_exam_capacity"),
        )

        total_result = await self.session.execute(total_stmt)
        totals = total_result.first()

        features_stmt = select(
            func.count(func.nullif(Room.has_projector & Room.is_active, False)).label(
                "with_projector"
            ),
            func.count(func.nullif(Room.has_ac & Room.is_active, False)).label(
                "with_ac"
            ),
            func.count(func.nullif(Room.has_computers & Room.is_active, False)).label(
                "with_computers"
            ),
            func.count(func.nullif(Room.overbookable & Room.is_active, False)).label(
                "overbookable"
            ),
        )

        features_result = await self.session.execute(features_stmt)
        features = features_result.first()

        total_rooms = totals.total_rooms if totals else 0
        active_rooms = totals.active_rooms if totals else 0
        total_capacity = totals.total_capacity if totals else 0
        total_exam_capacity = totals.total_exam_capacity if totals else 0

        with_projector = features.with_projector if features else 0
        with_ac = features.with_ac if features else 0
        with_computers = features.with_computers if features else 0
        overbookable = features.overbookable if features else 0

        return {
            "total_rooms": total_rooms,
            "active_rooms": active_rooms,
            "inactive_rooms": total_rooms - active_rooms,
            "total_capacity": int(total_capacity),
            "total_exam_capacity": int(total_exam_capacity),
            "rooms_with_projector": with_projector,
            "rooms_with_ac": with_ac,
            "rooms_with_computers": with_computers,
            "overbookable_rooms": overbookable,
        }
