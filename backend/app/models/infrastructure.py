# app/models/infrastructure.py

import uuid
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, Integer, ForeignKey, ARRAY, Text, Table, Column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.associationproxy import association_proxy, AssociationProxy
from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .scheduling import TimetableAssignment
    from .academic import Faculty, Department


# New association table for Room <-> Department
class RoomDepartment(Base):
    __tablename__ = "room_departments"
    room_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="CASCADE"),
        primary_key=True,
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="CASCADE"),
        primary_key=True,
    )


class Building(Base, TimestampMixin):
    __tablename__ = "buildings"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # New nullable foreign key to Faculty
    faculty_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("faculties.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    rooms: Mapped[List["Room"]] = relationship(back_populates="building")
    faculty: Mapped[Optional["Faculty"]] = relationship(back_populates="buildings")


class RoomType(Base):
    __tablename__ = "room_types"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rooms: Mapped[List["Room"]] = relationship(back_populates="room_type")


class Room(Base, TimestampMixin):
    __tablename__ = "rooms"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    building_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False
    )
    room_type_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("room_types.id"), nullable=False
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    exam_capacity: Mapped[int | None] = mapped_column(Integer)
    floor_number: Mapped[int | None] = mapped_column(Integer)
    has_ac: Mapped[bool] = mapped_column(Boolean, nullable=False)
    has_projector: Mapped[bool] = mapped_column(Boolean, nullable=False)
    has_computers: Mapped[bool] = mapped_column(Boolean, nullable=False)
    accessibility_features: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    overbookable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    max_inv_per_room: Mapped[int] = mapped_column(Integer, nullable=False)
    adjacency_pairs: Mapped[dict | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)

    building: Mapped["Building"] = relationship(back_populates="rooms")
    room_type: Mapped["RoomType"] = relationship(back_populates="rooms")
    timetable_assignments: Mapped[List["TimetableAssignment"]] = relationship(
        back_populates="room"
    )

    # New many-to-many relationship with Department
    department_associations: Mapped[List["RoomDepartment"]] = relationship()
    departments: AssociationProxy[List["Department"]] = association_proxy(
        "department_associations", "department"
    )
