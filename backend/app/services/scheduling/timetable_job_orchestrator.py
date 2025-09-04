# backend/app/services/scheduling/timetable_job_orchestrator.py

from __future__ import annotations

from typing import Dict, List, Optional, Callable, Any
from uuid import UUID, uuid4
from dataclasses import dataclass
from datetime import datetime
import logging
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

# Retrieval services and helpers
from app.services.data_retrieval import (
    JobData,
    ConstraintData,
    AuditData,
)
from app.services.job import JobService
from app.services.scheduling.data_preparation_service import DataPreparationService
from app.services.scheduling.room_allocation_service import RoomAllocationService
from app.services.scheduling.invigilator_assignment_service import (
    InvigilatorAssignmentService,
)

# Models
from app.models.jobs import TimetableJob, TimetableVersion
from app.models.audit_logs import AuditLog

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorOptions:
    run_room_planning: bool = True
    run_invigilator_planning: bool = True
    activate_version: bool = False


def serialize_for_json(obj: Any) -> Any:
    """Convert objects to JSON-serializable format"""
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, "__dict__"):
        return {k: serialize_for_json(v) for k, v in obj.__dict__.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    else:
        return obj


class TimetableJobOrchestrator:
    """
    Orchestrates a scheduling job lifecycle:
    - Create job
    - Prepare dataset
    - Call external solver (optional; injected callable)
    - Build room and invigilator plans
    - Persist result + versioning
    - Emit audit events
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.job_data = JobData(session)
        self.job_service = JobService(session)
        self.constraint_data = ConstraintData(session)
        self.audit_data = AuditData(session)
        self.data_prep = DataPreparationService(session)
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
        options = options or OrchestratorOptions()

        job = TimetableJob(
            session_id=session_id,
            configuration_id=configuration_id,
            initiated_by=initiated_by,
            status="queued",
            progress_percentage=0,
            started_at=datetime.utcnow(),
        )

        self.session.add(job)
        await self.session.flush()

        # Audit create
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

        try:
            # Run the process
            await self._update_job_status(job.id, "running", 5, "preparing")
            prepared = await self.data_prep.build_dataset(session_id)

            # Merge constraints
            conf_constraints = await self.constraint_data.get_configuration_constraints(
                configuration_id
            )

            solver_input = {
                "prepared_data": serialize_for_json(prepared),
                "constraints": conf_constraints,
                "options": vars(options),
            }

            solver_result: Dict[str, Any] = {}
            if solver_callable:
                await self._update_job_status(job.id, "running", 25, "solving")
                try:
                    solver_result = solver_callable(solver_input) or {}
                except Exception as exc:
                    await self._update_job_error(job.id, f"Solver failed: {exc}")
                    return job.id

            # Room planning
            room_plan = None
            if options.run_room_planning:
                await self._update_job_status(job.id, "running", 50, "room_planning")
                room_plan = await self.room_alloc.plan_room_allocations(session_id)
                plan_validation = await self.room_alloc.validate_room_plan(
                    room_plan, session_id
                )

                if plan_validation.get("errors"):
                    await self._update_job_error(
                        job.id, f"Room plan invalid: {plan_validation['errors']}"
                    )
                    return job.id

            # Invigilator planning
            invig_plan = None
            if options.run_invigilator_planning:
                await self._update_job_status(
                    job.id, "running", 70, "invigilator_planning"
                )
                invig_plan = await self.invig_alloc.assign_invigilators(session_id)

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
            }

            # Finalize and version
            await self._update_job_result(job.id, result_data)
            await self._update_job_status(job.id, "completed", 100, "finalized")

            # Create version
            version = TimetableVersion(
                job_id=job.id,
                version_number=await self.job_data.get_latest_version_number() + 1,
                is_active=bool(options.activate_version),
                approved_by=None,
                approved_at=None,
            )

            self.session.add(version)

            # Audit complete
            self.session.add(
                AuditLog(
                    user_id=initiated_by,
                    action="job_completed",
                    entity_type="timetable_job",
                    entity_id=job.id,
                    notes=f"Job completed; version {version.version_number} created",
                )
            )

            await self.session.commit()
            return job.id

        except Exception as exc:
            logger.exception(f"Job {job.id} failed with error: {exc}")
            await self._update_job_error(job.id, f"Job failed: {exc}")
            return job.id

    async def _update_job_status(
        self, job_id: UUID, status: str, progress: int, phase: Optional[str]
    ) -> None:
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

    async def _update_job_error(self, job_id: UUID, error_message: str) -> None:
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

    async def _update_job_result(
        self, job_id: UUID, result_data: Dict[str, Any]
    ) -> None:
        # Ensure all UUID objects are serialized before storing in JSONB
        serialized_data = serialize_for_json(result_data)

        await self.session.execute(
            update(TimetableJob)
            .where(TimetableJob.id == job_id)
            .values(result_data=serialized_data, updated_at=datetime.utcnow())
        )
        await self.session.commit()
