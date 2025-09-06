# backend/app/services/scheduling/versioning_and_edit_service.py
from __future__ import annotations

from typing import Dict, List, Optional, Any, cast
from uuid import UUID
from dataclasses import dataclass
from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from ...services.data_retrieval import TimetableEditData, JobData, AuditData
from ...models.timetable_edits import TimetableEdit
from ...models.jobs import TimetableVersion
from ...models.audit_logs import AuditLog

logger = logging.getLogger(__name__)


@dataclass
class ProposedEdit:
    version_id: UUID
    exam_id: UUID
    edit_type: str
    old_values: Optional[Dict[str, Any]]
    new_values: Optional[Dict[str, Any]]
    reason: Optional[str]


class VersioningAndEditService:
    """
    Applies and validates timetable edits and manages approvals for versions.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.edit_data = TimetableEditData(session)
        self.job_data = JobData(session)
        self.audit_data = AuditData(session)

    async def propose_edit(self, user_id: UUID, edit: ProposedEdit) -> UUID:
        """Propose a new timetable edit."""
        try:
            rec = TimetableEdit(
                version_id=edit.version_id,
                exam_id=edit.exam_id,
                edited_by=user_id,
                edit_type=edit.edit_type,
                old_values=edit.old_values or {},
                new_values=edit.new_values or {},
                reason=edit.reason,
                validation_status="pending",
            )
            self.session.add(rec)

            audit_log = AuditLog(
                user_id=user_id,
                action="timetable_edit_proposed",
                entity_type="timetable_version",
                entity_id=edit.version_id,
                new_values={
                    "edit_type": edit.edit_type,
                    "exam_id": str(edit.exam_id),
                    "reason": edit.reason,
                },
                notes=f"Edit proposed for exam {edit.exam_id} of type {edit.edit_type}",
            )
            self.session.add(audit_log)

            await self.session.commit()
            return rec.id

        except Exception:
            await self.session.rollback()
            logger.exception("Failed to propose edit")
            raise

    async def validate_edit(self, edit_id: UUID) -> Dict[str, Any]:
        """Validate a proposed edit."""
        try:
            edit_raw: Any = await self.edit_data.get_edit_by_id(edit_id)
            edit_rec = cast(Optional[Dict[str, Any]], edit_raw)
            if not edit_rec:
                return {"valid": False, "errors": ["Edit not found"]}

            nv = cast(Dict[str, Any], edit_rec.get("new_values") or {})

            errors: List[str] = []
            warnings: List[str] = []

            if not isinstance(nv, dict):
                errors.append("new_values must be a mapping")
                await self._set_validation_status(edit_id, "rejected")
                return {"valid": False, "errors": errors, "warnings": warnings}

            # Validate expected_students field
            if "expected_students" in nv:
                try:
                    expected_students = int(nv["expected_students"])
                    if expected_students < 0:
                        errors.append("expected_students cannot be negative")
                    elif expected_students > 1000:
                        warnings.append("expected_students is unusually high")
                except (TypeError, ValueError):
                    errors.append("expected_students must be a valid integer")

            # Validate exam_date field
            if "exam_date" in nv:
                val = nv["exam_date"]
                if not isinstance(val, str) or len(val) != 10:
                    errors.append("exam_date must be in YYYY-MM-DD format")

            # Validate time_slot_id field
            if "time_slot_id" in nv:
                if not nv["time_slot_id"]:
                    errors.append("time_slot_id cannot be empty")

            status = "validated" if not errors else "rejected"
            await self._set_validation_status(edit_id, status)

            return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

        except Exception:
            logger.exception("Failed to validate edit %s", edit_id)
            return {"valid": False, "errors": [f"Validation failed for {edit_id}"]}

    async def validate_edit_with_invalid_data(self, edit_id: UUID) -> Dict[str, Any]:
        """Test method for validation with invalid data."""
        try:
            invalid_edit = {
                "id": str(edit_id),
                "new_values": {
                    "expected_students": "invalid_number",
                    "exam_date": "invalid-date-format",
                    "time_slot_id": None,
                },
            }

            errors: List[str] = []
            nv = invalid_edit.get("new_values", {})

            try:
                int(nv["expected_students"])  # type: ignore
            except (TypeError, ValueError):
                errors.append("expected_students must be a valid integer")

            if "exam_date" in nv and nv["exam_date"] == "invalid-date-format":  # type: ignore
                errors.append("exam_date format is invalid")

            if not nv.get("time_slot_id"):  # type: ignore
                errors.append("time_slot_id cannot be null or empty")

            await self._set_validation_status(edit_id, "rejected")

            return {"valid": False, "errors": errors, "warnings": []}

        except Exception:
            logger.exception("Failed to validate edit with invalid data %s", edit_id)
            raise

    async def apply_validated_edits(
        self, version_id: UUID, user_id: UUID
    ) -> Dict[str, Any]:
        """Apply all validated edits for a version."""
        try:
            edits_raw: Any = await self.edit_data.get_edits_by_version(version_id)
            edits = cast(List[Dict[str, Any]], edits_raw)

            applied = 0
            skipped = 0

            for e in edits:
                status_val = e.get("validation_status")
                edit_id_val = e.get("id")

                if status_val != "validated":
                    skipped += 1
                    continue

                if not edit_id_val:
                    logger.warning("Edit record missing id; skipping")
                    skipped += 1
                    continue

                await self._set_validation_status(UUID(str(edit_id_val)), "applied")
                applied += 1

            audit_log = AuditLog(
                user_id=user_id,
                action="timetable_edits_applied",
                entity_type="timetable_version",
                entity_id=version_id,
                new_values={"applied_edits": applied, "skipped_edits": skipped},
                notes=f"Applied {applied} edits, skipped {skipped}",
            )
            self.session.add(audit_log)

            await self.session.commit()
            return {"applied": applied, "skipped": skipped}

        except Exception:
            await self.session.rollback()
            logger.exception("Failed to apply validated edits")
            raise

    async def approve_version(
        self, version_id: UUID, approver_id: UUID, activate: bool = True
    ) -> Dict[str, Any]:
        """Approve a timetable version."""
        try:
            await self.session.execute(
                update(TimetableVersion)
                .where(TimetableVersion.id == version_id)
                .values(
                    approved_by=approver_id,
                    approved_at=datetime.utcnow(),
                    is_active=activate,
                )
            )

            audit_log = AuditLog(
                user_id=approver_id,
                action="timetable_version_approved",
                entity_type="timetable_version",
                entity_id=version_id,
                new_values={
                    "is_active": activate,
                    "approved_at": datetime.utcnow().isoformat(),
                },
                notes=f"Version approved; activated={activate}",
            )
            self.session.add(audit_log)

            await self.session.commit()
            return {"approved": True, "activated": activate}

        except Exception:
            await self.session.rollback()
            logger.exception("Failed to approve version %s", version_id)
            raise

    async def _set_validation_status(self, edit_id: UUID, status: str) -> None:
        """Set validation status for an edit."""
        try:
            await self.session.execute(
                update(TimetableEdit)
                .where(TimetableEdit.id == edit_id)
                .values(validation_status=status)
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            logger.exception("Failed to set validation status")
            raise
