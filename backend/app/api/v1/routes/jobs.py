#C:\Users\fresh\OneDrive\Dokumen\thesis\proj\CODE\adaptive-exam-timetabling\backend\app\api\v1\routes\jobs.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import db_session
from app.services.job import JobService

router = APIRouter()

@router.get("/")
async def list_jobs(db: AsyncSession = Depends(db_session)):
    return await JobService(db).list_jobs()

@router.get("/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(db_session)):
    return await JobService(db).get_job_status(job_id)
