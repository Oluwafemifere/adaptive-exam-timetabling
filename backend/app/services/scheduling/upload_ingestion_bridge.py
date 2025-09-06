# backend/app/services/scheduling/upload_ingestion_bridge.py

from __future__ import annotations

from typing import Dict, List, Optional, Any
from uuid import UUID
from dataclasses import dataclass
from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from ...services.data_retrieval import FileUploadData, AuditData, SchedulingData

logger = logging.getLogger(__name__)


@dataclass
class UploadIngestionSummary:
    upload_session_id: UUID
    upload_type: str
    status: str
    total_records: int
    processed_records: int
    errors: Optional[Dict[str, Any]]


class UploadIngestionBridge:
    """
    Surfaces upload sessions and provides hooks for converting validated uploads
    into domain entities used by scheduling services.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.file_upload_data = FileUploadData(session)
        self.audit_data = AuditData(session)
        self.scheduling_data = SchedulingData(session)

    async def list_recent_uploads(
        self, limit: int = 20
    ) -> List[UploadIngestionSummary]:
        sessions = await self.file_upload_data.get_recent_uploads(limit=limit)
        out: List[UploadIngestionSummary] = []
        for s in sessions:
            out.append(
                UploadIngestionSummary(
                    upload_session_id=UUID(s["id"]),
                    upload_type=str(s.get("upload_type")),
                    status=str(s.get("status")),
                    total_records=int(s.get("total_records") or 0),
                    processed_records=int(s.get("processed_records") or 0),
                    errors=s.get("validation_errors"),
                )
            )
        return out

    async def get_upload_detail(self, upload_session_id: UUID) -> Dict[str, Any]:
        detail = await self.file_upload_data.get_upload_session_by_id(upload_session_id)
        return detail or {}

    async def ready_for_ingestion(self, upload_session_id: UUID) -> bool:
        detail = await self.file_upload_data.get_upload_session_by_id(upload_session_id)
        if not detail:
            return False
        return detail.get("status") == "completed" and not detail.get(
            "validation_errors"
        )

    async def ingest_to_staging(self, upload_session_id: UUID) -> Dict[str, Any]:
        """
        Example placeholder for transforming uploaded rows to staging tables prior to being
        part of scheduling dataset (implementation will depend on the ingestion spec).
        """
        detail = await self.file_upload_data.get_upload_session_by_id(upload_session_id)
        if not detail:
            return {"success": False, "errors": ["Upload session not found"]}

        if detail.get("validation_errors"):
            return {"success": False, "errors": ["Upload contains validation errors"]}

        # No-op demo: record audit and return
        # Note: Actual ingestion would parse file rows and write to domain tables.
        logger.info("Ingestion simulated for upload session %s", upload_session_id)
        return {"success": True, "ingested_records": detail.get("total_records") or 0}
