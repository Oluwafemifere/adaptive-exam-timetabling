# scheduling_engine/main.py
"""
Main Module for Exam Scheduling Engine (CLI Task Dispatcher)
...
"""
import asyncio
import logging
import sys
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime, date, timedelta
from pathlib import Path
import traceback
import argparse

from backend.app.tasks import generate_timetable_task, celery_app
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# --- START OF FIX ---
from sqlalchemy import select, func, and_, text

# --- END OF FIX ---

# (setup_production_logging, create_database_sessionmaker, ensure_user_exists, get_or_create_academic_session, get_end_date_by_weekdays functions remain the same)
# ...


def setup_production_logging(log_level: str = "INFO") -> logging.Logger:
    """Setup production-grade logging configuration."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logs_dir = Path("scheduling_logs")
    logs_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                logs_dir
                / f"scheduling_cli_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
                mode="w",
                encoding="utf-8",
            ),
        ],
        force=True,
    )

    loggers = {
        "scheduling_engine": logging.INFO,
        "backend.app.tasks": logging.INFO,
        "ortools": logging.WARNING,
        "sqlalchemy.engine": logging.WARNING,
    }
    for logger_name, level in loggers.items():
        logging.getLogger(logger_name).setLevel(level)

    return logging.getLogger(__name__)


logger = setup_production_logging()


async def create_database_sessionmaker(database_url: str) -> async_sessionmaker:
    """Create async database sessionmaker for the scheduling engine."""
    engine = create_async_engine(database_url, echo=False)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def ensure_user_exists(db_session: AsyncSession) -> UUID:
    """Ensure a user exists for scheduling operations, creating one if necessary."""
    from backend.app.models.users import User

    try:
        result = await db_session.execute(
            select(User).where(User.email == "scheduler@university.edu")
        )
        user = result.scalar_one_or_none()
        if user:
            logger.info(f"Using existing scheduler user: {user.id}")
            return user.id

        logger.info("Creating a new scheduler user...")
        new_user = User(
            email="scheduler@university.edu",
            first_name="Scheduling",
            last_name="EngineCLI",
            is_active=True,
        )
        db_session.add(new_user)
        await db_session.commit()
        await db_session.refresh(new_user)
        logger.info(f"Created new scheduler user: {new_user.id}")
        return new_user.id
    except Exception as e:
        logger.error(f"Error ensuring user exists: {e}", exc_info=True)
        raise


async def get_or_create_academic_session(
    db_session: AsyncSession, session_id_str: Optional[str]
) -> UUID:
    """Get an existing academic session that has exams, or create a test one."""
    from backend.app.models.academic import AcademicSession
    from backend.app.models.scheduling import Exam

    if session_id_str:
        try:
            session_uuid = UUID(session_id_str)
            stmt = select(AcademicSession).where(AcademicSession.id == session_uuid)
            res = await db_session.execute(stmt)
            if res.scalar_one_or_none():
                logger.info(f"Using provided session ID: {session_uuid}")
                return session_uuid
            else:
                logger.warning(
                    f"Provided session ID {session_uuid} not found. Searching for another session."
                )
        except ValueError:
            logger.warning(f"Invalid session ID format: {session_id_str}")

    # Find the most recent active session with exams
    stmt = (
        select(AcademicSession.id)
        .join(Exam, Exam.session_id == AcademicSession.id)
        .where(AcademicSession.is_active == True)
        .group_by(AcademicSession.id)
        .having(func.count(Exam.id) > 0)
        .order_by(AcademicSession.start_date.desc())
        .limit(1)
    )
    result = await db_session.execute(stmt)
    session_id = result.scalar_one_or_none()
    if session_id:
        logger.info(f"Found existing session with exams: {session_id}")
        return session_id

    # Fallback: create a test session
    logger.warning("No suitable academic session found. Creating a test session.")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_session = AcademicSession(
        name=f"Test Session {timestamp}",
        semester_system="semester",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=90),
        is_active=True,
    )
    db_session.add(test_session)
    await db_session.commit()
    return test_session.id


def get_end_date_by_weekdays(start_date: date, num_weekdays: int) -> date:
    """
    Calculates an end date by adding a specific number of weekdays (Mon-Fri)
    to a given start date.
    """
    if num_weekdays <= 0:
        return start_date

    weekdays_counted = 0
    current_date = start_date

    # Ensure the start date is not a weekend
    while current_date.weekday() >= 5:  # Saturday or Sunday
        logger.info(f"Start date {current_date} is a weekend, moving to next Monday.")
        current_date += timedelta(days=1)

    # We decrement the day so that the start date itself is included in the count
    effective_start_date = current_date
    current_date -= timedelta(days=1)

    while weekdays_counted < num_weekdays:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5:  # Monday to Friday are 0-4
            weekdays_counted += 1

    logger.info(
        f"Calculated exam period: {effective_start_date} to {current_date} ({num_weekdays} weekdays)."
    )
    return current_date


# --- START OF FIX ---
async def create_job_in_db(db: AsyncSession, session_id: UUID, user_id: UUID) -> UUID:
    """Creates the initial job record by calling the PostgreSQL function."""
    logger.info("Creating job record via database function...")
    query = text("SELECT exam_system.create_timetable_job(:session_id, :user_id)")
    result = await db.execute(query, {"session_id": session_id, "user_id": user_id})
    new_job_id = result.scalar_one()
    await db.commit()
    logger.info(f"Successfully created job with ID: {new_job_id}")
    return new_job_id


# --- END OF FIX ---


async def main():
    """Main entry point for dispatching a scheduling job via Celery."""
    parser = argparse.ArgumentParser(description="Exam Scheduling Engine CLI")
    # ... (parser arguments remain the same)
    parser.add_argument(
        "--session-id", type=str, help="Specific academic session ID to schedule."
    )
    parser.add_argument(
        "--solver-time", type=int, default=300, help="Maximum solver time in seconds."
    )
    parser.add_argument(
        "--exam-days",
        type=int,
        default=10,
        help="The number of weekdays the schedule should span.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    setup_production_logging(args.log_level)
    logger.info("🚀 Starting Exam Scheduling Engine CLI Dispatcher")

    try:
        from backend.app.core.config import settings
        from backend.app.models.academic import AcademicSession

        logger.info("Connecting to the database...")
        async_session_factory = await create_database_sessionmaker(
            settings.DATABASE_URL
        )

        async with async_session_factory() as db_session:
            user_id = await ensure_user_exists(db_session)
            session_id = await get_or_create_academic_session(
                db_session, args.session_id
            )

            # --- START OF FIX ---
            # Create the job in the database using the new function
            job_id = await create_job_in_db(db_session, session_id, user_id)
            # We no longer need a placeholder configuration_id here
            # --- END OF FIX ---

            session_result = await db_session.execute(
                select(AcademicSession).where(AcademicSession.id == session_id)
            )
            academic_session = session_result.scalar_one()
            start_date = academic_session.start_date
            end_date = get_end_date_by_weekdays(start_date, args.exam_days)

        options = {
            "exam_days": args.exam_days,
            "solver_time_limit": args.solver_time,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        logger.info(f"Dispatching Celery task 'generate_timetable' for job {job_id}")
        logger.info(f"  - Session ID: {session_id}")
        logger.info(f"  - User ID: {user_id}")
        logger.info(f"  - Options: {options}")

        task_signature = generate_timetable_task.s(
            job_id=str(job_id),
            session_id=str(session_id),
            # Pass the job_id as the configuration_id placeholder, though it's not used by the task for job creation anymore
            configuration_id=str(job_id),
            user_id=str(user_id),
            options=options,
        )

        async_result = task_signature.apply_async()
        logger.info(
            f"Task dispatched with Celery ID: {async_result.id}. Waiting for completion..."
        )
        task_result = async_result.get(timeout=args.solver_time + 60)

        # ... (result display remains the same)
        logger.info("--- SCHEDULING JOB COMPLETE ---")
        if isinstance(task_result, dict) and task_result.get("success"):
            logger.info("✅ Status: SUCCESS")
            logger.info(f"  - Job ID: {task_result.get('job_id')}")
            logger.info(f"  - Solution ID: {task_result.get('solution_id')}")
            logger.info(
                f"  - Completion: {task_result.get('completion_percentage', 'N/A'):.1f}%"
            )
            logger.info(
                f"  - Objective Value: {task_result.get('objective_value', 'N/A')}"
            )
            logger.info(
                f"  - Total Assignments: {task_result.get('total_assignments', 'N/A')}"
            )
        else:
            logger.error("❌ Status: FAILED")
            logger.error(f"Result or Error: {task_result}")
            if async_result.traceback:
                logger.error("--- Traceback from Celery Worker ---")
                logger.error(async_result.traceback)
            return 1

    except ImportError as e:
        logger.error(f"Failed to import backend components: {e}")
        logger.error(
            "Please ensure this script is run from a context where the 'backend' package is available."
        )
        return 1
    except Exception as e:
        logger.error(f"CLI execution failed: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
