# backend/app/api/v1/routes/uploads.py
import logging
import os
import shutil
import uuid  # IMPORT THE UUID MODULE
from uuid import UUID
from typing import List
from pathlib import Path
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.seeding.file_upload_service import FileUploadService
from ....services.seeding.data_seeding_service import DataSeedingService
from ....schemas.system import GenericResponse

# Define a temporary directory for uploads
TEMP_UPLOAD_DIR = Path("/tmp/exam_uploads")
TEMP_UPLOAD_DIR.mkdir(exist_ok=True)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/upload/{academic_session_id}",
    response_model=GenericResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Step 2: Upload Data Files",
)
async def upload_data_files(
    academic_session_id: UUID,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Handles the upload of multiple CSV files for a given academic session.

    This endpoint saves the files, validates their structure, detects their entity type,
    and dispatches background tasks to process them.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No files were uploaded."
        )

    # First, get the corresponding data_seeding_session_id
    seeding_service = DataSeedingService(db)
    seeding_session = await seeding_service.get_seeding_session_by_academic_session(
        academic_session_id
    )
    if not seeding_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data seeding session found for the given academic session. Please complete Step 1 first.",
        )
    data_seeding_session_id = seeding_session["id"]

    # Save uploaded files to a temporary location
    temp_file_paths = []
    try:
        for file in files:
            # --- FIX: Use uuid.uuid4() to generate a proper random UUID ---
            temp_path = TEMP_UPLOAD_DIR / f"{uuid.uuid4()}_{file.filename}"
            with temp_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            temp_file_paths.append(temp_path)
            logger.info(f"Temporarily saved file to {temp_path}")
    finally:
        for file in files:
            file.file.close()

    # Dispatch tasks using the refactored service
    upload_service = FileUploadService(db)
    dispatch_results = await upload_service.handle_file_uploads_and_dispatch(
        academic_session_id=academic_session_id,
        data_seeding_session_id=data_seeding_session_id,
        user_id=user.id,
        file_paths=temp_file_paths,
    )

    return GenericResponse(
        success=True,
        message=f"{len(dispatch_results['dispatched_tasks'])} files accepted for processing. Check status endpoint for progress.",
        data=dispatch_results,
    )
