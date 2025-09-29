# backend/app/tasks/scheduling_tasks.py

"""
Celery tasks for scheduling operations including timetable generation,
optimization, and solution management with real-time progress updates.
REFACTORED FOR PURE CP-SAT SOLVER IMPLEMENTATION.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime, date
from celery import Task

# --- Core Application Imports ---
from .celery_app import celery_app, _run_coro_in_new_loop
from ..services.scheduling.data_preparation_service import ExactDataFlowService
from ..services.notification.websocket_manager import publish_job_update
from ..models.jobs import TimetableJob
from ..core.exceptions import SchedulingError
from ..core.config import settings

# --- SQLAlchemy Imports for Per-Task DB Connection ---
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy import update, text
from sqlalchemy.pool import NullPool

# --- SCHEDULING ENGINE IMPORTS (CP-SAT ONLY) ---
from scheduling_engine.core.problem_model import ExamSchedulingProblem
from scheduling_engine.core.solution import TimetableSolution, SolutionStatus
from scheduling_engine.cp_sat.solver_manager import CPSATSolverManager
from ortools.sat.python import cp_model

logger = logging.getLogger(__name__)


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
    session_id: str,
    configuration_id: str,
    user_id: str,
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
        result = _run_coro_in_new_loop(
            _async_generate_timetable(
                self, job_id, session_id, configuration_id, user_id, options
            )
        )
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


async def _update_job_status(
    db: AsyncSession, job_id: UUID, status: str, started_at: Optional[datetime] = None
) -> None:
    """Updates the status and start time of a job."""
    values: Dict[str, Any] = {"status": status}
    if started_at:
        values["started_at"] = started_at

    query = update(TimetableJob).where(TimetableJob.id == job_id).values(**values)
    await db.execute(query)
    await db.commit()


async def _async_generate_timetable(
    task: SchedulingTask,
    job_id: str,
    session_id: str,
    configuration_id: str,
    user_id: str,
    options: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Async implementation of timetable generation using CP-SAT solver."""

    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    async_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    try:
        async with async_session_factory() as db:
            await db.execute(
                text("SELECT exam_system.update_job_status(:job_id, 'running', true)"),
                {"job_id": UUID(job_id)},
            )
            await db.commit()

            await task.update_progress(
                5, "preparing_data", "Preparing scheduling dataset..."
            )
            data_prep = ExactDataFlowService(db)
            dataset = await data_prep.build_exact_problem_model_dataset(
                UUID(session_id)
            )

            assert options
            start_date_str = options.get("start_date")
            end_date_str = options.get("end_date")

            if not start_date_str or not end_date_str:
                raise SchedulingError(
                    "Scheduling task requires 'start_date' and 'end_date' in options."
                )

            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
            logger.info(
                f"Using date range from task options: {start_date} to {end_date}"
            )

            await task.update_progress(
                15, "building_problem", "Building problem model..."
            )
            problem = ExamSchedulingProblem(
                session_id=UUID(session_id),
                exam_period_start=start_date,
                exam_period_end=end_date,
                db_session=db,
            )
            await problem.load_from_backend(dataset)

            await task.update_progress(
                25, "initializing_solver", "Initializing CP-SAT solver..."
            )
            solver_manager = CPSATSolverManager(problem=problem)

            await task.update_progress(30, "solving", "Running CP-SAT solver...")
            status, solution = solver_manager.solve()

            if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                raise SchedulingError(
                    f"Solver failed to find a solution. Status: {solver_manager.solver.StatusName(status)}"
                )

            await task.update_progress(85, "post_processing", "Processing solution...")
            solution.update_statistics()

            objective_value = solution.objective_value
            completion_percentage = solution.get_completion_percentage()
            backend_solution_dict = solution.to_dict()
            statistics_dict = solution.statistics.to_dict()

            await task.update_progress(
                90, "saving_results", "Saving results to database..."
            )
            results_payload = {
                "solution": backend_solution_dict,
                "objective_value": objective_value,
                "completion_percentage": completion_percentage,
                "statistics": statistics_dict,
            }
            await db.execute(
                text("SELECT exam_system.update_job_results(:job_id, :results)"),
                {"job_id": UUID(job_id), "results": json.dumps(results_payload)},
            )
            await db.commit()

            await publish_job_update(
                job_id,
                {
                    "status": "completed",
                    "progress": 100,
                    "phase": "completed",
                    "message": f"Generated timetable with {completion_percentage:.1f}% completion.",
                    "result": results_payload,
                },
            )

            # --- START OF FIX ---
            # REMOVED the redundant call that was causing the status to revert to "running"
            # await task.update_progress(100, "completed", "Timetable generation complete!")
            # --- END OF FIX ---

            return {
                "success": True,
                "job_id": job_id,
                "solution_id": str(solution.id),
                "objective_value": objective_value,
                "completion_percentage": completion_percentage,
                "total_assignments": len(solution.assignments),
            }

    except Exception as e:
        logger.error(
            f"Error in async timetable generation for job {job_id}: {e}",
            exc_info=True,
        )
        async with async_session_factory() as error_db:
            await _update_job_failed(error_db, UUID(job_id), str(e))

        raise SchedulingError(f"Timetable generation failed: {e}")
    finally:
        await engine.dispose()


async def _update_job_results(
    db: AsyncSession, job_id: UUID, results: Dict[str, Any]
) -> None:
    """Update job with results data"""
    query = (
        update(TimetableJob)
        .where(TimetableJob.id == job_id)
        .values(
            status="completed",
            progress_percentage=100,
            result_data=results,
            completed_at=datetime.utcnow(),
        )
    )
    await db.execute(query)
    await db.commit()


async def _update_job_failed(
    db: AsyncSession, job_id: UUID, error_message: str
) -> None:
    """Update job as failed"""
    query = (
        update(TimetableJob)
        .where(TimetableJob.id == job_id)
        .values(
            status="failed", error_message=error_message, completed_at=datetime.utcnow()
        )
    )
    await db.execute(query)
    await db.commit()


__all__ = [
    "generate_timetable_task",
]
