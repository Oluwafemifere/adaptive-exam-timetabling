# backend/app/services/scheduling/integrated_engine_manager.py

"""
Integrated scheduling engine manager that provides a unified interface
for timetable generation with direct database integration.
This consolidates engine_manager.py and integrated_engine_manager.py functionality.
"""

import logging
import asyncio
import time
from typing import Dict, Any, Optional, List, Union
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from collections import defaultdict

logger = logging.getLogger(__name__)


class IntegratedSchedulingEngineManager:
    """
    Unified scheduling engine manager that provides all timetable generation
    functionality with direct database integration.

    Features:
    - Hybrid CP-SAT + GA optimization
    - Real-time progress tracking
    - Manual edit support with incremental optimization
    - Comprehensive result management
    - Job lifecycle management
    """

    def __init__(self, session: AsyncSession, user: Optional[Any] = None):
        self.session = session
        self.user = user

        # Initialize core components (import here to avoid circular imports)
        from .enhanced_engine_connector import EnhancedSchedulingEngineConnector
        from .hybrid_optimization_coordinator import HybridOptimizationCoordinator
        from .incremental_optimizer import IncrementalOptimizer

        self.connector = EnhancedSchedulingEngineConnector(session)
        self.coordinator = HybridOptimizationCoordinator(session)
        self.incremental_optimizer = IncrementalOptimizer(session)

        # Track active jobs for cancellation support
        self._active_jobs: Dict[str, asyncio.Task] = {}

    async def create_and_run_timetable_job(
        self,
        session_id: UUID,
        configuration_id: UUID,
        optimization_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new timetable generation job and start optimization.

        Returns:
            Dict containing job information and status
        """
        try:
            from app.models import TimetableJob
            from app.services.notification import publish_job_update

            # Create job record
            job = TimetableJob(
                session_id=session_id,
                configuration_id=configuration_id,
                initiated_by=self.user.id if self.user else None,
                status="queued",
                progress_percentage=0,
                created_at=datetime.utcnow(),
            )

            self.session.add(job)
            await self.session.commit()
            await self.session.refresh(job)

            # Start background optimization
            task = asyncio.create_task(
                self._run_optimization_background(job.id, optimization_params)
            )
            self._active_jobs[str(job.id)] = task

            # Publish initial job update
            await publish_job_update(
                str(job.id),
                {
                    "status": "queued",
                    "progress": 0,
                    "message": "Job queued for processing",
                },
            )

            logger.info(f"Created and started timetable job {job.id}")

            return {
                "success": True,
                "job_id": str(job.id),
                "status": "queued",
                "session_id": str(session_id),
                "created_at": job.created_at.isoformat(),
            }

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create timetable job: {e}")
            return {"success": False, "error": f"Failed to create job: {str(e)}"}

    async def start_timetable_job(
        self, session_id: str, configuration_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Legacy method for backward compatibility.
        Start a new timetable generation job.
        """
        try:
            session_uuid = UUID(session_id)
            config_uuid = (
                UUID(configuration_id)
                if configuration_id
                else await self._get_default_configuration_id()
            )

            return await self.create_and_run_timetable_job(session_uuid, config_uuid)

        except (ValueError, TypeError) as e:
            logger.error(f"Invalid UUID format: {e}")
            return {"success": False, "error": f"Invalid ID format: {str(e)}"}

    async def _run_optimization_background(
        self, job_id: UUID, optimization_params: Optional[Dict[str, Any]] = None
    ) -> None:
        """Run optimization in background with full error handling"""
        try:
            from app.services.notification import (
                notify_job_completed,
                notify_job_cancelled,
            )

            # Update job status to running
            await self._update_job_status(job_id, "running", 0, "starting")

            # Get job details
            job = await self._get_job(job_id)
            if not job:
                raise Exception(f"Job {job_id} not found")

            # Run hybrid optimization
            result = await self.coordinator.optimize_timetable(
                job_id=job_id,
                session_id=job.session_id,
                configuration_id=job.configuration_id,
                optimization_params=optimization_params,
            )

            if result.success:
                # Store results in database
                await self._store_optimization_results(job_id, result)
                # Create timetable version - add assertion for non-None solution
                assert (
                    result.solution is not None
                ), "Solution should not be None when optimization is successful"
                # Create timetable version
                await self._create_timetable_version(job_id, result.solution)

                # Update job to completed
                await self._update_job_status(
                    job_id, "completed", 100, "optimization_completed"
                )

                # Notify completion
                await notify_job_completed(
                    str(job_id),
                    {
                        "success": True,
                        "metrics": result.metrics,
                        "execution_time": result.execution_time,
                    },
                )

                logger.info(
                    f"Job {job_id} completed successfully in {result.execution_time:.2f}s"
                )

            else:
                await self._handle_optimization_failure(job_id, result.error)

        except asyncio.CancelledError:
            logger.info(f"Optimization job {job_id} was cancelled")
            await self._update_job_status(job_id, "cancelled", 0, "cancelled_by_user")
            try:
                from app.services.notification import notify_job_cancelled

                await notify_job_cancelled(str(job_id))
            except Exception:
                pass

        except Exception as e:
            logger.error(
                f"Optimization job {job_id} failed with error: {e}", exc_info=True
            )
            await self._handle_optimization_failure(job_id, str(e))

        finally:
            # Clean up job tracking
            self._active_jobs.pop(str(job_id), None)

    async def get_job_status(self, job_id: UUID) -> Dict[str, Any]:
        """Get comprehensive job status information"""
        try:
            job = await self._get_job(job_id)
            if not job:
                from app.core.exceptions import JobNotFoundError

                raise JobNotFoundError(f"Job {job_id} not found")

            # Check if user has access
            if self.user and not await self._can_access_job(job):
                from app.core.exceptions import SchedulingError

                raise SchedulingError(f"Access denied to job {job_id}")

            # Get optimization statistics if available
            optimization_stats = None
            if job.status in ["completed", "failed"]:
                try:
                    optimization_stats = (
                        await self.connector.get_optimization_statistics(job.session_id)
                    )
                except Exception:
                    pass  # Don't fail if stats unavailable

            status_data = {
                "job_id": str(job.id),
                "session_id": str(job.session_id),
                "configuration_id": str(job.configuration_id),
                "status": job.status,
                "progress_percentage": job.progress_percentage,
                "solver_phase": job.solver_phase,
                "initiated_by": str(job.initiated_by) if job.initiated_by else None,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": (
                    job.completed_at.isoformat() if job.completed_at else None
                ),
                "error_message": job.error_message,
                "total_runtime_seconds": job.total_runtime_seconds,
                "metrics": {
                    "hard_constraint_violations": job.hard_constraint_violations or 0,
                    "soft_constraint_score": float(job.soft_constraint_score or 0),
                    "room_utilization_percentage": float(
                        job.room_utilization_percentage or 0
                    ),
                    "cp_sat_runtime_seconds": job.cp_sat_runtime_seconds,
                    "ga_runtime_seconds": job.ga_runtime_seconds,
                },
                "optimization_statistics": optimization_stats,
            }

            return status_data

        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {e}")
            from app.core.exceptions import SchedulingError

            raise SchedulingError(f"Failed to get job status: {str(e)}")

    async def cancel_timetable_job(self, job_id: UUID) -> Dict[str, Any]:
        """Cancel a running or queued job"""
        try:
            from app.core.exceptions import JobNotFoundError, SchedulingError
            from app.services.notification import publish_job_update

            job = await self._get_job(job_id)
            if not job:
                raise JobNotFoundError(f"Job {job_id} not found")

            if job.status not in ["queued", "running"]:
                raise SchedulingError(f"Cannot cancel job with status: {job.status}")

            # Cancel background task if running
            task = self._active_jobs.get(str(job_id))
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # Update job status
            await self._update_job_status(job_id, "cancelled", 0, "cancelled_by_user")

            # Notify cancellation
            await publish_job_update(
                str(job_id),
                {
                    "status": "cancelled",
                    "progress": 0,
                    "message": "Job cancelled by user",
                },
            )

            logger.info(f"Cancelled job {job_id}")

            return {
                "success": True,
                "job_id": str(job_id),
                "status": "cancelled",
                "message": "Job cancelled successfully",
            }

        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            from app.core.exceptions import SchedulingError

            raise SchedulingError(f"Failed to cancel job: {str(e)}")

    async def cancel_job(self, job_id: Union[UUID, str]) -> None:
        """Legacy method for backward compatibility"""
        job_uuid = UUID(str(job_id)) if not isinstance(job_id, UUID) else job_id
        result = await self.cancel_timetable_job(job_uuid)
        if not result["success"]:
            raise Exception(result.get("error", "Failed to cancel job"))

    async def get_timetable_data(
        self, job_id: UUID, format_type: str = "detailed"
    ) -> Dict[str, Any]:
        """Get timetable data for a completed job"""
        try:
            from app.core.exceptions import JobNotFoundError, SchedulingError

            job = await self._get_job(job_id)
            if not job:
                raise JobNotFoundError(f"Job {job_id} not found")

            if job.status != "completed":
                raise SchedulingError(
                    f"Job {job_id} is not completed (status: {job.status})"
                )

            # Get timetable version
            version = await self._get_job_timetable_version(job_id)
            if not version:
                raise SchedulingError(f"No timetable version found for job {job_id}")

            # Get exam assignments
            assignments = await self._get_exam_assignments(job.session_id)

            if format_type == "summary":
                return await self._format_timetable_summary(assignments, job)
            elif format_type == "export":
                return await self._format_timetable_export(assignments, job)
            else:  # detailed
                return await self._format_timetable_detailed(assignments, job, version)

        except Exception as e:
            logger.error(f"Failed to get timetable data for job {job_id}: {e}")
            from app.core.exceptions import SchedulingError

            raise SchedulingError(f"Failed to get timetable data: {str(e)}")

    async def get_timetable(self, timetable_id: str) -> Optional[Dict[str, Any]]:
        """Legacy method - Get timetable data by ID"""
        try:
            timetable_uuid = UUID(timetable_id)
            return await self.get_timetable_data(timetable_uuid, "detailed")
        except Exception as e:
            logger.error(f"Failed to get timetable {timetable_id}: {e}")
            return None

    async def apply_manual_edit(
        self, job_id: UUID, edit_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply manual edit to existing timetable using incremental optimization"""
        try:
            from app.core.exceptions import JobNotFoundError, SchedulingError

            job = await self._get_job(job_id)
            if not job:
                raise JobNotFoundError(f"Job {job_id} not found")

            if job.status != "completed":
                raise SchedulingError(
                    f"Cannot edit incomplete job (status: {job.status})"
                )

            # Get current timetable version
            version = await self._get_job_timetable_version(job_id)
            if not version:
                raise SchedulingError(f"No timetable version found for job {job_id}")

            # Apply incremental optimization
            edit_result = await self.incremental_optimizer.apply_manual_edit(
                version_id=version.id,
                edit_data=edit_data,
                user_id=self.user.id if self.user else None,
            )

            if edit_result["success"]:
                # Create new timetable version
                new_version = await self._create_timetable_version_from_edit(
                    job_id, edit_result["solution"], edit_data
                )

                return {
                    "success": True,
                    "new_version_id": str(new_version.id),
                    "edit_summary": edit_result.get("edit_summary", {}),
                    "validation_results": edit_result.get("validation_results", {}),
                    "performance_impact": edit_result.get("performance_impact", {}),
                }
            else:
                return {
                    "success": False,
                    "error": edit_result.get("error"),
                    "conflicts": edit_result.get("conflicts", []),
                    "suggestions": edit_result.get("suggestions", []),
                }

        except Exception as e:
            logger.error(f"Failed to apply manual edit to job {job_id}: {e}")
            from app.core.exceptions import SchedulingError

            raise SchedulingError(f"Failed to apply manual edit: {str(e)}")

    async def generate_timetable(self, job_id: UUID) -> Dict[str, Any]:
        """Legacy method - Core timetable generation logic"""
        try:
            # Get job details
            job = await self._get_job(job_id)
            if not job:
                raise Exception(f"Job {job_id} not found")

            # Use the coordinator for optimization
            result = await self.coordinator.optimize_timetable(
                job_id=job_id,
                session_id=job.session_id,
                configuration_id=job.configuration_id,
                optimization_params=None,
            )

            if result.success:
                # Store results and create version
                await self._store_optimization_results(job_id, result)
                version = await self._create_timetable_version(job_id, result.solution)

                return {
                    "version_id": str(version.id),
                    "metrics": result.metrics,
                    "solution": result.solution,
                }
            else:
                raise Exception(f"Optimization failed: {result.error}")

        except Exception as e:
            logger.error(f"Failed to generate timetable for job {job_id}: {e}")
            raise

    # Helper methods

    async def _get_job(self, job_id: UUID) -> Optional[Any]:
        """Get job by ID"""
        from app.models import TimetableJob

        query = select(TimetableJob).where(TimetableJob.id == job_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def _can_access_job(self, job: Any) -> bool:
        """Check if current user can access the job"""
        if not self.user:
            return False

        # System admin can access all jobs
        if hasattr(self.user, "is_superuser") and self.user.is_superuser:
            return True

        # Users can access their own jobs
        if job.initiated_by == self.user.id:
            return True

        return False

    async def _update_job_status(
        self, job_id: UUID, status: str, progress: int, phase: Optional[str] = None
    ) -> None:
        """Update job status in database"""
        try:
            from app.models import TimetableJob

            update_data = {
                "status": status,
                "progress_percentage": progress,
                "updated_at": datetime.utcnow(),
            }

            if phase:
                update_data["solver_phase"] = phase

            if status == "running" and progress == 0:
                update_data["started_at"] = datetime.utcnow()
            elif status in ["completed", "failed", "cancelled"]:
                update_data["completed_at"] = datetime.utcnow()

            query = (
                update(TimetableJob)
                .where(TimetableJob.id == job_id)
                .values(**update_data)
            )

            await self.session.execute(query)
            await self.session.commit()

        except Exception as e:
            logger.error(f"Failed to update job status: {e}")
            await self.session.rollback()

    async def _store_optimization_results(self, job_id: UUID, result: Any) -> None:
        """Store optimization results in job record"""
        try:
            from app.models import TimetableJob

            metrics = result.metrics or {}
            update_data = {
                "total_runtime_seconds": int(result.execution_time or 0),
                "hard_constraint_violations": (
                    metrics.get("constraint_analysis", {})
                    .get("hard_constraints", {})
                    .get("student_conflicts", {})
                    .get("violations", 0)
                ),
                "soft_constraint_score": float(
                    metrics.get("quality_metrics", {}).get("assignment_rate", 0)
                ),
                "room_utilization_percentage": float(
                    metrics.get("resource_utilization", {}).get(
                        "room_utilization_rate", 0
                    )
                    * 100
                ),
                "result_data": metrics,
                "updated_at": datetime.utcnow(),
            }

            # Add phase-specific runtimes if available
            phase_times = metrics.get("phase_times", {})
            if "cpsat" in phase_times:
                update_data["cp_sat_runtime_seconds"] = int(
                    phase_times["cpsat"].get("cpsat_runtime", 0)
                )
            if "ga" in phase_times:
                update_data["ga_runtime_seconds"] = int(
                    phase_times["ga"].get("ga_runtime", 0)
                )

            query = (
                update(TimetableJob)
                .where(TimetableJob.id == job_id)
                .values(**update_data)
            )

            await self.session.execute(query)
            await self.session.commit()

        except Exception as e:
            logger.error(f"Failed to store optimization results: {e}")
            await self.session.rollback()

    async def _create_timetable_version(
        self, job_id: UUID, solution: Dict[str, Any]
    ) -> Any:
        """Create timetable version from optimization solution"""
        try:
            from app.models import TimetableVersion

            version = TimetableVersion(
                job_id=job_id,
                version_number=1,
                is_active=True,
                created_at=datetime.utcnow(),
            )

            self.session.add(version)
            await self.session.commit()
            await self.session.refresh(version)

            # Update exam assignments in database
            assignments = solution.get("assignments", {})
            await self._apply_exam_assignments(assignments)

            logger.info(f"Created timetable version {version.id} for job {job_id}")
            return version

        except Exception as e:
            logger.error(f"Failed to create timetable version: {e}")
            await self.session.rollback()
            raise

    async def _apply_exam_assignments(
        self, assignments: Dict[str, Dict[str, Any]]
    ) -> None:
        """Apply exam assignments to database"""
        try:
            from app.models import Exam, ExamRoom, ExamInvigilator

            for exam_id_str, assignment in assignments.items():
                try:
                    exam_id = UUID(exam_id_str)
                    time_slot_id = UUID(assignment["timeslot_id"])
                    room_id = UUID(assignment["room_id"])
                    staff_ids = [UUID(sid) for sid in assignment.get("staff_ids", [])]

                    # Update exam
                    exam_query = (
                        update(Exam)
                        .where(Exam.id == exam_id)
                        .values(
                            time_slot_id=time_slot_id,
                            status="scheduled",
                            updated_at=datetime.utcnow(),
                        )
                    )
                    await self.session.execute(exam_query)

                    # Clear existing assignments
                    from sqlalchemy import delete

                    await self.session.execute(
                        delete(ExamRoom).where(ExamRoom.exam_id == exam_id)
                    )
                    await self.session.execute(
                        delete(ExamInvigilator).where(
                            ExamInvigilator.exam_id == exam_id
                        )
                    )

                    # Add room assignment
                    exam_room = ExamRoom(
                        exam_id=exam_id,
                        room_id=room_id,
                        allocated_capacity=50,  # Default capacity
                        is_primary=True,
                    )
                    self.session.add(exam_room)

                    # Add invigilator assignments
                    for i, staff_id in enumerate(staff_ids):
                        exam_invigilator = ExamInvigilator(
                            exam_id=exam_id,
                            staff_id=staff_id,
                            room_id=room_id,
                            is_chief_invigilator=(i == 0),
                        )
                        self.session.add(exam_invigilator)

                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Invalid UUID in assignment for exam {exam_id_str}: {e}"
                    )
                    continue

            await self.session.commit()
            logger.info(f"Applied {len(assignments)} exam assignments to database")

        except Exception as e:
            logger.error(f"Failed to apply exam assignments: {e}")
            await self.session.rollback()
            raise

    async def _handle_optimization_failure(
        self, job_id: UUID, error_message: str
    ) -> None:
        """Handle optimization failure"""
        try:
            from app.models import TimetableJob
            from app.services.notification import notify_job_completed

            await self._update_job_status(job_id, "failed", 0, "optimization_failed")

            # Store error message
            query = (
                update(TimetableJob)
                .where(TimetableJob.id == job_id)
                .values(error_message=error_message, completed_at=datetime.utcnow())
            )

            await self.session.execute(query)
            await self.session.commit()

            # Notify failure
            await notify_job_completed(
                str(job_id), {"success": False, "error": error_message}
            )

        except Exception as e:
            logger.error(f"Failed to handle optimization failure: {e}")

    async def _get_job_timetable_version(self, job_id: UUID) -> Optional[Any]:
        """Get the active timetable version for a job"""
        from app.models import TimetableVersion

        query = select(TimetableVersion).where(
            TimetableVersion.job_id == job_id, TimetableVersion.is_active == True
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def _get_exam_assignments(self, session_id: UUID) -> List[Dict[str, Any]]:
        """Get all exam assignments for a session"""
        # This would be a complex query joining exams, rooms, time slots, and staff
        # For now, return a placeholder
        return []

    async def _format_timetable_detailed(
        self,
        assignments: List[Dict[str, Any]],
        job: Any,
        version: Any,
    ) -> Dict[str, Any]:
        """Format detailed timetable data"""
        return {
            "job_id": str(job.id),
            "version_id": str(version.id),
            "session_id": str(job.session_id),
            "assignments": assignments,
            "metadata": {
                "created_at": version.created_at.isoformat(),
                "optimization_method": "hybrid_cpsat_ga",
                "total_runtime": job.total_runtime_seconds,
            },
        }

    async def _format_timetable_summary(
        self, assignments: List[Dict[str, Any]], job: Any
    ) -> Dict[str, Any]:
        """Format summary timetable data"""
        return {
            "job_id": str(job.id),
            "total_assignments": len(assignments),
            "completion_rate": job.soft_constraint_score or 0,
            "execution_time": job.total_runtime_seconds,
        }

    async def _format_timetable_export(
        self, assignments: List[Dict[str, Any]], job: Any
    ) -> Dict[str, Any]:
        """Format timetable data for export"""
        return {
            "format": "export",
            "job_id": str(job.id),
            "assignments": assignments,
            "export_timestamp": datetime.utcnow().isoformat(),
        }

    async def _create_timetable_version_from_edit(
        self, job_id: UUID, solution: Dict[str, Any], edit_data: Dict[str, Any]
    ) -> Any:
        """Create new timetable version from manual edit"""
        from app.models import TimetableVersion

        # Get current version number
        query = (
            select(TimetableVersion)
            .where(TimetableVersion.job_id == job_id)
            .order_by(TimetableVersion.version_number.desc())
            .limit(1)
        )

        result = await self.session.execute(query)
        latest_version = result.scalar_one_or_none()

        next_version_number = (
            (latest_version.version_number + 1) if latest_version else 1
        )

        # Deactivate previous versions
        deactivate_query = (
            update(TimetableVersion)
            .where(TimetableVersion.job_id == job_id)
            .values(is_active=False)
        )

        await self.session.execute(deactivate_query)

        # Create new version
        version = TimetableVersion(
            job_id=job_id,
            version_number=next_version_number,
            is_active=True,
            created_at=datetime.utcnow(),
        )

        self.session.add(version)
        await self.session.commit()
        await self.session.refresh(version)

        # Apply new assignments
        assignments = solution.get("assignments", {})
        await self._apply_exam_assignments(assignments)

        logger.info(f"Created timetable version {version.id} from manual edit")
        return version

    async def _get_default_configuration_id(self) -> UUID:
        """Get default configuration ID"""
        # For now, return a placeholder UUID
        # In practice, this would query the default configuration
        from uuid import uuid4

        return uuid4()
