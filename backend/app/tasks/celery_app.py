# backend/app/tasks/celery_app.py
import asyncio
import logging
from celery import Celery
from celery.signals import setup_logging
from kombu import Queue
from sqlalchemy import NullPool, text
from ..core.config import settings
from ..main import health_check as fastapi_health_check
from typing import Any, Optional, Dict
from ..database import db_manager, DatabaseManager
import re
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)


def make_celery() -> Celery:
    broker = getattr(
        settings, "CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//"
    )
    backend = getattr(settings, "CELERY_RESULT_BACKEND", "rpc://")
    app = Celery("timetabling_tasks", broker=broker, backend=backend)

    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_routes={
            "backend.app.tasks.scheduling_tasks.*": {"queue": "scheduling"},
            "backend.app.tasks.data_processing_tasks.*": {"queue": "data_processing"},
            "backend.app.tasks.notification_tasks.*": {"queue": "notifications"},
        },
        task_default_queue="default",
        task_queues=(
            Queue("default", routing_key="default"),
            Queue("scheduling", routing_key="scheduling"),
            Queue("data_processing", routing_key="data_processing"),
            Queue("notifications", routing_key="notifications"),
        ),
        task_soft_time_limit=300,
        task_time_limit=600,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        result_expires=3600,
        worker_send_task_events=True,
        task_send_sent_event=True,
        task_reject_on_worker_lost=True,
        task_ignore_result=False,
    )

    @setup_logging.connect
    def config_loggers(*args, **kwargs):
        from logging.config import dictConfig

        dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "default": {
                        "format": "[%(asctime)s: %(levelname)s/%(name)s] %(message)s"
                    }
                },
                "handlers": {
                    "console": {
                        "level": "INFO",
                        "class": "logging.StreamHandler",
                        "formatter": "default",
                    }
                },
                "root": {"level": "INFO", "handlers": ["console"]},
                "loggers": {
                    "celery": {
                        "level": "INFO",
                        "handlers": ["console"],
                        "propagate": False,
                    },
                    "backend.app.tasks": {
                        "level": "INFO",
                        "handlers": ["console"],
                        "propagate": False,
                    },
                },
            }
        )

    return app


# single canonical instance
celery_app = make_celery()

# autodiscover tasks under package namespace
# this will import modules matching backend.app.tasks.* to register tasks
celery_app.autodiscover_tasks(["backend.app.tasks"])


def _run_coro_in_new_loop(coro):
    """Run an async coroutine on a fresh event loop in this thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
        loop.close()


@celery_app.task(name="health_check")
def health_check():
    async def _check():
        engine = None
        try:
            engine = create_async_engine(
                settings.DATABASE_URL, poolclass=NullPool, echo=False
            )
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                return {
                    "status": "healthy",
                    "service": "backend",
                    "database": {
                        "status": "healthy",
                        "message": "Database connection successful",
                    },
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "service": "backend",
                "database": {
                    "status": "unhealthy",
                    "error": str(e),
                    "message": "Database connection failed",
                },
            }
        finally:
            if engine is not None:
                await engine.dispose()

    return _run_coro_in_new_loop(_check())


# --- minimal DB-session decorator used by tests ---
def task_with_db_session(func):
    """Decorator to provide an async DB session to a coroutine task function."""
    from functools import wraps
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    @wraps(func)
    async def wrapper(*args, **kwargs):
        engine = create_async_engine(
            settings.DATABASE_URL, poolclass=NullPool, echo=False
        )
        async_session = async_sessionmaker(engine, expire_on_commit=False)

        async with async_session() as session:
            try:
                result = await func(session, *args, **kwargs)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    return wrapper


# --- lightweight TaskMonitor used by tests ---
class TaskMonitor:
    """Basic helpers for inspecting and controlling Celery tasks."""

    @staticmethod
    def get_task_info(task_id: str) -> Optional[Dict[str, Any]]:
        try:
            res = celery_app.AsyncResult(task_id)
            return {
                "task_id": task_id,
                "status": getattr(res, "status", None),
                "result": getattr(res, "result", None),
                "traceback": getattr(res, "traceback", None),
                "info": getattr(res, "info", None),
            }
        except Exception as exc:
            logger.error("TaskMonitor.get_task_info failed: %s", exc)
            return None

    @staticmethod
    def get_active_tasks() -> Dict[str, Any]:
        try:
            inspect = celery_app.control.inspect()
            return {
                "active": inspect.active() if inspect else {},
                "scheduled": inspect.scheduled() if inspect else {},
                "reserved": inspect.reserved() if inspect else {},
            }
        except Exception as exc:
            logger.error("TaskMonitor.get_active_tasks failed: %s", exc)
            return {}

    @staticmethod
    def cancel_task(task_id: str) -> bool:
        try:
            celery_app.control.revoke(task_id, terminate=True)
            return True
        except Exception as exc:
            logger.error("TaskMonitor.cancel_task failed: %s", exc)
            return False


# export
__all__ = ["celery_app", "task_with_db_session", "TaskMonitor"]
