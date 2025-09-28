# backend/app/api/v1/routes/exams.py
"""API endpoints for managing exams."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.data_management.core_data_service import CoreDataService
from ....services.data_retrieval.unified_data_retrieval import UnifiedDataService
from ....schemas.scheduling import ExamCreate, ExamRead, ExamUpdate
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/", response_model=ExamRead, status_code=status.HTTP_201_CREATED)
async def create_exam(
    exam_in: ExamCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Create a new exam."""
    service = CoreDataService(db)
    result = await service.create_exam(exam_in.model_dump(), user.id)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to create exam."),
        )
    data_service = UnifiedDataService(db)
    created_exam = await data_service.get_entity_by_id("exam", result["id"])
    return created_exam


@router.get("/", response_model=List[ExamRead])
async def list_exams(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve a paginated list of exams."""
    service = UnifiedDataService(db)
    result = await service.get_paginated_entities(
        "exams", page=page, page_size=page_size
    )
    assert result
    return result.get("data", [])


@router.get("/{exam_id}", response_model=ExamRead)
async def get_exam(
    exam_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve a single exam by its ID."""
    service = UnifiedDataService(db)
    exam = await service.get_entity_by_id("exam", exam_id)
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found"
        )
    return exam


@router.put("/{exam_id}", response_model=ExamRead)
async def update_exam(
    exam_id: UUID,
    exam_in: ExamUpdate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Update an existing exam."""
    service = CoreDataService(db)
    result = await service.update_exam(
        exam_id, exam_in.model_dump(exclude_unset=True), user.id
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to update exam."),
        )
    data_service = UnifiedDataService(db)
    updated_exam = await data_service.get_entity_by_id("exam", exam_id)
    return updated_exam


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exam(
    exam_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Delete an exam."""
    service = CoreDataService(db)
    result = await service.delete_exam(exam_id, user.id)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to delete exam."),
        )
    return None
