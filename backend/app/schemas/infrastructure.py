# backend/app/schemas/infrastructure.py
from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from uuid import UUID

MODEL_CONFIG = ConfigDict(from_attributes=True)


class RoomBase(BaseModel):
    model_config = MODEL_CONFIG

    code: str
    name: str
    building_id: UUID
    room_type_id: UUID
    capacity: int
    exam_capacity: Optional[int] = None
    floor_number: Optional[int] = None
    has_ac: bool = False
    has_projector: bool = False
    has_computers: bool = False
    accessibility_features: Optional[List[str]] = None
    is_active: bool = True
    overbookable: bool = False
    max_inv_per_room: int = 50
    adjacency_pairs: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class RoomCreate(RoomBase):
    pass


class RoomUpdate(BaseModel):
    model_config = MODEL_CONFIG

    code: Optional[str] = None
    name: Optional[str] = None
    building_id: Optional[UUID] = None
    room_type_id: Optional[UUID] = None
    capacity: Optional[int] = None
    exam_capacity: Optional[int] = None
    floor_number: Optional[int] = None
    has_ac: Optional[bool] = None
    has_projector: Optional[bool] = None
    has_computers: Optional[bool] = None
    accessibility_features: Optional[List[str]] = None
    is_active: Optional[bool] = None
    overbookable: Optional[bool] = None
    max_inv_per_room: Optional[int] = None
    adjacency_pairs: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class RoomRead(RoomBase):
    id: UUID
