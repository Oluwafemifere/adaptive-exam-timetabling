# backend/app/services/scheduling/versioning_and_edit_service.py

from __future__ import annotations

from typing import Dict, List, Optional, Any, cast
from uuid import UUID, uuid4
from dataclasses import dataclass
from datetime import datetime
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

# Import tracking mixin
from ..tracking_mixin import TrackingMixin

from ...services.data_retrieval import TimetableEditData, JobData, AuditData
from ...models.timetable_edits import TimetableEdit
from ...models.versioning import TimetableVersion
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
    edit_id: Optional[UUID] = None  # Auto-generate edit ID
    edit_metadata: Optional[Dict[str, Any]] = None  # For tracking

    def __post_init__(self):
        if self.edit_id is None:
            self.edit_id = uuid4()
        if self.edit_metadata is None:
            self.edit_metadata = {}


class VersioningAndEditService(TrackingMixin):
    """
    Enhanced service that applies and validates timetable edits and manages approvals for versions
    with comprehensive tracking of all edit and versioning operations.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.session = session
        self.edit_data = TimetableEditData(session)
        self.job_data = JobData(session)
        self.audit_data = AuditData(session)

    async def propose_edit(self, user_id: UUID, edit: ProposedEdit) -> UUID:
        """Propose a new timetable edit with comprehensive tracking."""

        proposal_action = self._start_action(
            "edit_proposal",
            f"Proposing {edit.edit_type} edit for exam {edit.exam_id}",
            metadata={
                "edit_id": str(edit.edit_id),
                "edit_type": edit.edit_type,
                "user_id": str(user_id),
                "version_id": str(edit.version_id),
                "exam_id": str(edit.exam_id),
            },
        )

        try:
            await self._log_operation(
                "edit_proposal_started",
                {
                    "edit_id": str(edit.edit_id),
                    "edit_type": edit.edit_type,
                    "proposed_by": str(user_id),
                },
            )

            # Validation phase
            validation_action = self._start_action(
                "edit_validation", "Validating proposed edit"
            )

            # Basic validation
            validation_errors = []
            if not edit.version_id:
                validation_errors.append("Version ID is required")
            if not edit.exam_id:
                validation_errors.append("Exam ID is required")
            if not edit.edit_type:
                validation_errors.append("Edit type is required")

            if validation_errors:
                self._end_action(
                    validation_action, "failed", {"errors": validation_errors}
                )
                raise ValueError(
                    f"Edit validation failed: {', '.join(validation_errors)}"
                )

            self._end_action(validation_action, "completed")

            # Update edit metadata with tracking info
            assert edit.edit_metadata
            edit.edit_metadata.update(
                {
                    "proposed_at": datetime.utcnow().isoformat(),
                    "proposed_by": str(user_id),
                    "tracking_context": self._get_current_context(),
                    "validation_status": "pending",
                }
            )

            # Create database record
            db_action = self._start_action(
                "database_record_creation", "Creating edit database record"
            )

            rec = TimetableEdit(
                id=edit.edit_id,  # Use our generated ID
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

            # Create audit log
            audit_log = AuditLog(
                user_id=user_id,
                action="timetable_edit_proposed",
                entity_type="timetable_version",
                entity_id=edit.version_id,
                new_values={
                    "edit_id": str(edit.edit_id),
                    "edit_type": edit.edit_type,
                    "exam_id": str(edit.exam_id),
                    "reason": edit.reason,
                    "tracking_context": self._get_current_context(),
                },
                notes=f"Edit proposed for exam {edit.exam_id} of type {edit.edit_type}",
            )

            self.session.add(audit_log)
            await self.session.commit()

            self._end_action(db_action, "completed")

            self._end_action(
                proposal_action,
                "completed",
                {"edit_created": str(edit.edit_id), "database_persisted": True},
            )

            await self._log_operation(
                "edit_proposed",
                {
                    "edit_id": str(edit.edit_id),
                    "edit_summary": {
                        "type": edit.edit_type,
                        "exam_id": str(edit.exam_id),
                        "version_id": str(edit.version_id),
                        "has_reason": bool(edit.reason),
                    },
                },
            )

            return rec.id

        except Exception as e:
            await self.session.rollback()
            self._end_action(proposal_action, "failed", {"error": str(e)})
            await self._log_operation(
                "edit_proposal_failed", {"error": str(e)}, "ERROR"
            )
            logger.exception("Failed to propose edit")
            raise

    async def validate_edit(self, edit_id: UUID) -> Dict[str, Any]:
        """Validate a proposed edit with comprehensive tracking."""

        validation_action = self._start_action(
            "edit_validation_comprehensive",
            f"Comprehensively validating edit {edit_id}",
            metadata={"edit_id": str(edit_id)},
        )

        try:
            await self._log_operation(
                "edit_validation_started", {"edit_id": str(edit_id)}
            )

            # Retrieve edit data
            retrieval_action = self._start_action(
                "edit_data_retrieval", "Retrieving edit data for validation"
            )

            edit_raw: Any = await self.edit_data.get_edit_by_id(edit_id)
            edit_rec = cast(Optional[Dict[str, Any]], edit_raw)

            if not edit_rec:
                self._end_action(
                    retrieval_action, "failed", {"reason": "edit_not_found"}
                )
                return {"valid": False, "errors": ["Edit not found"]}

            self._end_action(retrieval_action, "completed")

            # Field validation
            field_validation_action = self._start_action(
                "field_validation", "Validating edit fields"
            )

            nv = cast(Dict[str, Any], edit_rec.get("new_values") or {})
            errors: List[str] = []
            warnings: List[str] = []

            if not isinstance(nv, dict):
                errors.append("new_values must be a mapping")
                await self._set_validation_status(edit_id, "rejected")
                self._end_action(
                    field_validation_action,
                    "failed",
                    {"issue": "invalid_new_values_format"},
                )
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

            self._end_action(
                field_validation_action,
                "completed",
                {
                    "fields_validated": len(nv),
                    "errors_found": len(errors),
                    "warnings_found": len(warnings),
                },
            )

            # Set validation status
            status_action = self._start_action(
                "validation_status_update", "Updating validation status"
            )

            status = "validated" if not errors else "rejected"
            await self._set_validation_status(edit_id, status)

            self._end_action(status_action, "completed", {"final_status": status})

            validation_result = {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "validation_metadata": {
                    "validated_at": datetime.utcnow().isoformat(),
                    "fields_count": len(nv),
                    "tracking_context": self._get_current_context(),
                },
            }

            self._end_action(
                validation_action,
                "completed",
                {
                    "validation_passed": validation_result["valid"],
                    "total_issues": len(errors) + len(warnings),
                },
            )

            await self._log_operation(
                "edit_validation_completed",
                {
                    "edit_id": str(edit_id),
                    "validation_result": {
                        "valid": validation_result["valid"],
                        "errors_count": len(errors),
                        "warnings_count": len(warnings),
                    },
                },
            )

            return validation_result

        except Exception as e:
            self._end_action(validation_action, "failed", {"error": str(e)})
            await self._log_operation(
                "edit_validation_failed", {"error": str(e)}, "ERROR"
            )
            logger.exception("Failed to validate edit %s", edit_id)
            return {"valid": False, "errors": [f"Validation failed for {edit_id}"]}

    async def apply_validated_edits(
        self, version_id: UUID, user_id: UUID
    ) -> Dict[str, Any]:
        """Apply all validated edits for a version with comprehensive tracking."""

        application_action = self._start_action(
            "validated_edits_application",
            f"Applying validated edits for version {version_id}",
            metadata={"version_id": str(version_id), "user_id": str(user_id)},
        )

        try:
            await self._log_operation(
                "edit_application_started",
                {"version_id": str(version_id), "applied_by": str(user_id)},
            )

            # Retrieve edits
            retrieval_action = self._start_action(
                "edits_retrieval", "Retrieving validated edits"
            )

            edits_raw: Any = await self.edit_data.get_edits_by_version(version_id)
            edits = cast(List[Dict[str, Any]], edits_raw)

            self._end_action(
                retrieval_action, "completed", {"edits_retrieved": len(edits)}
            )

            # Apply each edit
            applied = 0
            skipped = 0
            edit_results = []

            for edit_idx, e in enumerate(edits):
                edit_application_action = self._start_action(
                    "single_edit_application",
                    f"Applying edit {edit_idx + 1}/{len(edits)}",
                    metadata={"edit_index": edit_idx},
                )

                status_val = e.get("validation_status")
                edit_id_val = e.get("id")

                if status_val != "validated":
                    skipped += 1
                    edit_results.append(
                        {
                            "edit_id": str(edit_id_val) if edit_id_val else "unknown",
                            "status": "skipped",
                            "reason": f"invalid_status_{status_val}",
                        }
                    )
                    self._end_action(
                        edit_application_action,
                        "skipped",
                        {"reason": f"status_{status_val}"},
                    )
                    continue

                if not edit_id_val:
                    logger.warning("Edit record missing id; skipping")
                    skipped += 1
                    edit_results.append(
                        {
                            "edit_id": "missing",
                            "status": "skipped",
                            "reason": "missing_id",
                        }
                    )
                    self._end_action(
                        edit_application_action, "skipped", {"reason": "missing_id"}
                    )
                    continue

                await self._set_validation_status(UUID(str(edit_id_val)), "applied")
                applied += 1
                edit_results.append(
                    {
                        "edit_id": str(edit_id_val),
                        "status": "applied",
                        "applied_at": datetime.utcnow().isoformat(),
                    }
                )

                self._end_action(edit_application_action, "completed")

            # Create audit log
            audit_action = self._start_action(
                "audit_logging", "Creating audit log for applied edits"
            )

            audit_log = AuditLog(
                user_id=user_id,
                action="timetable_edits_applied",
                entity_type="timetable_version",
                entity_id=version_id,
                new_values={
                    "applied_edits": applied,
                    "skipped_edits": skipped,
                    "edit_results": edit_results,
                    "tracking_context": self._get_current_context(),
                },
                notes=f"Applied {applied} edits, skipped {skipped}",
            )

            self.session.add(audit_log)
            await self.session.commit()

            self._end_action(audit_action, "completed")

            application_result = {
                "applied": applied,
                "skipped": skipped,
                "edit_details": edit_results,
                "application_metadata": {
                    "applied_at": datetime.utcnow().isoformat(),
                    "applied_by": str(user_id),
                    "version_id": str(version_id),
                    "tracking_context": self._get_current_context(),
                },
            }

            self._end_action(
                application_action,
                "completed",
                {
                    "edits_applied": applied,
                    "edits_skipped": skipped,
                    "success_rate": (applied / len(edits) * 100) if edits else 0,
                },
            )

            await self._log_operation(
                "edits_applied",
                {
                    "version_id": str(version_id),
                    "application_summary": {
                        "applied": applied,
                        "skipped": skipped,
                        "total_processed": len(edits),
                    },
                },
            )

            return application_result

        except Exception as e:
            await self.session.rollback()
            self._end_action(application_action, "failed", {"error": str(e)})
            await self._log_operation(
                "edit_application_failed", {"error": str(e)}, "ERROR"
            )
            logger.exception("Failed to apply validated edits")
            raise

    async def approve_version(
        self, version_id: UUID, approver_id: UUID, activate: bool = True
    ) -> Dict[str, Any]:
        """Approve a timetable version with comprehensive tracking."""

        approval_action = self._start_action(
            "version_approval",
            f"Approving version {version_id} (activate: {activate})",
            metadata={
                "version_id": str(version_id),
                "approver_id": str(approver_id),
                "activate": activate,
            },
        )

        try:
            await self._log_operation(
                "version_approval_started",
                {
                    "version_id": str(version_id),
                    "approver_id": str(approver_id),
                    "will_activate": activate,
                },
            )

            # Update version status
            update_action = self._start_action(
                "version_status_update", "Updating version approval status"
            )

            approval_timestamp = datetime.utcnow()

            await self.session.execute(
                update(TimetableVersion)
                .where(TimetableVersion.id == version_id)
                .values(
                    approved_by=approver_id,
                    approved_at=approval_timestamp,
                    is_active=activate,
                )
            )

            self._end_action(update_action, "completed")

            # Create audit log
            audit_action = self._start_action(
                "approval_audit_logging", "Creating approval audit log"
            )

            audit_log = AuditLog(
                user_id=approver_id,
                action="timetable_version_approved",
                entity_type="timetable_version",
                entity_id=version_id,
                new_values={
                    "is_active": activate,
                    "approved_at": approval_timestamp.isoformat(),
                    "tracking_context": self._get_current_context(),
                },
                notes=f"Version approved; activated={activate}",
            )

            self.session.add(audit_log)
            await self.session.commit()

            self._end_action(audit_action, "completed")

            approval_result = {
                "approved": True,
                "activated": activate,
                "approval_metadata": {
                    "approved_by": str(approver_id),
                    "approved_at": approval_timestamp.isoformat(),
                    "version_id": str(version_id),
                    "tracking_context": self._get_current_context(),
                },
            }

            self._end_action(
                approval_action,
                "completed",
                {"version_approved": str(version_id), "version_activated": activate},
            )

            await self._log_operation(
                "version_approved",
                {"version_id": str(version_id), "approval_summary": approval_result},
            )

            return approval_result

        except Exception as e:
            await self.session.rollback()
            self._end_action(approval_action, "failed", {"error": str(e)})
            await self._log_operation(
                "version_approval_failed", {"error": str(e)}, "ERROR"
            )
            logger.exception("Failed to approve version %s", version_id)
            raise

    async def _set_validation_status(self, edit_id: UUID, status: str) -> None:
        """Set validation status for an edit with action tracking."""

        status_action = self._start_action(
            "validation_status_setting", f"Setting status to {status}"
        )

        try:
            await self.session.execute(
                update(TimetableEdit)
                .where(TimetableEdit.id == edit_id)
                .values(validation_status=status)
            )

            await self.session.commit()
            self._end_action(status_action, "completed")

        except Exception as e:
            await self.session.rollback()
            self._end_action(status_action, "failed", {"error": str(e)})
            logger.exception("Failed to set validation status")
            raise

    def get_versioning_tracking_info(
        self, version_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get comprehensive tracking information for versioning and edit operations."""
        return {
            "version_id": str(version_id) if version_id else None,
            "current_context": self._get_current_context(),
            "versioning_history": [
                {
                    "action_id": str(action["action_id"]),
                    "action_type": action["action_type"],
                    "description": action["description"],
                    "metadata": action.get("metadata", {}),
                    "status": action.get("status", "active"),
                    "duration_ms": action.get("duration_ms", 0),
                }
                for action in self._action_stack
            ],
        }
