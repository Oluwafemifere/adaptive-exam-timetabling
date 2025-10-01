"""API endpoints for managing academic courses."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.data_management.core_data_service import CoreDataService
from ....services.data_retrieval import DataRetrievalService  # Corrected import
from ....schemas.academic import CourseCreate, CourseRead, CourseUpdate

router = APIRouter()


@router.post("/", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def create_course(
    course_in: CourseCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Create a new academic course."""
    service = CoreDataService(db)
    result = await service.create_course(course_in.model_dump(), user.id)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to create course."),
        )
    # Fetch the created course to return it with all fields
    data_service = DataRetrievalService(db)  # Corrected service class
    created_course = await data_service.get_entity_by_id("course", result["id"])
    return created_course


@router.get("/", response_model=List[CourseRead])
async def list_courses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve a paginated list of courses."""
    service = DataRetrievalService(db)  # Corrected service class
    result = await service.get_paginated_entities(
        "courses", page=page, page_size=page_size
    )
    return result.get("data", []) if result else []


@router.get("/{course_id}", response_model=CourseRead)
async def get_course(
    course_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieve a single course by its ID."""
    service = DataRetrievalService(db)  # Corrected service class
    course = await service.get_entity_by_id("course", course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )
    return course


@router.put("/{course_id}", response_model=CourseRead)
async def update_course(
    course_id: UUID,
    course_in: CourseUpdate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Update an existing course."""
    service = CoreDataService(db)
    result = await service.update_course(
        course_id, course_in.model_dump(exclude_unset=True), user.id
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to update course."),
        )
    data_service = DataRetrievalService(db)  # Corrected service class
    updated_course = await data_service.get_entity_by_id("course", course_id)
    if not updated_course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found after update.",
        )
    return updated_course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Delete a course."""
    service = CoreDataService(db)
    result = await service.delete_course(course_id, user.id)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to delete course."),
        )
    return None
