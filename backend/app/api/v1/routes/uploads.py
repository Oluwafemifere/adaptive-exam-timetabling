# backend/app/api/v1/routes/uploads.py
import os
from fastapi import APIRouter, File, UploadFile, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ....api.deps import db_session
from ....services.data_validation.csv_processor import CSVProcessor

router = APIRouter()


@router.post("/")
async def upload_csv(
    entity_type: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(db_session),
):
    # Ensure the tmp directory exists
    tmp_dir = "/tmp"
    os.makedirs(tmp_dir, exist_ok=True)

    # Save uploaded file
    contents = await file.read()
    filename = file.filename or "uploaded.csv"
    path = os.path.join(tmp_dir, filename)
    with open(path, "wb") as f:
        f.write(contents)

    # Process CSV
    processor = CSVProcessor()
    result = processor.process_csv_file(path, entity_type)
    return result
