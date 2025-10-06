# backend/app/api/v1/routes/versions.py
import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_active_superuser, get_db
from backend.app.services.data_retrieval import DataRetrievalService
from backend.app.models import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/publish/{job_id}", status_code=status.HTTP_200_OK)
async def publish_version_from_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
):
    """
    Publishes the timetable version associated with a specific completed job.

    This action makes the timetable the official, visible version for the
    academic session. It will automatically un-publish any previously
    published timetable for the same session.

    - **job_id**: The UUID of the completed timetable job to publish.
    - **Requires**: Superuser authentication.
    """
    logger.info(f"User '{current_user.email}' attempting to publish job '{job_id}'.")
    service = DataRetrievalService(db)
    try:
        result = await service.publish_timetable_version(
            job_id=job_id, user_id=current_user.id
        )

        # FIX: Handle the case where result might be None before calling .get()
        if result is None or result.get("success") is False:
            error_message = (
                result.get("error", "Failed to publish timetable version.")
                if result
                else "An unknown error occurred during publishing."
            )
            logger.error(f"Publishing failed for job '{job_id}': {error_message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message,
            )

        logger.info(f"Successfully published timetable version for job '{job_id}'.")
        return {
            "success": True,
            "message": result.get("message"),
            "data": {
                "published_version_id": result.get("published_version_id"),
                "job_id": result.get("job_id"),
            },
        }
    except Exception as e:
        logger.exception(
            f"An unexpected error occurred while publishing job {job_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
