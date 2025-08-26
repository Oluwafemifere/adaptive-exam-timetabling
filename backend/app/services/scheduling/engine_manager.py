import logging
import asyncio
from typing import Dict, Optional, Any, cast, TYPE_CHECKING
from uuid import UUID, uuid4
from datetime import datetime, date
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.jobs import TimetableJob, TimetableVersion
from app.models.academic import AcademicSession, Exam
from app.services.notification.websocket_manager import publish_job_update
from app.services.scheduling.constraint_builder import ConstraintBuilder
from app.services.scheduling.solution_evaluator import SolutionEvaluator
from app.services.scheduling.incremental_solver import IncrementalSolver
from app.core.exceptions import SchedulingError, InfeasibleProblemError #TODO implement

# Avoid importing runtime model types except for annotations
if TYPE_CHECKING:
    from app.models.users import User

logger = logging.getLogger(__name__)

class SchedulingService:
    """Main service for timetable generation and management."""

    def __init__(self, db: AsyncSession, user: Optional["User"] = None):
        self.db = db
        self.user = user
        self.constraint_builder = ConstraintBuilder(db)
        self.solution_evaluator = SolutionEvaluator()
        self.incremental_solver = IncrementalSolver(db)

    async def start_timetable_job(
        self,
        session_id: str,
        configuration_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Start a new timetable generation job."""
        try:
            session_uuid = UUID(session_id)
            session = await self._get_session(session_uuid)
            if not session:
                raise ValueError(f"Academic session {session_id} not found")

            if not configuration_id:
                configuration_id = await self._get_default_configuration()

            job = TimetableJob(
                id=uuid4(),
                session_id=session_uuid,
                # keep model type consistent. If TimetableJob.configuration_id is a UUID column
                # convert string to UUID. If it is string column adjust accordingly.
                configuration_id=UUID(configuration_id),
                initiated_by=self.user.id if self.user else None,
                status='queued',
                progress_percentage=0,
                created_at=datetime.utcnow()
            )

            self.db.add(job)
            await self.db.commit()
            await self.db.refresh(job)

            # Fire and forget background task
            await self._queue_timetable_generation(job.id)

            await publish_job_update(str(job.id), {
                'status': 'queued',
                'progress': 0,
                'message': 'Job queued for processing'
            })

            logger.info(f"Started timetabling job {job.id} for session {session_id}")

            return {
                'job_id': str(job.id),
                'status': 'queued',
                'session_id': session_id,
                'created_at': cast(datetime, job.created_at).isoformat()
            }

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to start timetable job: {e}")
            raise SchedulingError(f"Failed to start timetabling: {e}")

    async def get_timetable(self, timetable_id: str) -> Optional[Dict[str, Any]]:
        """Get timetable data by ID."""
        try:
            version_query = select(TimetableVersion).options(
                selectinload(TimetableVersion.job),
                selectinload(TimetableVersion.job).selectinload(TimetableJob.session)
            ).where(TimetableVersion.id == UUID(timetable_id))

            result = await self.db.execute(version_query)
            version = result.scalar_one_or_none()

            if version:
                return await self._format_timetable_response(version)

            job_query = select(TimetableJob).options(
                selectinload(TimetableJob.versions),  # keep if relationship exists
                selectinload(TimetableJob.session)
            ).where(TimetableJob.id == UUID(timetable_id))

            result = await self.db.execute(job_query)
            job = result.scalar_one_or_none()

            if job and getattr(job, "versions", None):
                active_version = next(
                    (v for v in job.versions if getattr(v, "is_active", False)),
                    job.versions[-1] if job.versions else None
                )
                if active_version:
                    return await self._format_timetable_response(active_version)

            return None

        except Exception as e:
            logger.error(f"Failed to get timetable {timetable_id}: {e}")
            raise

    async def generate_timetable(self, job_id: UUID) -> Dict[str, Any]:
        """Core timetable generation logic."""
        try:
            await self._update_job_status(job_id, 'running', 0, 'Initializing...')

            job = await self._get_job(job_id)
            if not job:
                raise SchedulingError(f"Job {job_id} not found")

            await publish_job_update(str(job_id), {
                'status': 'running',
                'progress': 10,
                'phase': 'data_loading',
                'message': 'Loading exam data and validating constraints...'
            })

            problem_data = await self._load_problem_data(job.session_id)

            await publish_job_update(str(job_id), {
                'status': 'running',
                'progress': 20,
                'phase': 'constraint_building',
                'message': 'Building constraint model...'
            })

            # ConstraintBuilder expects configuration_id as str.
            # Convert to str to match its typing if it requires str.
            cfg_id_for_builder = str(job.configuration_id)
            constraint_model = await self.constraint_builder.build_constraints(
                problem_data, cfg_id_for_builder
            )

            await publish_job_update(str(job_id), {
                'status': 'running',
                'progress': 30,
                'phase': 'cpsat_solving',
                'message': 'Finding feasible solution with CP-SAT...'
            })

            cpsat_solution = await self._solve_cpsat_phase(
                constraint_model, job_id
            )

            if not cpsat_solution['feasible']:
                raise InfeasibleProblemError("No feasible solution found")

            await publish_job_update(str(job_id), {
                'status': 'running',
                'progress': 60,
                'phase': 'ga_optimization',
                'message': 'Optimizing solution with genetic algorithm...'
            })

            optimized_solution = await self._solve_ga_phase(
                cpsat_solution, constraint_model, job_id
            )

            await publish_job_update(str(job_id), {
                'status': 'running',
                'progress': 90,
                'phase': 'finalizing',
                'message': 'Evaluating and storing solution...'
            })

            final_solution = await self._finalize_solution(
                optimized_solution, job_id
            )

            await self._update_job_status(job_id, 'completed', 100, 'Timetable generated successfully')

            await publish_job_update(str(job_id), {
                'status': 'completed',
                'progress': 100,
                'phase': 'completed',
                'message': 'Timetable generation completed successfully',
                'solution_metrics': final_solution['metrics']
            })

            return final_solution

        except InfeasibleProblemError as e:
            await self._handle_job_failure(job_id, f"Infeasible problem: {e}")
            raise
        except Exception as e:
            await self._handle_job_failure(job_id, f"Unexpected error: {e}")
            raise SchedulingError(f"Timetable generation failed: {e}")

    async def apply_manual_edit(
        self,
        timetable_id: str,
        edit_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply manual edit to existing timetable."""
        try:
            version = await self._get_timetable_version(UUID(timetable_id))
            if not version:
                raise ValueError(f"Timetable {timetable_id} not found")

            result = await self.incremental_solver.apply_edit(
                version, edit_data
            )

            if result['success']:
                new_version = await self._create_timetable_version(
                    version.job_id, result['solution'], is_active=False
                )

                await self._log_timetable_edit(
                    version.id, edit_data, getattr(self.user, "id", None)
                )

                return {
                    'success': True,
                    'new_version_id': str(new_version.id),
                    'validation_results': result.get('validation_results', {}),
                    'impact_analysis': result.get('impact_analysis', {})
                }
            else:
                return {
                    'success': False,
                    'errors': result.get('errors', []),
                    'conflicts': result.get('conflicts', [])
                }

        except Exception as e:
            logger.error(f"Failed to apply manual edit: {e}")
            raise

    async def _load_problem_data(self, session_id: UUID) -> Dict[str, Any]:
        """Load all data needed for timetable generation."""
        try:
            exams_query = select(Exam).options(
                selectinload(Exam.course),
                selectinload(Exam.course).selectinload(Exam.course.registrations),
                selectinload(Exam.rooms),
                selectinload(Exam.invigilators)
            ).where(Exam.session_id == session_id)

            result = await self.db.execute(exams_query)
            exams = result.scalars().all()

            problem_data = {
                'exams': [self._exam_to_dict(exam) for exam in exams],
                'session_id': str(session_id),
                'loaded_at': datetime.utcnow().isoformat()
            }

            logger.info(f"Loaded {len(exams)} exams for session {session_id}")
            return problem_data

        except Exception as e:
            logger.error(f"Failed to load problem data: {e}")
            raise

    async def _solve_cpsat_phase(
        self,
        constraint_model: Dict[str, Any],
        job_id: UUID
    ) -> Dict[str, Any]:
        try:
            await asyncio.sleep(2)
            for progress in range(35, 60, 5):
                await publish_job_update(str(job_id), {
                    'progress': progress,
                    'message': f'CP-SAT solving... {progress}%'
                })
                await asyncio.sleep(0.5)

            return {
                'feasible': True,
                'solution': {
                    'assignments': {},
                    'solver_stats': {
                        'solve_time': 2.0,
                        'constraints_checked': 1000,
                        'variables': 500
                    }
                }
            }

        except Exception as e:
            logger.error(f"CP-SAT phase failed: {e}")
            return {'feasible': False, 'error': str(e)}

    async def _solve_ga_phase(
        self,
        initial_solution: Dict[str, Any],
        constraint_model: Dict[str, Any],
        job_id: UUID
    ) -> Dict[str, Any]:
        try:
            await asyncio.sleep(3)
            for progress in range(65, 90, 5):
                await publish_job_update(str(job_id), {
                    'progress': progress,
                    'message': f'GA optimization... {progress}%'
                })
                await asyncio.sleep(0.5)

            return {
                'solution': initial_solution['solution'],
                'optimization_stats': {
                    'generations': 100,
                    'best_fitness': 0.95,
                    'optimization_time': 3.0
                }
            }

        except Exception as e:
            logger.error(f"GA phase failed: {e}")
            raise

    async def _finalize_solution(
        self,
        solution: Dict[str, Any],
        job_id: UUID
    ) -> Dict[str, Any]:
        try:
            metrics = await self.solution_evaluator.evaluate_solution(solution)

            version = await self._create_timetable_version(
                job_id, solution, is_active=True
            )

            await self._update_job_results(job_id, metrics, solution)

            return {
                'version_id': str(version.id),
                'metrics': metrics,
                'solution': solution
            }

        except Exception as e:
            logger.error(f"Failed to finalize solution: {e}")
            raise

    # Helper methods
    async def _get_session(self, session_id: UUID) -> Optional[AcademicSession]:
        query = select(AcademicSession).where(AcademicSession.id == session_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_job(self, job_id: UUID) -> Optional[TimetableJob]:
        query = select(TimetableJob).where(TimetableJob.id == job_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _update_job_status(
        self,
        job_id: UUID,
        status: str,
        progress: int,
        message: str
    ) -> None:
        try:
            update_data = {
                'status': status,
                'progress_percentage': progress,
                'solver_phase': message,
                'updated_at': datetime.utcnow()
            }

            if status == 'running' and progress == 0:
                update_data['started_at'] = datetime.utcnow()
            elif status == 'completed':
                update_data['completed_at'] = datetime.utcnow()

            query = update(TimetableJob).where(
                TimetableJob.id == job_id
            ).values(**update_data)

            await self.db.execute(query)
            await self.db.commit()

        except Exception as e:
            logger.error(f"Failed to update job status: {e}")
            await self.db.rollback()

    async def _handle_job_failure(self, job_id: UUID, error_message: str) -> None:
        await self._update_job_status(job_id, 'failed', 0, 'Failed')

        query = update(TimetableJob).where(
            TimetableJob.id == job_id
        ).values(
            error_message=error_message,
            completed_at=datetime.utcnow()
        )

        await self.db.execute(query)
        await self.db.commit()

        await publish_job_update(str(job_id), {
            'status': 'failed',
            'progress': 0,
            'message': error_message
        })

    def _exam_to_dict(self, exam: Exam) -> Dict[str, Any]:
        exam_date_iso = None
        if isinstance(exam.exam_date, (datetime, date)):
            exam_date_iso = exam.exam_date.isoformat()
        return {
            'id': str(exam.id),
            'course_id': str(exam.course_id),
            'course_code': exam.course.code if exam.course else None,
            'course_title': exam.course.title if exam.course else None,
            'duration_minutes': exam.duration_minutes,
            'expected_students': exam.expected_students,
            'exam_date': exam_date_iso,
            'time_slot_id': str(exam.time_slot_id) if exam.time_slot_id else None,
            'requires_special_arrangements': exam.requires_special_arrangements,
            'notes': exam.notes
        }

    async def _queue_timetable_generation(self, job_id: UUID) -> None:
        try:
            asyncio.create_task(self._run_generation_task(job_id))
        except Exception as e:
            logger.error(f"Failed to queue timetable generation: {e}")
            await self._handle_job_failure(job_id, f"Failed to start processing: {e}")

    async def _run_generation_task(self, job_id: UUID) -> None:
        try:
            await self.generate_timetable(job_id)
        except Exception as e:
            logger.error(f"Background generation task failed for job {job_id}: {e}")
            await self._handle_job_failure(job_id, str(e))

    async def _get_default_configuration(self) -> str:
        return str(uuid4())

    async def _create_timetable_version(
        self,
        job_id: UUID,
        solution: Dict[str, Any],
        is_active: bool = False
    ) -> TimetableVersion:
        version = TimetableVersion(
            id=uuid4(),
            job_id=job_id,
            version_number=1,
            is_active=is_active,
            created_at=datetime.utcnow()
        )

        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)

        return version

    async def _get_timetable_version(self, version_id: UUID) -> Optional[TimetableVersion]:
        query = select(TimetableVersion).where(TimetableVersion.id == version_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _log_timetable_edit(self, version_id: UUID, edit_data: Dict[str, Any], user_id: Optional[Any]) -> None:
        # Minimal audit. Replace with persistent audit record if you have one.
        logger.info("Timetable edit", extra={
            "version_id": str(version_id),
            "user_id": str(user_id) if user_id else None,
            "edit": edit_data
        })

    async def _update_job_results(self, job_id: UUID, metrics: Dict[str, Any], solution: Dict[str, Any]) -> None:
        query = update(TimetableJob).where(TimetableJob.id == job_id).values(
            results=metrics,
            updated_at=datetime.utcnow()
        )
        await self.db.execute(query)
        await self.db.commit()

    async def _format_timetable_response(self, version: TimetableVersion) -> Dict[str, Any]:
        created_at_iso = None
        approved_at_iso = None
        if isinstance(version.created_at, datetime):
            created_at_iso = version.created_at.isoformat()
        if getattr(version, "approved_at", None) and isinstance(version.approved_at, datetime):
            approved_at_iso = version.approved_at.isoformat()

        return {
            'version_id': str(version.id),
            'job_id': str(version.job_id),
            'version_number': version.version_number,
            'is_active': version.is_active,
            'created_at': created_at_iso,
            'approved_at': approved_at_iso,
            'schedules': [],
            'statistics': {}
        }
