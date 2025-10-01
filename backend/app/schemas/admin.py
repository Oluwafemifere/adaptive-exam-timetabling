# backend/app/schemas/admin.py
from typing import Dict, Any, List
from uuid import UUID
from pydantic import BaseModel


class SeedingRequest(BaseModel):
    validation_mode: bool = True


class UploadSessionCreate(BaseModel):
    session_id: UUID
    upload_type: str
    file_metadata: Dict[str, Any]


# --- NEWLY ADDED SCHEMA ---
class JsonSeedingRequest(BaseModel):
    entity_type: str
    data: List[Dict[str, Any]]
