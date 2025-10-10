# backend/app/utils/celery_task_utils.py

import asyncio
from functools import wraps
import logging

logger = logging.getLogger(__name__)


def task_progress_tracker(
    start_progress: int, end_progress: int, phase: str, message: str
):
    """
    A decorator to track the progress of a method within a Celery task.

    It updates the task's progress before and after execution.
    The decorated class instance is expected to have a 'task_context'
    attribute holding the Celery task instance.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            task = getattr(self, "task_context", None)

            if task and hasattr(task, "update_progress"):
                try:
                    await task.update_progress(start_progress, phase, message)
                except Exception as e:
                    logger.warning(
                        f"Failed to update task progress (pre-execution): {e}"
                    )

            result = await func(self, *args, **kwargs)

            if task and hasattr(task, "update_progress"):
                try:
                    await task.update_progress(
                        end_progress, f"{phase}_complete", f"{message} complete."
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to update task progress (post-execution): {e}"
                    )

            return result

        return wrapper

    return decorator
