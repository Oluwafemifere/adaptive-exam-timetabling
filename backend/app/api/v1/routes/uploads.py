#C:\Users\fresh\OneDrive\Dokumen\thesis\proj\CODE\adaptive-exam-timetabling\backend\app\api\v1\routes\uploads.py
from fastapi import APIRouter, File, UploadFile, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import db_session
from app.services.data_validation.csv_processor import CSVProcessor

router = APIRouter()

@router.post("/")
async def upload_csv(
    entity_type: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(db_session)
):
    contents = await file.read()
    path = f"/tmp/{file.filename}"
    with open(path, "wb") as f:
        f.write(contents)
    processor = CSVProcessor()
    result = processor.process_csv_file(path, entity_type)
    return result
