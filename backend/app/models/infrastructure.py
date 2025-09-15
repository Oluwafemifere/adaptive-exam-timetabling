# app/models/infrastructure.py
import uuid
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, Integer, ForeignKey, ARRAY, Text, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .scheduling import Exam


class Building(Base, TimestampMixin):
    __tablename__ = "buildings"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    rooms: Mapped[List["Room"]] = relationship(back_populates="building")


class RoomType(Base):
    __tablename__ = "room_types"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

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
    exam_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    floor_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_ac: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_projector: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_computers: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    accessibility_features: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # NEW FIELDS
    overbookable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_inv_per_room: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    adjacency_pairs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    building: Mapped["Building"] = relationship(back_populates="rooms")
    room_type: Mapped["RoomType"] = relationship(back_populates="rooms")
    exam_rooms: Mapped[List["ExamRoom"]] = relationship(back_populates="room")
    allowed_exams: Mapped[List["ExamAllowedRoom"]] = relationship(back_populates="room")


class ExamAllowedRoom(Base):
    __tablename__ = "exam_allowed_rooms"

    exam_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("exams.id"), primary_key=True
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("rooms.id"), primary_key=True
    )

    exam: Mapped["Exam"] = relationship(back_populates="allowed_rooms")
    room: Mapped["Room"] = relationship(back_populates="allowed_exams")


class ExamRoom(Base):
    __tablename__ = "exam_rooms"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("exams.id"), nullable=False
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False
    )
    allocated_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    seating_arrangement: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    exam: Mapped["Exam"] = relationship(back_populates="exam_rooms")
    room: Mapped["Room"] = relationship(back_populates="exam_rooms")
