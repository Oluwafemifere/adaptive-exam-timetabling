# backend/app/api/v1/routes/uploads.py
import os
import uuid
import logging
from typing import Optional
from fastapi import (
    APIRouter,
    File,
    UploadFile,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession
from ....api.deps import db_session, get_current_user
from ....models import User
from ....services.uploads.data_upload_service import DataUploadService
from ....tasks import process_csv_upload_task
from ....schemas.system import GenericResponse

# Import centralized schemas to validate entity_type
from ....services.data_validation.validation_schemas import ENTITY_SCHEMAS

router = APIRouter()
logger = logging.getLogger(__name__)

# Use project-relative uploads directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# --- MODIFICATION: Endpoint now requires academic_session_id and entity_type in the path ---
@router.post(
    "/{academic_session_id}/{entity_type}", status_code=status.HTTP_202_ACCEPTED
)
async def upload_data_file(
    academic_session_id: uuid.UUID,  # Now a required path parameter
    entity_type: str,  # Now a required path parameter
    file: UploadFile = File(...),
    db: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Uploads a CSV file for bulk data ingestion via a background task.
    The data is loaded into a staging table before being processed by a DB function.
    """
    logger.info(
        f"Upload request for session '{academic_session_id}', entity '{entity_type}' from user '{current_user.email}'."
    )

    # Staging tables are named based on the entity_type, so we validate against the same keys
    if entity_type not in ENTITY_SCHEMAS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entity_type '{entity_type}'. Must be one of: {list(ENTITY_SCHEMAS.keys())}",
        )

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400, detail="Invalid file type. Only .csv files are accepted."
        )

    unique_filename = f"{uuid.uuid4()}.csv"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        contents = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
        file_size = len(contents)
        # Estimate record count based on newlines
        record_count = max(0, contents.decode("utf-8", errors="ignore").count("\n"))
    except IOError as e:
        logger.error(
            f"Failed to save uploaded file '{unique_filename}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail="Could not save file for processing."
        )

    # Metadata for the upload session record
    file_metadata = [
        {
            "file_name": file.filename,
            "file_size": file_size,
            "file_type": file.content_type,  # type: ignore
            "record_count": record_count,
            "file_path": file_path,
        }
    ]

    upload_service = DataUploadService(db)
    # The call to create_upload_session now passes the required session_id
    session_response = await upload_service.create_upload_session(
        user_id=current_user.id,
        session_id=academic_session_id,  # Pass the ID from the path
        upload_type=entity_type,
        file_metadata=file_metadata,
    )

    if not session_response or not session_response.get("success"):
        error_detail = f"Failed to create upload session: {session_response.get('error') if session_response else 'No response from service'}"
        raise HTTPException(status_code=500, detail=error_detail)

    upload_session_id = session_response["upload_session_id"]
    logger.info(f"Upload session {upload_session_id} created. Dispatching Celery task.")

    # --- MODIFICATION: Dispatch the Celery task with the academic_session_id ---
    process_csv_upload_task.delay(
        upload_session_id=str(upload_session_id),
        file_path=file_path,
        entity_type=entity_type,
        user_id=str(current_user.id),
        academic_session_id=str(academic_session_id),  # Add session ID to the task
    )

    return {
        "message": "File upload accepted and is being processed.",
        "upload_session_id": str(upload_session_id),
        "entity_type": entity_type,
        "academic_session_id": str(academic_session_id),
    }


@router.get("/{upload_session_id}/status", response_model=GenericResponse)
async def get_upload_status(
    upload_session_id: uuid.UUID,
    db: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves the current status of a file upload session.
    """
    service = DataUploadService(db)
    status_data = await service.get_upload_session_status(upload_session_id)

    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload session with ID {upload_session_id} not found.",
        )

    return GenericResponse(success=True, data=status_data)
