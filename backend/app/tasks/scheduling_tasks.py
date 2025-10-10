# backend/app/tasks/scheduling_tasks.py

"""
Celery tasks for scheduling operations including timetable generation,
optimization, and solution management with real-time progress updates.
REFACTORED FOR PURE CP-SAT SOLVER IMPLEMENTATION.
"""

import asyncio
import json
import logging
import math
from enum import Enum  # <-- Import Enum
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, date
from celery import Task

# --- Core Application Imports ---
from .celery_app import celery_app, _run_coro_in_new_loop
from .post_processing_tasks import (
    enrich_timetable_result_task,
)
from ..services.scheduling.data_preparation_service import ExactDataFlowService
from ..services.notification.websocket_manager import publish_job_update
from ..core.exceptions import SchedulingError
from ..core.config import settings

# --- SQLAlchemy Imports for Per-Task DB Connection ---
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy import event, text
from sqlalchemy.pool import NullPool

# --- SCHEDULING ENGINE IMPORTS (CP-SAT ONLY) ---
from scheduling_engine.core.problem_model import ExamSchedulingProblem
from scheduling_engine.core.solution import TimetableSolution, SolutionStatus
from scheduling_engine.cp_sat.solver_manager import CPSATSolverManager
from ortools.sat.python import cp_model

logger = logging.getLogger(__name__)


# --- START OF ENHANCED SAFETY NET ---
def json_safe_default(o):
    """
    A robust JSON serializer 'default' function that handles non-serializable types,
    including datetimes, UUIDs, Enums, and infinity.
    """
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, UUID):
        return str(o)
    if isinstance(o, Enum):  # <-- ADDED ENUM HANDLER
        return o.value
    if o == float("inf") or o == -float("inf"):
        return None

    # Let the base class default method raise the TypeError
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")


# --- END OF ENHANCED SAFETY NET ---


class SchedulingTask(Task):
    """Base class for scheduling tasks with progress tracking"""

    def __init__(self):
        self.job_id: Optional[str] = None
        self.progress = 0
        self.current_phase = "initializing"

    async def update_progress(self, progress: int, phase: str, message: str = ""):
        """Update task progress and notify WebSocket clients"""
        self.progress = progress
        self.current_phase = phase

        self.update_state(
            state="PROGRESS",
            meta={
                "current": progress,
                "total": 100,
                "phase": phase,
                "message": message,
                "job_id": self.job_id,
            },
        )
        if self.job_id:
            await publish_job_update(
                self.job_id,
                {
                    "status": "running",
                    "progress": progress,
                    "phase": phase,
                    "message": message,
                },
            )


@celery_app.task(bind=True, base=SchedulingTask, name="generate_timetable")
def generate_timetable_task(
    self,
    job_id: str,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Main timetable generation task using the CP-SAT scheduling engine.
    Runs asynchronously with progress updates.
    """
    self.job_id = job_id
    options = options or {}

    try:
        logger.info(f"Starting timetable generation for job {job_id}")
        result = _run_coro_in_new_loop(_async_generate_timetable(self, job_id, options))
        return result

    except Exception as exc:
        logger.error(
            f"Timetable generation failed catastrophically for job {job_id}: {exc}",
            exc_info=True,
        )
        _run_coro_in_new_loop(
            publish_job_update(
                job_id,
                {
                    "status": "failed",
                    "progress": self.progress,
                    "phase": "error",
                    "message": f"Critical Error: {str(exc)}",
                },
            )
        )
        raise


async def _async_generate_timetable(
    task: SchedulingTask,
    job_id: str,
    options: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Async implementation of timetable generation using CP-SAT solver."""

    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    schema_search_path = "staging, exam_system, public"

    # Ensure every connection from this engine's pool has the correct search path.
    @event.listens_for(engine.sync_engine, "connect")
    def set_search_path(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute(f"SET search_path TO {schema_search_path};")
        cursor.close()

    async_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    job_uuid = UUID(job_id)

    try:
        async with async_session_factory() as db:
            await db.execute(
                text(
                    "SELECT exam_system.update_job_status(:p_job_id, :p_status, :p_progress, :p_solver_phase, :p_metrics, :p_set_started_at)"
                ),
                {
                    "p_job_id": job_uuid,
                    "p_status": "running",
                    "p_progress": 0,
                    "p_solver_phase": "initializing",
                    "p_metrics": None,
                    "p_set_started_at": True,
                },
            )
            await db.commit()

            await task.update_progress(
                5, "preparing_data", "Preparing scheduling dataset..."
            )
            data_prep = ExactDataFlowService(db)
            dataset = await data_prep.build_exact_problem_model_dataset(job_uuid)

            session_id = dataset.session_id

            assert options is not None

            # --- START OF FIX: Remove fallback logic for date range ---
            start_date = dataset.exam_period_start
            end_date = dataset.exam_period_end
            logger.info(f"Using date range from dataset: {start_date} to {end_date}")
            # --- END OF FIX ---

            if not start_date or not end_date:
                raise SchedulingError(
                    "Could not determine a valid exam period start or end date."
                )

            await task.update_progress(
                15, "building_problem", "Building problem model..."
            )
            problem = ExamSchedulingProblem(
                session_id=session_id,
                exam_period_start=start_date,
                exam_period_end=end_date,
                db_session=db,
            )
            await problem.load_from_backend(dataset)
            problem.ensure_constraints_activated()

            lookup_metadata = {
                "exams": {str(e.id): e.to_dict() for e in problem.exams.values()},
                "rooms": {str(r.id): r.to_dict() for r in problem.rooms.values()},
                "invigilators": {
                    str(i.id): i.to_dict() for i in problem.invigilators.values()
                },
                "instructors": {
                    str(i.id): i.to_dict() for i in problem.instructors.values()
                },
                "timeslots": {
                    str(t.id): t.to_dict() for t in problem.timeslots.values()
                },
                "days": {str(d.id): d.to_dict() for d in problem.days.values()},
                "timeslot_to_day_map": {
                    str(ts_id): str(day_id)
                    for day_id, ts_set in problem.day_timeslot_map.items()
                    for ts_id in ts_set
                },
            }

            await task.update_progress(
                25, "initializing_solver", "Initializing CP-SAT solver..."
            )
            solver_manager = CPSATSolverManager(problem=problem)

            # --- START OF MODIFICATION ---
            # Pass the task context to the solver manager so decorators can use it.
            solver_manager.task_context = task

            # The solve method will now trigger its own detailed progress updates via decorators.
            # We no longer need a manual update to 30% here.
            status, solution = await solver_manager.solve()
            # --- END OF MODIFICATION ---

            if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                raise SchedulingError(
                    f"Solver failed to find a solution. Status: {solver_manager.solver.StatusName(status)}"
                )

            await task.update_progress(85, "post_processing", "Processing solution...")
            solution.update_statistics()

            results_payload = {
                "solution": solution.to_dict(),
                "lookup_metadata": lookup_metadata,
                "objective_value": solution.objective_value,
                "completion_percentage": solution.get_completion_percentage(),
                "statistics": solution.statistics.to_dict(),
                "is_enriched": False,
            }

            await task.update_progress(
                90, "saving_results", "Saving results to database..."
            )
            await db.execute(
                text(
                    "SELECT exam_system.update_job_results(:p_job_id, :p_results_data)"
                ),
                {
                    "p_job_id": job_uuid,
                    "p_results_data": json.dumps(
                        results_payload, default=json_safe_default
                    ),
                },
            )
            await db.commit()

            logger.info(f"Chaining enrichment task for job {job_id}")
            enrich_timetable_result_task.delay(job_id=job_id)

            await publish_job_update(
                job_id,
                {
                    "status": "post_processing",
                    "progress": 95,
                    "phase": "pending_enrichment",
                    "message": "Timetable generated, preparing final view.",
                },
            )

            return {
                "success": True,
                "job_id": job_id,
                "solution_id": str(solution.id),
                "objective_value": results_payload["objective_value"],
                "completion_percentage": results_payload["completion_percentage"],
                "total_assignments": len(solution.assignments),
            }

    except Exception as e:
        logger.error(
            f"Error in async timetable generation for job {job_id}: {e}",
            exc_info=True,
        )
        async with async_session_factory() as error_db:
            await error_db.execute(
                text(
                    "SELECT exam_system.update_job_failed(:p_job_id, :p_error_message)"
                ),
                {"p_job_id": job_uuid, "p_error_message": str(e)},
            )
            await error_db.commit()
        raise SchedulingError(f"Timetable generation failed: {e}")
    finally:
        await engine.dispose()


__all__ = [
    "generate_timetable_task",
]
