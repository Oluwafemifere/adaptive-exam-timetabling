# backend/app/api/v1/routes/uploads.py
import os
import uuid
import logging
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
from ....services.seeding.data_seeding_service import DataSeedingService
from ....services.uploads.file_upload_service import (
    FileUploadService,
)  # MODIFIED: Renamed service
from ....tasks import process_csv_upload_task
from ....schemas.system import GenericResponse
from ....services.data_validation.validation_schemas import ENTITY_SCHEMAS

router = APIRouter()
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post(
    "/{academic_session_id}/{entity_type}", status_code=status.HTTP_202_ACCEPTED
)
async def upload_data_file(
    academic_session_id: uuid.UUID,
    entity_type: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Uploads a CSV file for a specific entity within an academic session.
    This creates a file_uploads record linked to the session's data_seeding_session.
    """
    if entity_type not in ENTITY_SCHEMAS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entity_type. Must be one of: {list(ENTITY_SCHEMAS.keys())}",
        )
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")

    # Step 1: Find the parent data_seeding_session
    seeding_service = DataSeedingService(db)
    seeding_session = await seeding_service.get_seeding_session_by_academic_session(
        academic_session_id
    )
    if not seeding_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data seeding has not been initiated for this academic session.",
        )
    seeding_session_id = seeding_session["id"]

    # Step 2: Save the file locally
    unique_filename = f"{uuid.uuid4()}.csv"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    try:
        contents = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
        record_count = max(0, contents.decode("utf-8", errors="ignore").count("\n"))
    except IOError as e:
        logger.error(
            f"Failed to save uploaded file '{unique_filename}': {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Could not save file.")

    # Step 3: Create the file_uploads record in the database
    upload_service = FileUploadService(db)
    upload_response = await upload_service.create_file_upload(
        seeding_session_id=seeding_session_id,
        upload_type=entity_type,
        file_name=file.filename,
        file_path=file_path,
        total_records=record_count,
    )

    if not upload_response or not upload_response.get("success"):
        error_detail = f"Failed to create file upload record: {upload_response.get('error', 'Unknown error')}"
        raise HTTPException(status_code=500, detail=error_detail)

    file_upload_id = upload_response["file_upload_id"]
    logger.info(f"File upload {file_upload_id} created. Dispatching Celery task.")

    # Step 4: Dispatch background task with the new file_upload_id
    process_csv_upload_task.delay(
        file_upload_id=str(file_upload_id),
        file_path=file_path,
        entity_type=entity_type,
        user_id=str(current_user.id),
        academic_session_id=str(academic_session_id),
    )

    return {
        "message": "File upload accepted and is being processed.",
        "file_upload_id": str(file_upload_id),
        "data_seeding_session_id": str(seeding_session_id),
    }


@router.get("/file/{file_upload_id}/status", response_model=GenericResponse)
async def get_upload_status(
    file_upload_id: uuid.UUID,
    db: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves the current status of a single file upload.
    """
    service = FileUploadService(db)
    status_data = await service.get_file_upload_status(file_upload_id)

    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File upload with ID {file_upload_id} not found.",
        )

    return GenericResponse(success=True, data=status_data)
