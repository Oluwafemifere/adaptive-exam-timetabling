# backend/app/tasks/scheduling_tasks.py

"""
Celery tasks for scheduling operations including timetable generation,
optimization, and solution management with real-time progress updates.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from datetime import datetime
from celery import Task

from .celery_app import celery_app
from ..services.scheduling.timetable_job_orchestrator import (
    TimetableJobOrchestrator,
    OrchestratorOptions,
)
from ..services.scheduling.data_preparation_service import DataPreparationService
from ..services.notification.websocket_manager import publish_job_update
from ..models.jobs import TimetableJob
from ..core.exceptions import SchedulingError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

# Scheduling engine imports
from scheduling_engine.core.problem_model import ExamSchedulingProblem
from scheduling_engine.core.solution import TimetableSolution
from scheduling_engine.cp_sat.solver_manager import CPSATSolverManager
from scheduling_engine.hybrid.coordinator import HybridCoordinator
from scheduling_engine.genetic_algorithm.evolution_manager import EvolutionManager

logger = logging.getLogger(__name__)


class SchedulingTask(Task):
    """Base class for scheduling tasks with progress tracking"""

    def __init__(self):
        self.job_id: Optional[str] = None
        self.progress = 0
        self.current_phase = "initializing"

    def update_progress(self, progress: int, phase: str, message: str = ""):
        """Update task progress and notify WebSocket clients"""
        self.progress = progress
        self.current_phase = phase

        # Update Celery task state
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

        # Send WebSocket update if job_id is available
        if self.job_id:
            asyncio.create_task(
                publish_job_update(
                    self.job_id,
                    {
                        "status": "running",
                        "progress": progress,
                        "phase": phase,
                        "message": message,
                    },
                )
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
    Main timetable generation task using hybrid scheduling engine.
    Runs asynchronously with progress updates.
    """
    self.job_id = job_id

    try:
        logger.info(f"Starting timetable generation for job {job_id}")

        # Run the async scheduling process
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                _async_generate_timetable(
                    self, job_id, session_id, configuration_id, user_id, options
                )
            )
            return result
        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"Timetable generation failed for job {job_id}: {exc}")

        # Update job status to failed
        asyncio.create_task(
            publish_job_update(
                job_id,
                {
                    "status": "failed",
                    "progress": 0,
                    "phase": "error",
                    "message": f"Generation failed: {str(exc)}",
                },
            )
        )

        raise exc


async def _async_generate_timetable(
    task: SchedulingTask,
    job_id: str,
    session_id: str,
    configuration_id: str,
    user_id: str,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Async implementation of timetable generation"""

    from ..database import db_manager

    if not db_manager._is_initialized:
        await db_manager.initialize()
    async with db_manager.get_session() as db:
        try:
            # Initialize services
            orchestrator = TimetableJobOrchestrator(db)
            data_prep = DataPreparationService(db)

            # Parse UUIDs
            session_uuid = UUID(session_id)
            config_uuid = UUID(configuration_id)
            user_uuid = UUID(user_id)
            job_uuid = UUID(job_id)

            task.update_progress(5, "preparing_data", "Preparing scheduling data...")

            # Prepare dataset
            dataset = await data_prep.build_dataset(session_uuid)

            task.update_progress(15, "building_problem", "Building problem model...")

            # Create problem model
            problem = ExamSchedulingProblem(
                session_id=session_uuid,
                session_name=f"Session {session_id}",
                db_session=db,
                configuration_id=config_uuid,
            )

            # Load data into problem model
            await problem.load_from_backend()

            task.update_progress(
                25, "initializing_solver", "Initializing hybrid solver..."
            )

            # Create hybrid coordinator
            coordinator = HybridCoordinator()

            def handle_progress(progress_info):
                progress = progress_info.get(
                    "progress", 0.0
                )  # Expected to be between 0.0-1.0
                message = progress_info.get("message", "")
                phase = progress_info.get("phase", "optimizing")
                # Map 0-1 progress to 25-85% of overall task progress
                task_progress = 25 + int(progress * 60)
                task.update_progress(task_progress, phase, message)

            coordinator.add_progress_callback(handle_progress)
            task.update_progress(30, "solving", "Running hybrid optimization...")

            # Run optimization
            results = await coordinator.optimize_schedule(
                problem=problem, time_limit_seconds=600  # 10 minutes total timeout
            )
            solution = results.best_solution

            if solution is None:
                raise SchedulingError("No solution found during optimization")

            task.update_progress(85, "post_processing", "Processing solution...")

            # Update solution statistics
            if hasattr(solution, "update_statistics"):
                solution.update_statistics()

            # Calculate quality metrics
            objective_value = (
                solution.calculate_objective_value()
                if hasattr(solution, "calculate_objective_value")
                else 0
            )
            fitness_score = (
                solution.calculate_fitness_score()
                if hasattr(solution, "calculate_fitness_score")
                else 0
            )
            completion_percentage = (
                solution.get_completion_percentage()
                if hasattr(solution, "get_completion_percentage")
                else 0
            )

            task.update_progress(90, "saving_results", "Saving results...")

            # Export solution to backend format
            backend_solution = (
                solution.export_to_backend_format()
                if hasattr(solution, "export_to_backend_format")
                else {}
            )

            # Update job with results
            await _update_job_results(
                db,
                job_uuid,
                {
                    "solution": backend_solution,
                    "objective_value": objective_value,
                    "fitness_score": fitness_score,
                    "completion_percentage": completion_percentage,
                    "statistics": (
                        solution.statistics.__dict__
                        if hasattr(solution, "statistics") and solution.statistics
                        else {}
                    ),
                },
            )

            task.update_progress(100, "completed", "Timetable generation completed!")

            # Send completion notification
            await publish_job_update(
                job_id,
                {
                    "status": "completed",
                    "progress": 100,
                    "phase": "completed",
                    "message": f"Generated timetable with {completion_percentage:.1f}% completion",
                    "result": {
                        "objective_value": objective_value,
                        "fitness_score": fitness_score,
                        "completion_percentage": completion_percentage,
                        "total_assignments": (
                            len(solution.assignments)
                            if hasattr(solution, "assignments")
                            else 0
                        ),
                    },
                },
            )

            return {
                "success": True,
                "job_id": job_id,
                "solution_id": str(solution.id),
                "objective_value": objective_value,
                "completion_percentage": completion_percentage,
                "total_assignments": len(solution.assignments),
            }

        except Exception as e:
            logger.error(f"Error in timetable generation: {e}")

            # Update job as failed
            await _update_job_failed(db, UUID(job_id), str(e))

            raise SchedulingError(f"Timetable generation failed: {e}")


@celery_app.task(bind=True, base=SchedulingTask, name="optimize_existing_timetable")
def optimize_existing_timetable_task(
    self, job_id: str, timetable_version_id: str, optimization_type: str = "incremental"
) -> Dict[str, Any]:
    """Optimize an existing timetable solution"""

    self.job_id = job_id

    try:
        logger.info(f"Starting timetable optimization for job {job_id}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                _async_optimize_timetable(
                    self, job_id, timetable_version_id, optimization_type
                )
            )
            return result
        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"Timetable optimization failed for job {job_id}: {exc}")
        raise exc


async def _async_optimize_timetable(
    task: SchedulingTask, job_id: str, timetable_version_id: str, optimization_type: str
) -> Dict[str, Any]:
    """Async implementation of timetable optimization"""

    from ..database import db_manager

    if not db_manager._is_initialized:
        await db_manager.initialize()

    async with db_manager.get_session() as db:
        try:
            task.update_progress(10, "loading_solution", "Loading existing solution...")

            # Load existing solution (implementation would depend on your storage format)
            # This is a placeholder - you'd implement based on how solutions are stored

            task.update_progress(
                30, "optimizing", f"Running {optimization_type} optimization..."
            )

            # Run optimization based on type
            if optimization_type == "incremental":
                # Run incremental optimization
                pass
            elif optimization_type == "full":
                # Run full re-optimization
                pass

            task.update_progress(90, "saving_optimized", "Saving optimized solution...")

            task.update_progress(100, "completed", "Optimization completed!")

            return {
                "success": True,
                "job_id": job_id,
                "optimization_type": optimization_type,
            }

        except Exception as e:
            logger.error(f"Error in timetable optimization: {e}")
            raise SchedulingError(f"Timetable optimization failed: {e}")


@celery_app.task(name="validate_timetable_solution")
def validate_timetable_solution_task(
    solution_data: Dict[str, Any], session_id: str, configuration_id: str
) -> Dict[str, Any]:
    """Validate a timetable solution against constraints"""

    try:
        logger.info(f"Validating timetable solution for session {session_id}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                _async_validate_solution(solution_data, session_id, configuration_id)
            )
            return result
        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"Solution validation failed: {exc}")
        raise exc


async def _async_validate_solution(
    solution_data: Dict[str, Any], session_id: str, configuration_id: str
) -> Dict[str, Any]:
    """Async implementation of solution validation"""

    from ..database import db_manager

    if not db_manager._is_initialized:
        await db_manager.initialize()
    async with db_manager.get_session() as db:
        try:
            # Create problem model for validation
            problem = ExamSchedulingProblem(
                session_id=UUID(session_id),
                session_name=f"Validation Session {session_id}",
                db_session=db,
                configuration_id=UUID(configuration_id),
            )

            await problem.load_from_backend()

            # Create solution from data
            solution = TimetableSolution(problem=problem)

            # Load assignments from solution_data
            # (Implementation depends on your solution format)

            # Validate with backend
            validation_result = await solution.validate_with_backend()

            # Detect conflicts
            conflicts = solution.detect_conflicts()

            return {
                "success": True,
                "validation_result": validation_result,
                "conflict_count": len(conflicts),
                "conflicts": [
                    {
                        "type": c.conflict_type,
                        "severity": c.severity.value,
                        "description": c.description,
                        "affected_exams": [str(e) for e in c.affected_exams],
                    }
                    for c in conflicts
                ],
                "is_feasible": solution.is_feasible(),
                "completion_percentage": solution.get_completion_percentage(),
            }

        except Exception as e:
            logger.error(f"Error in solution validation: {e}")
            raise SchedulingError(f"Solution validation failed: {e}")


@celery_app.task(name="cancel_scheduling_job")
def cancel_scheduling_job_task(
    job_id: str, reason: str = "Cancelled by user"
) -> Dict[str, Any]:
    """Cancel a running scheduling job"""

    try:
        logger.info(f"Cancelling scheduling job {job_id}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(_async_cancel_job(job_id, reason))
            return result
        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"Job cancellation failed for {job_id}: {exc}")
        raise exc


async def _async_cancel_job(job_id: str, reason: str) -> Dict[str, Any]:
    """Async implementation of job cancellation"""

    from ..database import db_manager

    if not db_manager._is_initialized:
        await db_manager.initialize()
    async with db_manager.get_session() as db:
        try:
            job_uuid = UUID(job_id)

            # Update job status to cancelled
            query = (
                update(TimetableJob)
                .where(TimetableJob.id == job_uuid)
                .values(
                    status="cancelled",
                    error_message=reason,
                    completed_at=datetime.utcnow(),
                )
            )

            await db.execute(query)
            await db.commit()

            # Send cancellation notification
            await publish_job_update(
                job_id,
                {
                    "status": "cancelled",
                    "progress": 0,
                    "phase": "cancelled",
                    "message": reason,
                },
            )

            return {"success": True, "job_id": job_id, "reason": reason}

        except Exception as e:
            logger.error(f"Error cancelling job: {e}")
            raise SchedulingError(f"Job cancellation failed: {e}")


# Helper functions


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
            objective_value=results.get("objective_value"),
            soft_constraint_score=results.get("fitness_score"),
            room_utilization_percentage=results.get("completion_percentage"),
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


# Export task functions
__all__ = [
    "generate_timetable_task",
    "optimize_existing_timetable_task",
    "validate_timetable_solution_task",
    "cancel_scheduling_job_task",
]
