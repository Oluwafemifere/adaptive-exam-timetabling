# backend/app/services/scheduling/timetable_job_orchestrator.py

from __future__ import annotations

from typing import Dict, List, Optional, Callable, Any, Set
from uuid import UUID, uuid4
from dataclasses import dataclass
from datetime import datetime
import logging
import json
import math
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

# Import the tracking mixin
from ..tracking_mixin import TrackingMixin

# Retrieval services and helpers
from ..data_retrieval import (
    JobData,
    ConstraintData,
    AuditData,
)
from ..job import JobService
from ..scheduling.data_preparation_service import ExactDataFlowService
from ..scheduling.room_allocation_service import RoomAllocationService
from ..scheduling.invigilator_assignment_service import (
    InvigilatorAssignmentService,
)

# Models
from ...models.jobs import TimetableJob
from ...models.versioning import TimetableVersion
from ...models.audit_logs import AuditLog

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorOptions:
    run_room_planning: bool = True
    run_invigilator_planning: bool = True
    activate_version: bool = False


def serialize_for_json(obj: Any, _seen_objects: Optional[Set[int]] = None) -> Any:
    """Convert objects to JSON-serializable format with circular reference detection"""
    if _seen_objects is None:
        _seen_objects = set()

    obj_id = id(obj)
    if obj_id in _seen_objects:
        return f"<circular_ref:{getattr(obj, 'id', 'unknown')}>"

    # Only add to seen objects if it's a complex type that might cause circular references
    if hasattr(obj, "__dict__") or isinstance(obj, (list, dict)):
        _seen_objects.add(obj_id)

    try:
        if isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, float):
            # Handle special float values
            if math.isinf(obj) or math.isnan(obj):
                return None
            return obj
        elif hasattr(obj, "__dict__"):
            return {
                k: serialize_for_json(v, _seen_objects)
                for k, v in obj.__dict__.items()
                if not k.startswith("_")
            }
        elif isinstance(obj, list):
            return [serialize_for_json(item, _seen_objects) for item in obj]
        elif isinstance(obj, dict):
            return {k: serialize_for_json(v, _seen_objects) for k, v in obj.items()}
        else:
            return obj
    finally:

        if obj_id in _seen_objects:
            _seen_objects.remove(obj_id)


class TimetableJobOrchestrator(TrackingMixin):
    """
    Enhanced orchestrator with automatic job, session, and action ID tracking.
    Orchestrates a scheduling job lifecycle:
    - Create job with automatic ID generation
    - Prepare dataset with action tracking
    - Call external solver with monitoring
    - Build room and invigilator plans with tracking
    - Persist result + versioning with audit trail
    - Emit audit events with full context
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)  # Initialize tracking mixin
        self.session = session
        self.job_data = JobData(session)
        self.job_service = JobService(session)
        self.constraint_data = ConstraintData(session)
        self.audit_data = AuditData(session)
        self.data_prep = ExactDataFlowService(session)
        self.room_alloc = RoomAllocationService(session)
        self.invig_alloc = InvigilatorAssignmentService(session)

    async def start_job(
        self,
        session_id: UUID,
        configuration_id: UUID,
        initiated_by: UUID,
        solver_callable: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        options: Optional[OrchestratorOptions] = None,
    ) -> UUID:
        """Start a new timetabling job with complete tracking."""

        # Create job with automatic ID generation
        job_id = self._generate_job_id()

        # Start main orchestration action
        orchestration_action = self._start_action(
            action_type="job_orchestration",
            description=f"Orchestrating timetable job for session {session_id}",
            metadata={"job_id": str(job_id)},
        )

        options = options or OrchestratorOptions()
        job = None

        try:
            # ✅ FIX: Verify configuration exists before creating job
            config_check_action = self._start_action(
                "configuration_verification", "Verifying configuration exists"
            )

            # Check if configuration exists
            from ...models.users import SystemConfiguration
            from sqlalchemy import select

            config_result = await self.session.execute(
                select(SystemConfiguration).where(
                    SystemConfiguration.id == configuration_id
                )
            )
            config_exists = config_result.scalar_one_or_none() is not None

            self._end_action(
                config_check_action, "completed", {"config_exists": config_exists}
            )

            if not config_exists:
                raise ValueError(
                    f"Configuration {configuration_id} not found in database"
                )

            # Create database job record
            job = TimetableJob(
                id=job_id,
                session_id=session_id,
                configuration_id=configuration_id,
                initiated_by=initiated_by,
                status="queued",
                progress_percentage=0,
                started_at=datetime.utcnow(),
            )

            self.session.add(job)
            await self.session.flush()

            # Log job creation
            await self._log_operation(
                "job_created",
                {
                    "job_id": str(job_id),
                    "session_id": str(session_id),
                    "configuration_id": str(configuration_id),
                },
            )

            # Audit create with action tracking
            audit_action = self._start_action("audit_log", "Recording job creation")
            self.session.add(
                AuditLog(
                    user_id=initiated_by,
                    action="job_created",
                    entity_type="timetable_job",
                    entity_id=job.id,
                    notes=f"Job created for session {session_id} with config {configuration_id}",
                )
            )
            await self.session.commit()
            self._end_action(audit_action, "completed")

            # Data preparation phase
            prep_action = self._start_action(
                "data_preparation",
                "Preparing dataset for scheduling",
                {"session_id": str(session_id)},
            )

            await self._update_job_status(job.id, "running", 5, "preparing")
            prepared = await self.data_prep.build_exact_problem_model_dataset(
                session_id
            )

            self._end_action(
                prep_action,
                "completed",
                {
                    "exams_count": len(prepared.exams),
                    "rooms_count": len(prepared.rooms),
                    "staff_count": len(prepared.staff),
                },
            )

            # Constraint processing
            constraint_action = self._start_action(
                "constraint_processing", "Processing configuration constraints"
            )

            conf_constraints = await self.constraint_data.get_configuration_constraints(
                configuration_id
            )

            solver_input = {
                "prepared_data": serialize_for_json(prepared),
                "constraints": conf_constraints,
                "options": vars(options),
                "tracking_context": self._get_current_context(),  # Include tracking context
            }

            self._end_action(constraint_action, "completed")

            # Solver execution
            solver_result: Dict[str, Any] = {}
            if solver_callable:
                solver_action = self._start_action(
                    "solver_execution", "Executing scheduling solver"
                )

                await self._update_job_status(job.id, "running", 25, "solving")
                try:
                    solver_result = solver_callable(solver_input) or {}
                    self._end_action(
                        solver_action, "completed", {"has_result": bool(solver_result)}
                    )
                except Exception as exc:
                    self._end_action(solver_action, "failed", {"error": str(exc)})
                    await self._update_job_error(job.id, f"Solver failed: {exc}")
                    self._end_action(orchestration_action, "failed")
                    return job.id

            # Room planning phase
            room_plan = None
            if options.run_room_planning:
                room_action = self._start_action(
                    "room_planning", "Planning room allocations"
                )

                await self._update_job_status(job.id, "running", 50, "room_planning")
                room_plan = await self.room_alloc.plan_room_allocations(session_id)
                plan_validation = await self.room_alloc.validate_room_plan(
                    room_plan, session_id
                )

                if plan_validation.get("errors"):
                    self._end_action(
                        room_action, "failed", {"errors": plan_validation["errors"]}
                    )
                    await self._update_job_error(
                        job.id, f"Room plan invalid: {plan_validation['errors']}"
                    )
                    self._end_action(orchestration_action, "failed")
                    return job.id

                self._end_action(
                    room_action,
                    "completed",
                    {
                        "proposals_count": len(room_plan),
                        "validation_warnings": plan_validation.get("warnings", []),
                    },
                )

            # Invigilator planning phase
            invig_plan = None
            if options.run_invigilator_planning:
                invig_action = self._start_action(
                    "invigilator_planning", "Assigning invigilators"
                )

                await self._update_job_status(
                    job.id, "running", 70, "invigilator_planning"
                )

                invig_plan = await self.invig_alloc.assign_invigilators(session_id)

                self._end_action(
                    invig_action, "completed", {"assignments_count": len(invig_plan)}
                )

            # Result bundling and finalization
            finalize_action = self._start_action(
                "result_finalization", "Bundling and storing results"
            )

            # Bundle result - serialize all objects for JSON storage
            result_data = {
                "solver_result": serialize_for_json(solver_result),
                "room_plan": (
                    [serialize_for_json(vars(p)) for p in room_plan]
                    if room_plan
                    else []
                ),
                "invigilator_plan": (
                    [serialize_for_json(vars(p)) for p in invig_plan]
                    if invig_plan
                    else []
                ),
                "tracking_data": {
                    "job_id": str(job_id),
                    "total_actions": len(self._action_stack)
                    + 1,  # +1 for current action
                    "orchestration_context": self._get_current_context(),
                },
            }

            # Finalize and version
            await self._update_job_result(job.id, result_data)
            await self._update_job_status(job.id, "completed", 100, "finalized")

            # Create version with tracking
            version = TimetableVersion(
                job_id=job.id,
                version_number=await self.job_data.get_latest_version_number() + 1,
                is_active=bool(options.activate_version),
                approved_by=None,
                approved_at=None,
            )

            self.session.add(version)

            # Final audit log
            self.session.add(
                AuditLog(
                    user_id=initiated_by,
                    action="job_completed",
                    entity_type="timetable_job",
                    entity_id=job.id,
                    notes=f"Job completed; version {version.version_number} created",
                    new_values=serialize_for_json(
                        {
                            "version_id": str(version.id),
                            "tracking_context": self._get_current_context(),
                        }
                    ),
                )
            )

            await self.session.commit()

            self._end_action(finalize_action, "completed")
            self._end_action(orchestration_action, "completed")

            await self._log_operation(
                "job_completed",
                {
                    "job_id": str(job_id),
                    "version_number": version.version_number,
                    "total_duration": "calculated_from_tracking",
                },
            )

            return job.id

        except Exception as exc:
            logger.exception(f"Job {job_id} failed with error: {exc}")
            if job:  # type: ignore
                await self._update_job_error(job.id, f"Job failed: {exc}")
            self._end_action(orchestration_action, "failed", {"error": str(exc)})
            await self._log_operation("job_failed", {"error": str(exc)}, "ERROR")
            return job_id

    async def _update_job_status(
        self, job_id: UUID, status: str, progress: int, phase: Optional[str]
    ) -> None:
        """Update job status with action tracking."""
        action_id = self._start_action(
            "status_update", f"Updating job status to {status}"
        )

        await self.session.execute(
            update(TimetableJob)
            .where(TimetableJob.id == job_id)
            .values(
                status=status,
                progress_percentage=progress,
                solver_phase=phase,
                updated_at=datetime.utcnow(),
            )
        )
        await self.session.commit()

        self._end_action(action_id, "completed")

    async def _update_job_error(self, job_id: UUID, error_message: str) -> None:
        """Update job with error status and action tracking."""
        action_id = self._start_action("error_update", "Recording job error")

        await self.session.execute(
            update(TimetableJob)
            .where(TimetableJob.id == job_id)
            .values(
                status="failed",
                error_message=error_message,
                updated_at=datetime.utcnow(),
            )
        )
        await self.session.commit()

        self._end_action(action_id, "completed")
        await self._log_operation(
            "job_error_recorded", {"error": error_message}, "ERROR"
        )

    async def _update_job_result(
        self, job_id: UUID, result_data: Dict[str, Any]
    ) -> None:
        """Update job result with tracking context."""
        action_id = self._start_action("result_update", "Storing job results")

        # Ensure all UUID objects are serialized before storing in JSONB
        serialized_data = serialize_for_json(result_data)

        await self.session.execute(
            update(TimetableJob)
            .where(TimetableJob.id == job_id)
            .values(result_data=serialized_data, updated_at=datetime.utcnow())
        )
        await self.session.commit()

        self._end_action(action_id, "completed")

    def get_job_tracking_info(self, job_id: UUID) -> Dict[str, Any]:
        """Get comprehensive tracking information for a job."""
        return {
            "job_id": str(job_id),
            "current_context": self._get_current_context(),
            "action_history": [
                {
                    "action_id": str(action["action_id"]),
                    "action_type": action["action_type"],
                    "description": action["description"],
                    "started_at": action["started_at"].isoformat(),
                    "status": action.get("status", "active"),
                }
                for action in self._action_stack
            ],
        }
