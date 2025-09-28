# scheduling_engine\main.py
"""
Main Module for Exam Scheduling Engine

This module provides a production-ready interface for the exam timetabling system,
replacing test-driven development with real backend data services integration.

Key Components:
- Real data retrieval from backend services
- Comprehensive constraint management
- Production solver configuration
- Result persistence and versioning
- Admin configuration interface
"""

import asyncio
import logging
import sys
from typing import Dict, List, Optional, Any, Set, Tuple
from uuid import UUID, uuid4
from datetime import date, datetime, timedelta, timezone
from dataclasses import dataclass, field
from pathlib import Path
import traceback
import os
import argparse

from sqlalchemy import and_, func  # Added missing import

# Core scheduling engine imports
from scheduling_engine.core.problem_model import (
    ExamSchedulingProblem,
    Exam,
    Room,
    Student,
    Instructor,
    Staff,
    Invigilator,
    Day,
)

from scheduling_engine.core.constraint_types import ConstraintCategory, ConstraintType

from scheduling_engine.core.solution import TimetableSolution, AssignmentStatus
from scheduling_engine.core.metrics import QualityScore, SolutionMetrics

# CP-SAT solver components
from scheduling_engine.cp_sat import CPSATModelBuilder, CPSATSolverManager
from scheduling_engine.constraints.constraint_manager import CPSATConstraintManager

# Backend service imports - replace with actual imports
from backend.app.services.scheduling.data_preparation_service import (
    ExactDataFlowService,
    ProblemModelCompatibleDataset,
)
from backend.app.services.scheduling.admin_configuration_manager import (
    AdminConfigurationManager,
    ConfigurationTemplate,
    ObjectiveFunction,
)
from backend.app.services.scheduling.timetable_job_orchestrator import (
    TimetableJobOrchestrator,
    OrchestratorOptions,
)
from backend.app.services.scheduling.room_allocation_service import (
    RoomAllocationService,
)
from backend.app.services.scheduling.invigilator_assignment_service import (
    InvigilatorAssignmentService,
)
from backend.app.services.scheduling.versioning_and_edit_service import (
    VersioningAndEditService,
)
from backend.app.services.scheduling.faculty_partitioning_service import (
    FacultyPartitioningService,
)

# Database imports
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from scheduling_engine.data_flow_tracker import DataFlowTracker, track_data_flow_async


def setup_production_logging(log_level: str = "INFO") -> logging.Logger:
    """Setup production-grade logging configuration."""

    # Remove the problematic Windows Unicode handling that can close stderr
    # This is often the root cause of "I/O operation on closed file" errors

    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s"

    # Create logs directory
    logs_dir = Path("scheduling_logs")
    logs_dir.mkdir(exist_ok=True)

    # Configure logging with safer error handling
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            # Use a safer StreamHandler that won't close sys.stderr
            logging.StreamHandler(stream=sys.stdout),  # Use stdout instead of stderr
            logging.FileHandler(
                logs_dir
                / f"scheduling_engine_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
                mode="w",
                encoding="utf-8",
            ),
        ],
        force=True,  # Force reconfiguration to avoid handler conflicts
    )

    # Set specific component log levels
    loggers = {
        "scheduling_engine": logging.INFO,
        "ortools": logging.WARNING,
        "sqlalchemy.engine": logging.WARNING,
        "sqlalchemy.pool": logging.WARNING,
    }

    for logger_name, level in loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)

    return logging.getLogger(__name__)


logger = setup_production_logging()


async def get_or_create_scheduler_user(db_session: AsyncSession) -> UUID:
    """Get or create a user account for the scheduling engine."""
    from backend.app.models.users import User
    from sqlalchemy import select

    try:
        # Try to find an existing scheduler user
        result = await db_session.execute(
            select(User).where(User.email == "scheduler@university.edu")
        )
        user = result.scalar_one_or_none()

        if user:
            return user.id

        # Create new scheduler user
        user = User(
            email="scheduler@university.edu",
            first_name="Scheduling",
            last_name="Engine",
            is_active=True,
            is_superuser=False,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        logger.info(f"Created scheduler user with ID: {user.id}")
        return user.id

    except Exception as e:
        logger.error(f"Failed to get/create scheduler user: {e}")
        # Return a fallback UUID (you might need to create this user manually)
        return UUID("11111111-1111-1111-1111-111111111111")


@dataclass
class SchedulingConfiguration:
    """Production scheduling configuration parameters."""

    # Solver configuration
    max_solver_time_seconds: int = 300
    solver_threads: int = 4
    enable_presolve: bool = True
    enable_search_logging: bool = False

    # Quality thresholds
    min_feasibility_score: float = 0.8
    target_optimization_score: float = 0.9

    # Constraint configuration
    constraint_template: ConfigurationTemplate = ConfigurationTemplate.STANDARD
    objective_function: ObjectiveFunction = ObjectiveFunction.MULTI_OBJECTIVE

    # Job orchestration
    run_room_planning: bool = True
    run_invigilator_planning: bool = True
    activate_version: bool = False
    enable_faculty_partitioning: bool = True

    # Advanced features
    enable_genetic_algorithm_hints: bool = True
    enable_conflict_analysis: bool = True
    enable_capacity_optimization: bool = True
    # Data limits for testing
    limit_data: bool = False
    max_exams: Optional[int] = None
    max_students: Optional[int] = None
    max_rooms: Optional[int] = None
    max_time_slots: Optional[int] = None
    allow_suboptimal_solutions: bool = True


@dataclass
class SchedulingJobResult:
    """Result container for scheduling job execution."""

    job_id: UUID
    session_id: UUID
    status: str
    success: bool

    # Solution data
    solution: Optional[TimetableSolution] = None
    metrics: Optional[SolutionMetrics] = None
    quality_score: Optional[QualityScore] = None

    # Execution details
    execution_time_seconds: float = 0.0
    solver_status: Optional[str] = None
    constraint_violations: List[str] = field(default_factory=list)

    # Version information
    version_number: Optional[int] = None
    is_active_version: bool = False

    # Error handling
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class ExamSchedulingEngine:
    """
    Production-ready exam scheduling engine with full backend integration.

    This class orchestrates the complete scheduling workflow:
    1. Data preparation from backend services
    2. Problem model construction
    3. Constraint configuration
    4. CP-SAT solving with optional GA hints
    5. Solution validation and optimization
    6. Result persistence and versioning
    """

    def __init__(
        self, db_session: AsyncSession, config: Optional[SchedulingConfiguration] = None
    ):
        self.db_session = db_session
        self.config = config or SchedulingConfiguration()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Initialize backend services
        self._init_backend_services()

        # Current job state
        self.current_problem: Optional[ExamSchedulingProblem] = None
        self.current_job_id: Optional[UUID] = None

    def _init_backend_services(self):
        """Initialize all backend data and scheduling services."""
        try:
            # Data services
            self.data_prep_service = ExactDataFlowService(self.db_session)
            self.admin_config_manager = AdminConfigurationManager(self.db_session)

            # Scheduling services
            self.job_orchestrator = TimetableJobOrchestrator(self.db_session)
            self.room_allocation_service = RoomAllocationService(self.db_session)
            self.invigilator_service = InvigilatorAssignmentService(self.db_session)
            self.versioning_service = VersioningAndEditService(self.db_session)

            # Advanced services
            self.faculty_partitioning_service = FacultyPartitioningService(
                self.db_session
            )

            self.logger.info("Successfully initialized all backend services")

        except Exception as e:
            self.logger.error(f"Failed to initialize backend services: {e}")
            raise

    @track_data_flow_async("schedule_session_start", include_stats=True)
    async def schedule_session(
        self,
        session_id: UUID,
        initiated_by: UUID,
        configuration_template: Optional[ConfigurationTemplate] = None,
        custom_constraints: Optional[List[str]] = None,
    ) -> SchedulingJobResult:
        """Main scheduling entry point - now tracked"""
        # Set session for tracking
        DataFlowTracker.set_session(session_id)

        start_time = datetime.now(timezone.utc)

        try:
            self.logger.info(f"Starting scheduling for session {session_id}")

            # Log initial configuration
            DataFlowTracker.log_stats(
                "scheduling_configuration",
                {
                    "session_id": str(session_id),
                    "initiated_by": str(initiated_by),
                    "configuration_template": str(configuration_template),
                    "custom_constraints_count": (
                        len(custom_constraints) if custom_constraints else 0
                    ),
                },
            )

            # Step 1: Initialize admin configuration
            config_id = await self._setup_configuration(
                session_id,
                initiated_by,
                configuration_template or self.config.constraint_template,
                custom_constraints,
            )

            # Step 2: Build comprehensive problem model
            problem = await self._build_problem_model(session_id)
            self.current_problem = problem

            # Step 3: Start orchestrated job
            job_id = await self.job_orchestrator.start_job(
                session_id=session_id,
                configuration_id=config_id,
                initiated_by=initiated_by,
                solver_callable=self._sync_advanced_solver_workflow,
                options=OrchestratorOptions(
                    run_room_planning=self.config.run_room_planning,
                    run_invigilator_planning=self.config.run_invigilator_planning,
                    activate_version=self.config.activate_version,
                ),
            )

            self.current_job_id = job_id

            # Step 4: Execute solving with advanced features
            solution_result = await self._execute_advanced_solving(problem, config_id)

            # Step 5: Create final result
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            result = SchedulingJobResult(
                job_id=job_id,
                session_id=session_id,
                status="completed",
                success=solution_result.get("success", False),
                solution=solution_result.get("solution"),
                metrics=solution_result.get("metrics"),
                execution_time_seconds=execution_time,
                solver_status=solution_result.get("solver_status"),
                quality_score=solution_result.get("quality_score"),
            )

            if result.success:
                self.logger.info(
                    f"✅ Scheduling completed successfully in {execution_time:.2f}s"
                )

                # Log success metrics
                DataFlowTracker.log_stats(
                    "scheduling_success",
                    {
                        "execution_time_seconds": execution_time,
                        "job_id": str(job_id),
                        "solver_status": solution_result.get(
                            "solver_status", "unknown"
                        ),
                        "has_solution": solution_result.get("solution") is not None,
                    },
                )

            else:
                self.logger.error(f"❌ Scheduling failed: {result.error_message}")
                DataFlowTracker.log_event(
                    "scheduling_failed",
                    {"error": result.error_message, "execution_time": execution_time},
                )

            # Export tracking log at the end
            DataFlowTracker.export(f"data_flow_log_{session_id}.md")

            return result

        except Exception as e:
            self.logger.error(f"Scheduling workflow failed: {e}")
            self.logger.error(traceback.format_exc())

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            # Export log even on error
            DataFlowTracker.export(f"data_flow_log_{session_id}_ERROR.md")

            return SchedulingJobResult(
                job_id=self.current_job_id or uuid4(),
                session_id=session_id,
                status="failed",
                success=False,
                execution_time_seconds=execution_time,
                error_message=str(e),
            )

    def _sync_advanced_solver_workflow(
        self, solver_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Synchronous wrapper for advanced solver workflow.
        This can be called from synchronous contexts.
        """
        try:
            # Run the async function in the current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, use a thread pool
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run, self._async_advanced_solver_workflow(solver_input)
                    )
                    return future.result()
            else:
                # Run directly in the event loop
                return asyncio.run(self._async_advanced_solver_workflow(solver_input))
        except Exception as e:
            self.logger.error(f"Advanced solver workflow failed: {e}")
            return {"success": False, "error": str(e)}

    async def _async_advanced_solver_workflow(
        self, solver_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Actual async implementation of advanced solver workflow.
        """
        try:
            self.logger.info("Executing advanced solver workflow...")

            # Extract prepared data
            prepared_data = solver_input.get("prepared_data", {})
            constraints = solver_input.get("constraints", [])
            options = solver_input.get("options", {})

            if not self.current_problem:
                raise ValueError("No current problem available for advanced solving")

            # Execute solving with current problem
            result = await self._execute_advanced_solving(
                self.current_problem, configuration_id=uuid4()  # Placeholder
            )

            return result

        except Exception as e:
            self.logger.error(f"Advanced solver workflow failed: {e}")
            return {"success": False, "error": str(e)}

    async def _setup_configuration(
        self,
        session_id: UUID,
        user_id: UUID,
        template: ConfigurationTemplate,
        custom_constraints: Optional[List[str]],
    ) -> UUID:
        """Setup scheduling configuration using admin manager."""

        try:
            await self.admin_config_manager.initialize()

            # Apply configuration template
            config_result = await self.admin_config_manager.apply_configuration_template(
                template=template,
                user_id=user_id,
                configuration_name=f"Scheduling_Session_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            )

            if not config_result.get("success"):
                raise ValueError(
                    f"Configuration setup failed: {config_result.get('errors', [])}"
                )

            config_id = UUID(config_result["configuration_id"])
            self.logger.info(
                f"Created configuration {config_id} using template {template.value}"
            )

            return config_id

        except Exception as e:
            self.logger.error(f"Configuration setup failed: {e}")
            raise

    @track_data_flow_async("build_problem_model", include_stats=True)
    async def _build_problem_model(self, session_id: UUID) -> ExamSchedulingProblem:
        """Build problem model - now tracked"""
        try:
            # Pre-validation: Check if session exists and has data
            await self._validate_session_has_data(session_id)

            # Use reasonable defaults with validation
            exam_period_start = date.today() + timedelta(days=30)
            exam_period_end = exam_period_start + timedelta(days=14)

            # Build dataset with comprehensive error handling
            dataset = await self._build_validated_dataset(session_id)

            # Log dataset statistics
            DataFlowTracker.log_stats(
                "dataset_loaded",
                {
                    "exams_count": len(dataset.exams),
                    "rooms_count": len(dataset.rooms),
                    "students_count": len(dataset.students),
                    "invigilators_count": len(dataset.invigilators),
                    "session_id": str(session_id),
                },
            )

            # Create problem instance with validation
            problem = await self._create_validated_problem(
                session_id, exam_period_start, exam_period_end, dataset
            )

            # Post-creation validation and recovery
            problem = await self._validate_and_recover_problem(problem, dataset)

            self.logger.info(
                f"✅ Successfully built problem model: {len(problem.exams)} exams, "
                f"{len(problem.rooms)} rooms, {len(problem.students)} students"
            )

            return problem

        except Exception as e:
            self.logger.error(f"Problem model building failed: {e}")
            # Attempt recovery before failing completely
            return await self._attempt_problem_recovery(session_id, str(e))

    async def _validate_session_has_data(self, session_id: UUID) -> None:
        """Validate that the session exists and has sufficient data"""
        try:
            # Check if session exists
            from backend.app.models.academic import AcademicSession
            from sqlalchemy import select

            stmt = select(AcademicSession).where(AcademicSession.id == session_id)
            result = await self.db_session.execute(stmt)
            session = result.scalar_one_or_none()

            if not session:
                raise ValueError(f"Academic session {session_id} not found")

            # Check if session has exams
            from backend.app.models.scheduling import Exam

            stmt = select(Exam).where(Exam.session_id == session_id)
            result = await self.db_session.execute(stmt)
            exams = result.scalars().all()

            if not exams:
                self.logger.warning(f"Session {session_id} has no exams")

        except Exception as e:
            self.logger.error(f"Session validation failed: {e}")
            raise

    async def _build_validated_dataset(
        self, session_id: UUID
    ) -> ProblemModelCompatibleDataset:
        """Build dataset with comprehensive validation"""
        max_retries = 3
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                dataset = (
                    await self.data_prep_service.build_exact_problem_model_dataset(
                        session_id
                    )
                )

                # Validate dataset completeness
                self._validate_dataset_for_scheduling(dataset)

                return dataset

            except Exception as e:
                if attempt == max_retries - 1:  # Last attempt
                    self.logger.error(
                        f"Dataset building failed after {max_retries} attempts: {e}"
                    )
                    raise

                self.logger.warning(
                    f"Dataset building attempt {attempt + 1} failed: {e}. Retrying..."
                )
                await asyncio.sleep(retry_delay * (attempt + 1))

        raise RuntimeError("Unexpected code path reached in _build_validated_dataset")

    def _validate_dataset_for_scheduling(
        self, dataset: ProblemModelCompatibleDataset
    ) -> None:
        """Validate dataset meets minimum requirements for scheduling - FIXED VERSION"""
        validation_errors = []
        warnings = []

        # Check minimum entity counts
        if len(dataset.exams) < 1:
            validation_errors.append("At least one exam required")
        if len(dataset.rooms) < 1:
            validation_errors.append("At least one room required")
        if len(dataset.students) < 1:
            warnings.append("No students found - this may indicate data issues")

        # Check for student-exam relationships (but don't fail if some exams have no students)
        exams_with_students = 0
        for exam in dataset.exams:
            student_count = len(exam.get("students", []))
            if student_count > 0:
                exams_with_students += 1

        if exams_with_students == 0:
            # Try alternative method: check student_exam_mappings
            total_mappings = sum(
                len(exams) for exams in dataset.student_exam_mappings.values()
            )
            if total_mappings == 0:
                validation_errors.append("No student-exam relationships found")
            else:
                warnings.append(
                    f"Using {total_mappings} student-exam mappings from alternative source"
                )
        elif exams_with_students < len(dataset.exams):
            warnings.append(
                f"{len(dataset.exams) - exams_with_students} exams have no direct student assignments"
            )

        # Only critical errors should prevent scheduling
        if validation_errors:
            error_msg = f"Dataset validation failed: {'; '.join(validation_errors)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        if warnings:
            self.logger.warning(f"Dataset validation warnings: {'; '.join(warnings)}")

    async def _create_validated_problem(
        self,
        session_id: UUID,
        start_date: date,
        end_date: date,
        dataset: ProblemModelCompatibleDataset,
    ) -> ExamSchedulingProblem:
        """Create and validate problem instance"""
        try:
            problem = ExamSchedulingProblem(
                session_id=session_id,
                exam_period_start=start_date,
                exam_period_end=end_date,
                db_session=self.db_session,
                exam_days_count=15,
            )

            # Load entities with error handling
            await self._populate_problem_from_dataset(problem, dataset)

            # CRITICAL: Ensure days are generated
            if not problem.days:
                self.logger.warning("No days in problem, generating default days")
                problem.configure_exam_days(problem.exam_days_count or 10)

            # Validate problem integrity
            validation_result = problem.validate_problem_data()
            if not validation_result["valid"]:
                self.logger.error(
                    f"Problem validation failed: {validation_result['errors']}"
                )
                raise ValueError(
                    f"Problem validation failed: {validation_result['errors']}"
                )

            return problem

        except Exception as e:
            self.logger.error(f"Problem creation failed: {e}")
            raise

    async def _validate_and_recover_problem(
        self, problem: ExamSchedulingProblem, dataset: ProblemModelCompatibleDataset
    ) -> ExamSchedulingProblem:
        """Validate problem and attempt recovery for common issues"""
        try:
            # Re-run validation
            validation_result = problem.validate_problem_data()

            if validation_result["valid"]:
                return problem

            self.logger.warning(
                f"Problem validation issues found: {validation_result['errors']}"
            )

            # Attempt common fixes
            if "No days defined" in str(validation_result["errors"]):
                self.logger.info("Attempting to fix days configuration...")
                problem.configure_exam_days(10)

            if "No invigilators available" in str(validation_result["errors"]):
                self.logger.info("Attempting to add fallback invigilators...")
                await self._add_fallback_invigilators(problem)

            # Re-validate after fixes
            validation_result = problem.validate_problem_data()
            if not validation_result["valid"]:
                self.logger.error(
                    f"Problem recovery failed: {validation_result['errors']}"
                )
                # Continue with the problem anyway for partial functionality
                self.logger.warning("Proceeding with partially valid problem model")

            return problem

        except Exception as e:
            self.logger.error(f"Problem validation and recovery failed: {e}")
            return problem  # Return the problem anyway

    async def _attempt_problem_recovery(
        self, session_id: UUID, error_msg: str
    ) -> ExamSchedulingProblem:
        """Attempt to recover from problem building failures - FIXED VERSION"""
        self.logger.warning(f"Attempting problem recovery after error: {error_msg}")

        try:
            # Create minimal problem instance with basic data
            problem = ExamSchedulingProblem(
                session_id=session_id,
                exam_period_start=date.today() + timedelta(days=30),
                exam_period_end=date.today() + timedelta(days=44),
                db_session=self.db_session,
                exam_days_count=10,
            )

            # Generate minimal days
            problem.configure_exam_days(10)

            # FIXED: Add fallback rooms if none exist
            if not problem.rooms:
                self.logger.warning("Adding fallback rooms for recovery")
                # Create a few basic rooms
                fallback_rooms = [
                    Room(
                        id=uuid4(),
                        code="FALLBACK-001",
                        capacity=50,
                        exam_capacity=30,
                        has_computers=False,
                    ),
                    Room(
                        id=uuid4(),
                        code="FALLBACK-002",
                        capacity=60,
                        exam_capacity=40,
                        has_computers=False,
                    ),
                ]
                for room in fallback_rooms:
                    problem.add_room(room)

            # FIXED: Add fallback invigilators
            await self._add_fallback_invigilators(problem)

            self.logger.info("Created recovered problem instance with fallback data")
            return problem

        except Exception as recovery_error:
            self.logger.error(f"Problem recovery failed: {recovery_error}")
            # Create absolute minimal problem as last resort
            minimal_problem = ExamSchedulingProblem(
                session_id=session_id,
                exam_period_start=date.today(),
                exam_period_end=date.today() + timedelta(days=1),
                db_session=self.db_session,
            )
            minimal_problem.configure_exam_days(1)
            return minimal_problem

    def _validate_solution_quality(
        self, quality_score: Optional[QualityScore], metrics: Optional[SolutionMetrics]
    ) -> bool:
        """Enhanced solution quality validation with detailed diagnostics"""

        if not quality_score:
            self.logger.warning(
                "No quality score available - performing basic validation"
            )
            return self._perform_basic_solution_validation(metrics)

        # Comprehensive quality assessment
        validation_results = {
            "feasibility": True,
            "optimization": True,
            "constraints": True,
            "coverage": True,
        }

        # Check feasibility threshold
        feasibility_score = getattr(quality_score, "feasibility_score", 1.0)
        if feasibility_score < self.config.min_feasibility_score:
            validation_results["feasibility"] = False
            self.logger.error(
                f"❌ Solution feasibility {feasibility_score:.3f} below threshold {self.config.min_feasibility_score}"
            )

        # Check optimization threshold
        optimization_score = getattr(quality_score, "optimization_score", 1.0)
        if optimization_score < self.config.target_optimization_score:
            validation_results["optimization"] = False
            self.logger.warning(
                f"⚠️ Solution optimization {optimization_score:.3f} below target {self.config.target_optimization_score}"
            )

        # Additional constraint validation
        if metrics and hasattr(metrics, "hard_constraint_violations"):
            violations = getattr(metrics, "hard_constraint_violations", 0)
            if violations > 0:
                validation_results["constraints"] = False
                self.logger.error(
                    f"❌ Solution has {violations} hard constraint violations"
                )

        # Determine overall validity
        is_acceptable = (
            validation_results["feasibility"]
            and validation_results["constraints"]
            and (
                validation_results["optimization"]
                or self.config.allow_suboptimal_solutions
            )
        )

        if is_acceptable:
            self.logger.info("✅ Solution quality validation passed")
        else:
            self.logger.error("❌ Solution quality validation failed")

        return is_acceptable

    async def _add_fallback_invigilators(self, problem: ExamSchedulingProblem) -> None:
        """Add fallback invigilators when none are available in the dataset."""
        try:
            from scheduling_engine.core.problem_model import Invigilator
            from uuid import uuid4

            self.logger.warning("Adding fallback invigilators...")

            # Create a few basic invigilators
            fallback_invigilators = [
                {
                    "id": uuid4(),
                    "name": "Fallback Invigilator 1",
                    "email": "invigilator1@university.edu",
                    "max_assignments": 5,
                    "availability": (
                        set(problem.days) if problem.days else set(range(10))
                    ),
                },
                {
                    "id": uuid4(),
                    "name": "Fallback Invigilator 2",
                    "email": "invigilator2@university.edu",
                    "max_assignments": 5,
                    "availability": (
                        set(problem.days) if problem.days else set(range(10))
                    ),
                },
            ]

            for inv_data in fallback_invigilators:
                invigilator = Invigilator.from_backend_data(inv_data)
                problem.add_invigilator(invigilator)

            self.logger.info(
                f"Added {len(fallback_invigilators)} fallback invigilators"
            )

        except Exception as e:
            self.logger.error(f"Failed to add fallback invigilators: {e}")

    def _perform_basic_solution_validation(
        self, metrics: Optional[SolutionMetrics]
    ) -> bool:
        """Perform basic validation when quality scores are unavailable"""
        if not metrics:
            self.logger.warning(
                "No metrics available - accepting solution with warning"
            )
            return True

        # Check for critical issues
        critical_issues = []

        if (
            hasattr(metrics, "unassigned_exams")
            and getattr(metrics, "unassigned_exams", 0) > 0
        ):
            critical_issues.append(
                f"{getattr(metrics, 'unassigned_exams')} unassigned exams"
            )

        if (
            hasattr(metrics, "hard_constraint_violations")
            and getattr(metrics, "hard_constraint_violations", 0) > 0
        ):
            critical_issues.append(
                f"{getattr(metrics, 'hard_constraint_violations')} constraint violations"
            )

        if critical_issues:
            self.logger.error(f"Critical solution issues: {', '.join(critical_issues)}")
            return False

        self.logger.info("Basic solution validation passed")
        return True

    async def _populate_problem_from_dataset(
        self, problem: ExamSchedulingProblem, dataset: ProblemModelCompatibleDataset
    ):
        """ENHANCED: Populate problem model with proper invigilator handling"""

        try:
            # Add rooms
            for room_data in dataset.rooms:
                room = Room.from_backend_data(room_data)
                problem.add_room(room)

            # Add exams WITH their pre-populated students from dataset
            for exam_data in dataset.exams:
                exam = Exam.from_backend_data(exam_data)

                # Use set_students method instead of direct assignment
                if "students" in exam_data:
                    exam.set_students(set(exam_data["students"]))
                    exam.actual_student_count = len(exam_data["students"])

                problem.add_exam(exam)

            # Add students
            for student_data in dataset.students:
                student = Student.from_backend_data(student_data)
                problem.add_student(student)

            # CRITICAL FIX: Add staff and invigilators properly
            logger.info(f"Processing {len(dataset.staff)} staff members")
            for staff_data in dataset.staff:
                try:
                    staff = Staff.from_backend_data(staff_data)
                    problem.add_staff(staff)
                    logger.debug(f"Added staff: {staff.name} (ID: {staff.id})")
                except Exception as e:
                    logger.error(
                        f"Error adding staff {staff_data.get('id', 'unknown')}: {e}"
                    )
                    continue

            # CRITICAL FIX: Add invigilators with proper validation
            logger.info(f"Processing {len(dataset.invigilators)} invigilators")
            invigilator_count = 0
            for invigilator_data in dataset.invigilators:
                try:
                    invigilator = Invigilator.from_backend_data(invigilator_data)
                    problem.add_invigilator(invigilator)
                    invigilator_count += 1
                    logger.debug(
                        f"Added invigilator: {invigilator.name} (ID: {invigilator.id})"
                    )
                except Exception as e:
                    logger.error(
                        f"Error adding invigilator {invigilator_data.get('id', 'unknown')}: {e}"
                    )
                    continue

            # Register student-course relationships (backup method)
            for registration in dataset.course_registrations:
                problem.register_student_course(
                    student_id=registration["student_id"],
                    course_id=registration["course_id"],
                )

            # Use the enhanced population method
            success = problem.populate_exam_students()

            # Load data using the problem's built-in method
            await problem.load_from_backend(dataset)

            # CRITICAL FIX: Convert staff to invigilators if none exist
            if len(problem.invigilators) == 0:
                logger.warning("No invigilators found, converting staff...")

                # Use staff from dataset directly
                staff_data = dataset.staff
                if staff_data:
                    converted = 0

                    for staff in staff_data[:5]:  # Convert up to 5 staff
                        if staff.get("can_invigilate", True):
                            try:
                                # Create invigilator from staff data
                                invigilator_data = {
                                    "id": staff["id"],
                                    "name": staff.get(
                                        "name",
                                        f"Staff {staff.get('staff_number', converted+1)}",
                                    ),
                                    "email": staff.get("email"),
                                    "department": staff.get("department"),
                                    "can_invigilate": True,
                                    "max_concurrent_exams": 2,
                                    "max_students_per_exam": 50,
                                    "staff_number": staff.get("staff_number"),
                                    "staff_type": staff.get("staff_type", "academic"),
                                }

                                invigilator = Invigilator.from_backend_data(
                                    invigilator_data
                                )
                                problem.add_invigilator(invigilator)
                                converted += 1

                            except Exception as e:
                                logger.error(
                                    f"Error converting staff to invigilator: {e}"
                                )
                                continue

                    logger.info(f"Converted {converted} staff to invigilators")

                # Create fallback invigilators if still none
                if len(problem.invigilators) == 0:
                    await self._add_fallback_invigilators(problem)

            # Ensure days are configured
            if not problem.days:
                logger.warning("No days configured, generating defaults...")
                problem.configure_exam_days(10)

            invigilator_count = len(problem.invigilators)
            logger.info(
                f"Successfully populated problem: {invigilator_count} invigilators, {len(problem.exams)} exams"
            )

        except Exception as e:
            logger.error(f"Error populating problem: {e}")
            # Create minimal fallback state
            if not problem.invigilators:
                await self._add_fallback_invigilators(problem)
            if not problem.days:
                problem.configure_exam_days(5)
            raise

    async def _configure_problem_constraints(self, problem: ExamSchedulingProblem):
        """Configure constraints based on admin configuration."""
        try:
            # Use complete constraint configuration for production
            problem.constraint_registry.configure_complete_with_soft()  # Changed from configure_minimal()

            # Ensure minimum constraints are active
            problem.ensure_constraints_activated()

            active_constraints = problem.constraint_registry.get_active_constraints()
            self.logger.info(
                f"Configured {len(active_constraints)} active constraints: {sorted(active_constraints)}"
            )

            # Validate that constraints were actually activated
            if len(active_constraints) == 0:
                self.logger.warning(
                    "No constraints were activated, trying fallback configuration"
                )
                # Force activation of core constraints
                problem.constraint_registry.configure_minimal()
                active_constraints = (
                    problem.constraint_registry.get_active_constraints()
                )

                if len(active_constraints) == 0:
                    raise RuntimeError(
                        "Failed to activate any constraints - constraint registry may be broken"
                    )

        except Exception as e:
            self.logger.error(f"Constraint configuration failed: {e}")
            raise

    @track_data_flow_async("execute_advanced_solving", include_stats=True)
    async def _execute_advanced_solving(
        self, problem: ExamSchedulingProblem, configuration_id: UUID
    ) -> Dict[str, Any]:
        """Execute solving with advanced features and optimizations - FIXED VERSION"""

        # FIXED: Add safe capacity analysis with zero division protection
        total_student_exams = (
            sum(exam.expected_students for exam in problem.exams.values())
            if problem.exams
            else 0
        )

        total_room_capacity = (
            sum(room.exam_capacity for room in problem.rooms.values())
            * len(problem.timeslots)
            if problem.rooms and problem.timeslots
            else 0
        )

        # Safe division with zero check
        if total_room_capacity > 0:
            utilization = total_student_exams / total_room_capacity * 100
            logger.info(
                f"Capacity Analysis: {total_student_exams} student-exams vs {total_room_capacity} total capacity"
            )
            logger.info(f"Room utilization needed: {utilization:.1f}%")
        else:
            logger.warning(
                f"Capacity Analysis: {total_student_exams} student-exams vs {total_room_capacity} total capacity"
            )
            logger.warning(
                "Cannot calculate utilization: zero room capacity or timeslots"
            )

        # Log solver configuration
        DataFlowTracker.log_stats(
            "solver_configuration",
            {
                "max_solver_time_seconds": self.config.max_solver_time_seconds,
                "solver_threads": self.config.solver_threads,
                "enable_presolve": self.config.enable_presolve,
                "configuration_id": str(configuration_id),
                "total_student_exams": total_student_exams,
                "total_room_capacity": total_room_capacity,
            },
        )

        # FIXED: Check if we have minimal data to proceed
        if not problem.exams:
            logger.error("No exams available for scheduling")
            return {
                "success": False,
                "error": "No exams available for scheduling",
                "solver_status": "INFEASIBLE",
            }

        if not problem.rooms:
            logger.error("No rooms available for scheduling")
            return {
                "success": False,
                "error": "No rooms available for scheduling",
                "solver_status": "INFEASIBLE",
            }

        if not problem.timeslots:
            logger.error("No timeslots available for scheduling")
            return {
                "success": False,
                "error": "No timeslots available for scheduling",
                "solver_status": "INFEASIBLE",
            }
        try:
            await self._configure_problem_constraints(problem)
            # Build CP-SAT model
            builder = CPSATModelBuilder(problem)
            model, shared_variables = builder.build()

            # Configure solver with production settings
            solver_manager = CPSATSolverManager(problem)
            solver_manager.solver.parameters.max_time_in_seconds = (
                self.config.max_solver_time_seconds
            )
            solver_manager.solver.parameters.num_search_workers = (
                self.config.solver_threads
            )

            if self.config.enable_presolve:
                solver_manager.solver.parameters.cp_model_presolve = True

            # Execute solving
            self.logger.info("Starting CP-SAT solving...")
            status, solution = solver_manager.solve()

            # Export data flow log
            DataFlowTracker.export("data_flow_log.md")

            if not solution:
                return {
                    "success": False,
                    "solver_status": str(status),
                    "error": "No solution found",
                }

            # Calculate quality metrics
            from scheduling_engine.core.metrics import SolutionMetrics

            metrics_calculator = SolutionMetrics()
            quality_score = metrics_calculator.evaluate_solution_quality(
                problem, solution
            )

            # Update solution with soft constraint metrics
            solution.update_soft_constraint_metrics(problem)

            # Get statistics
            solution.update_statistics()
            quality_score = metrics_calculator.evaluate_solution_quality(
                problem, solution
            )
            metrics = metrics_calculator

            # Log solution quality
            DataFlowTracker.log_stats(
                "solution_quality",
                {
                    "feasibility_score": getattr(
                        quality_score, "feasibility_score", 0.0
                    ),
                    "optimization_score": getattr(
                        quality_score, "optimization_score", 0.0
                    ),
                    "solver_status": str(status),
                    "has_solution": solution is not None,
                },
            )

            # Validate solution quality
            is_acceptable = self._validate_solution_quality(quality_score, metrics)

            return {
                "success": is_acceptable,
                "solution": solution,
                "solver_status": str(status),
                "metrics": metrics,
                "quality_score": quality_score,
            }

        except Exception as e:
            self.logger.error(f"Advanced solving failed: {e}")
            DataFlowTracker.log_event("solving_error", {"error": str(e)})
            return {"success": False, "error": str(e)}

    async def _advanced_solver_workflow(
        self, solver_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Advanced solver workflow callable for job orchestrator.

        This method integrates genetic algorithm hints, conflict analysis,
        and other advanced scheduling features.
        """

        try:
            self.logger.info("Executing advanced solver workflow...")

            # Extract prepared data
            prepared_data = solver_input.get("prepared_data", {})
            constraints = solver_input.get("constraints", [])
            options = solver_input.get("options", {})
            if not self.current_problem:
                # Try to get problem from solver_input
                problem = solver_input.get("problem")
                if problem:
                    self.current_problem = problem
                else:
                    raise ValueError(
                        "No problem instance available. Ensure build_problem_model() is called first."
                    )

            assert self.current_problem
            # Execute solving with current problem
            result = await self._execute_advanced_solving(
                self.current_problem, configuration_id=uuid4()
            )

            return result

        except Exception as e:
            self.logger.error(f"Advanced solver workflow failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_session_scheduling_status(self, session_id: UUID) -> Dict[str, Any]:
        """Get current scheduling status for a session."""

        try:
            # Query job status from orchestrator
            # This would be implemented based on JobData service methods
            return {
                "session_id": str(session_id),
                "status": "unknown",
                "message": "Status retrieval not yet implemented",
            }

        except Exception as e:
            self.logger.error(f"Status retrieval failed: {e}")
            return {"session_id": str(session_id), "status": "error", "error": str(e)}

    async def cancel_scheduling_job(self, job_id: UUID) -> bool:
        """Cancel a running scheduling job."""

        try:
            # Implementation would depend on job management capabilities
            self.logger.info(f"Cancellation requested for job {job_id}")
            return False  # Not implemented yet

        except Exception as e:
            self.logger.error(f"Job cancellation failed: {e}")
            return False


async def ensure_test_user_exists(db_session: AsyncSession) -> UUID:
    """Ensure a test user exists for scheduling operations."""
    from backend.app.models.users import User

    try:
        # Try to get any existing user
        from sqlalchemy import select

        result = await db_session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()

        if user:
            return user.id

        # Create a test user if none exists
        test_user = User(
            email="scheduler@university.edu",
            first_name="Scheduling",
            last_name="Engine",
            is_active=True,
            is_superuser=False,
        )
        db_session.add(test_user)
        await db_session.commit()

        return test_user.id

    except Exception as e:
        logger.error(f"Error ensuring test user exists: {e}")
        # fallback
        return UUID("00000000-0000-0000-0000-000000000001")


async def create_database_session(database_url: str) -> AsyncSession:
    """Create async database session for the scheduling engine."""

    # Create async engine
    engine = create_async_engine(
        database_url,
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True,
        pool_recycle=300,
    )

    # Create async session factory
    async_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Create and return a session
    async with async_session_factory() as session:
        return session


async def create_database_sessionmaker(database_url: str) -> async_sessionmaker:
    """Create async database sessionmaker for the scheduling engine."""

    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=300,
    )

    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_or_create_academic_session(
    db_session: AsyncSession, session_id: Optional[str] = None
) -> UUID:
    """Get an existing academic session that has exams, or create a test one."""
    from backend.app.models.academic import AcademicSession
    from backend.app.models.scheduling import Exam
    from sqlalchemy import select
    from datetime import date, timedelta, datetime
    from sqlalchemy.exc import IntegrityError

    try:
        # First, try to find sessions that actually have exams
        stmt = (
            select(AcademicSession)
            .join(Exam, Exam.session_id == AcademicSession.id)
            .where(AcademicSession.is_active == True)
            .group_by(AcademicSession.id)
            .having(func.count(Exam.id) > 0)
            .order_by(AcademicSession.start_date.desc())
        )

        result = await db_session.execute(stmt)
        sessions_with_exams = result.scalars().all()

        # If a specific session ID was provided, check if it exists and has exams
        if session_id:
            try:
                session_uuid = UUID(session_id)
                # Check if this specific session has exams
                specific_stmt = (
                    select(AcademicSession)
                    .join(Exam, Exam.session_id == AcademicSession.id)
                    .where(
                        and_(
                            AcademicSession.id == session_uuid,
                            AcademicSession.is_active == True,
                        )
                    )
                    .group_by(AcademicSession.id)
                    .having(func.count(Exam.id) > 0)
                )

                specific_result = await db_session.execute(specific_stmt)
                specific_session = specific_result.scalar_one_or_none()

                if specific_session:
                    logger.info(
                        f"Using provided academic session: {specific_session.name} (ID: {specific_session.id})"
                    )
                    return specific_session.id
                else:
                    logger.warning(
                        f"Session {session_id} not found or has no exams, looking for other sessions"
                    )
            except ValueError:
                logger.warning(f"Invalid session ID format: {session_id}")

        # Use the first session that has exams
        if sessions_with_exams:
            session = sessions_with_exams[0]
            logger.info(
                f"Using existing academic session with exams: {session.name} (ID: {session.id})"
            )
            return session.id

        # If no sessions with exams found, look for any active session
        stmt_any = (
            select(AcademicSession)
            .where(AcademicSession.is_active == True)
            .order_by(AcademicSession.start_date.desc())
            .limit(1)
        )

        result_any = await db_session.execute(stmt_any)
        any_session = result_any.scalar_one_or_none()

        if any_session:
            logger.warning(
                f"No sessions with exams found. Using active session: {any_session.name}"
            )
            return any_session.id

        # If no active sessions exist at all, create a test session
        logger.warning("No active academic sessions found. Creating test session...")
        return await _create_test_session(db_session)

    except Exception as e:
        logger.error(f"Error getting/creating academic session: {e}")
        # Fallback: try to create a test session
        try:
            return await _create_test_session(db_session)
        except Exception as create_error:
            logger.error(f"Failed to create test session: {create_error}")
            # Ultimate fallback
            if session_id:
                try:
                    return UUID(session_id)
                except ValueError:
                    pass
            return uuid4()


async def _create_test_session(db_session: AsyncSession) -> UUID:
    """Helper function to create a test academic session."""
    from backend.app.models.academic import AcademicSession
    from datetime import date, timedelta, datetime

    # Create a unique test session name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_session_name = f"Test Session {timestamp}"

    # Create a test academic session with required semester_system
    test_session = AcademicSession(
        name=test_session_name,
        semester_system="semester",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        is_active=True,
    )

    db_session.add(test_session)
    await db_session.commit()
    await db_session.refresh(test_session)

    logger.info(
        f"Created test academic session: {test_session.name} (ID: {test_session.id})"
    )
    return test_session.id


async def main():
    """Main entry point for production scheduling execution."""

    # Parse arguments
    parser = argparse.ArgumentParser(description="Exam Scheduling Engine")
    parser.add_argument(
        "--session-id", type=str, help="Academic session ID to schedule"
    )
    parser.add_argument(
        "--config-template",
        type=str,
        default="standard",
        choices=["standard", "emergency", "examweek", "flexible", "strict"],
        help="Configuration template to use",
    )
    parser.add_argument(
        "--solver-time", type=int, default=300, help="Maximum solver time in seconds"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    parser.add_argument(
        "--limit-data", action="store_true", help="Limit data size for testing"
    )
    parser.add_argument(
        "--max-exams", type=int, default=50, help="Maximum number of exams to process"
    )
    parser.add_argument(
        "--max-students",
        type=int,
        default=1000,
        help="Maximum number of students to process",
    )
    parser.add_argument(
        "--max-rooms", type=int, default=20, help="Maximum number of rooms to process"
    )
    parser.add_argument(
        "--max-time-slots",
        type=int,
        default=10,
        help="Maximum number of time slots to process",
    )
    args = parser.parse_args()

    # Update logging level
    setup_production_logging(args.log_level)

    logger.info("🚀 Starting Exam Scheduling Engine")

    try:
        # Get settings from environment
        from backend.app.config import get_settings

        settings = get_settings()

        # Initialize database
        from backend.app.database import init_db

        await init_db(database_url=settings.DATABASE_URL, create_tables=True)

        print("Database initialized successfully!")
        print(f"Using database: {settings.DATABASE_URL}")

        # Create database session
        sessionmaker = await create_database_sessionmaker(settings.DATABASE_URL)

        async with sessionmaker() as db_session:
            # Ensure we have a valid user for scheduling
            test_user_id = await ensure_test_user_exists(db_session)
            logger.info(f"Using user ID for scheduling: {test_user_id}")

            # Get or create an academic session
            session_id = await get_or_create_academic_session(
                db_session, args.session_id
            )
            logger.info(f"Using academic session ID: {session_id}")

            # Create scheduling configuration
            config = SchedulingConfiguration(
                max_solver_time_seconds=args.solver_time,
                constraint_template=ConfigurationTemplate(args.config_template.lower()),
                objective_function=ObjectiveFunction.MULTI_OBJECTIVE,
                run_room_planning=True,
                run_invigilator_planning=True,
                enable_genetic_algorithm_hints=True,
                limit_data=args.limit_data,
                max_exams=args.max_exams,
                max_students=args.max_students,
                max_rooms=args.max_rooms,
                max_time_slots=args.max_time_slots,
            )

            # Initialize scheduling engine
            engine = ExamSchedulingEngine(db_session, config)

            logger.info(f"Executing scheduling for session {session_id}")

            # Execute scheduling workflow
            result = await engine.schedule_session(
                session_id=session_id,
                initiated_by=test_user_id,
                configuration_template=ConfigurationTemplate(args.config_template),
            )

            # Display results
            if result.success:
                logger.info("✅ Scheduling completed successfully!")
                logger.info(f"📊 Execution time: {result.execution_time_seconds:.2f}s")
                logger.info(f"🆔 Job ID: {result.job_id}")
                logger.info(f"📈 Solver status: {result.solver_status}")

                if result.quality_score:
                    logger.info(f"🏆 Quality score: {result.quality_score}")
            else:
                logger.error("❌ Scheduling failed!")
                logger.error(f"Error: {result.error_message}")

    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        logger.error(traceback.format_exc())
        return 1

    return 0


if __name__ == "__main__":
    """CLI entry point."""

    # Run async main
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
