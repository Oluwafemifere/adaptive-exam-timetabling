# backend/app/api/v1/routes/session_management.py
"""
API endpoints for direct, session-scoped data management.

This router provides a high-level interface that directly calls the
session-aware PL/pgSQL functions via the SessionManagementService. It's
intended for detailed, record-by-record management of session data
after the initial setup phase.
"""

from uuid import UUID
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.data_management.session_management_service import (
    SessionManagementService,
)
from ....schemas import session_management as sm_schemas
from ....schemas.system import GenericResponse

router = APIRouter()


async def _handle_service_response(
    result: dict, success_status: int = status.HTTP_200_OK
):
    """Helper to process the standardized response from the service layer."""
    if not result or not result.get("success"):
        error_detail = result.get("error", "An unknown error occurred.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error_detail),
        )
    # For create operations, return the ID in the data field
    if success_status == status.HTTP_201_CREATED:
        return GenericResponse(
            success=True,
            message=result.get("message", "Resource created successfully."),
            data={"id": result.get("id")},
        )
    return result


# =========================================================================
# Course Management Endpoints
# =========================================================================


@router.post(
    "/{session_id}/courses",
    response_model=GenericResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Course in a Session",
)
async def create_course_in_session(
    session_id: UUID,
    payload: sm_schemas.CoursePayload,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Adds a new course directly to the specified academic session."""
    service = SessionManagementService(db)
    result = await service.create_course(session_id, payload.model_dump())
    return await _handle_service_response(result, status.HTTP_201_CREATED)


@router.put(
    "/{session_id}/courses/{course_id}",
    response_model=GenericResponse,
    summary="Update a Course in a Session",
)
async def update_course_in_session(
    session_id: UUID,
    course_id: UUID,
    payload: sm_schemas.CoursePayload,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Updates an existing course within the specified academic session."""
    service = SessionManagementService(db)
    result = await service.update_course(session_id, course_id, payload.model_dump())
    return await _handle_service_response(result)


@router.delete(
    "/{session_id}/courses/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Course from a Session",
)
async def delete_course_from_session(
    session_id: UUID,
    course_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Removes a course from the specified academic session."""
    service = SessionManagementService(db)
    result = await service.delete_course(session_id, course_id)
    await _handle_service_response(result)
    return None


@router.get(
    "/{session_id}/courses",
    response_model=sm_schemas.PaginatedCoursesResponse,
    summary="Get Paginated Courses in a Session",
)
async def get_paginated_courses_in_session(
    session_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search_term: Optional[str] = Query(None),
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieves a paginated list of courses for a specific session."""
    service = SessionManagementService(db)
    result = await service.get_paginated_courses(
        session_id, page, page_size, search_term
    )
    if result is None:
        raise HTTPException(
            status_code=404, detail="No courses found for this session."
        )
    return result


# =========================================================================
# Building Management Endpoints
# =========================================================================


@router.post(
    "/{session_id}/buildings",
    response_model=GenericResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Building in a Session",
)
async def create_building_in_session(
    session_id: UUID,
    payload: sm_schemas.BuildingPayload,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Adds a new building directly to the specified academic session."""
    service = SessionManagementService(db)
    result = await service.create_building(session_id, payload.model_dump())
    return await _handle_service_response(result, status.HTTP_201_CREATED)


@router.put(
    "/{session_id}/buildings/{building_id}",
    response_model=GenericResponse,
    summary="Update a Building in a Session",
)
async def update_building_in_session(
    session_id: UUID,
    building_id: UUID,
    payload: sm_schemas.BuildingPayload,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Updates an existing building within the specified academic session."""
    service = SessionManagementService(db)
    result = await service.update_building(
        session_id, building_id, payload.model_dump()
    )
    return await _handle_service_response(result)


@router.delete(
    "/{session_id}/buildings/{building_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Building from a Session",
)
async def delete_building_from_session(
    session_id: UUID,
    building_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Removes a building from the specified academic session."""
    service = SessionManagementService(db)
    result = await service.delete_building(session_id, building_id)
    await _handle_service_response(result)
    return None


# =========================================================================
# Room Management Endpoints
# =========================================================================


@router.post(
    "/{session_id}/rooms",
    response_model=GenericResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Room in a Session",
)
async def create_room_in_session(
    session_id: UUID,
    payload: sm_schemas.RoomPayload,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Adds a new room directly to the specified academic session."""
    service = SessionManagementService(db)
    result = await service.create_room(session_id, payload.model_dump())
    return await _handle_service_response(result, status.HTTP_201_CREATED)


@router.put(
    "/{session_id}/rooms/{room_id}",
    response_model=GenericResponse,
    summary="Update a Room in a Session",
)
async def update_room_in_session(
    session_id: UUID,
    room_id: UUID,
    payload: sm_schemas.RoomPayload,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Updates an existing room within the specified academic session."""
    service = SessionManagementService(db)
    result = await service.update_room(session_id, room_id, payload.model_dump())
    return await _handle_service_response(result)


@router.delete(
    "/{session_id}/rooms/{room_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Room from a Session",
)
async def delete_room_from_session(
    session_id: UUID,
    room_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Removes a room from the specified academic session."""
    service = SessionManagementService(db)
    result = await service.delete_room(session_id, room_id)
    await _handle_service_response(result)
    return None


# =========================================================================
# Department Management Endpoints
# =========================================================================


@router.post(
    "/{session_id}/departments",
    response_model=GenericResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Department in a Session",
)
async def create_department_in_session(
    session_id: UUID,
    payload: sm_schemas.DepartmentPayload,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Adds a new department to the specified academic session."""
    service = SessionManagementService(db)
    result = await service.create_department(session_id, payload.model_dump())
    return await _handle_service_response(result, status.HTTP_201_CREATED)


@router.put(
    "/{session_id}/departments/{department_id}",
    response_model=GenericResponse,
    summary="Update a Department in a Session",
)
async def update_department_in_session(
    session_id: UUID,
    department_id: UUID,
    payload: sm_schemas.DepartmentPayload,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Updates an existing department within the specified academic session."""
    service = SessionManagementService(db)
    result = await service.update_department(
        session_id, department_id, payload.model_dump()
    )
    return await _handle_service_response(result)


@router.delete(
    "/{session_id}/departments/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Department from a Session",
)
async def delete_department_from_session(
    session_id: UUID,
    department_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Removes a department from the specified academic session."""
    service = SessionManagementService(db)
    result = await service.delete_department(session_id, department_id)
    await _handle_service_response(result)
    return None


@router.get(
    "/{session_id}/departments",
    response_model=sm_schemas.PaginatedDepartmentsResponse,
    summary="Get Paginated Departments in a Session",
)
async def get_paginated_departments_in_session(
    session_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search_term: Optional[str] = Query(None),
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieves a paginated list of departments for a specific session."""
    service = SessionManagementService(db)
    result = await service.get_paginated_departments(
        session_id, page, page_size, search_term
    )
    if result is None:
        raise HTTPException(
            status_code=404, detail="No departments found for this session."
        )
    return result


# =========================================================================
# Staff Management Endpoints
# =========================================================================


@router.post(
    "/{session_id}/staff",
    response_model=GenericResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Staff Member in a Session",
)
async def create_staff_in_session(
    session_id: UUID,
    payload: sm_schemas.StaffPayload,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Adds a new staff member to the specified academic session."""
    service = SessionManagementService(db)
    result = await service.create_staff(session_id, payload.model_dump())
    return await _handle_service_response(result, status.HTTP_201_CREATED)


@router.put(
    "/{session_id}/staff/{staff_id}",
    response_model=GenericResponse,
    summary="Update a Staff Member in a Session",
)
async def update_staff_in_session(
    session_id: UUID,
    staff_id: UUID,
    payload: sm_schemas.StaffPayload,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Updates an existing staff member within the specified academic session."""
    service = SessionManagementService(db)
    result = await service.update_staff(session_id, staff_id, payload.model_dump())
    return await _handle_service_response(result)


@router.delete(
    "/{session_id}/staff/{staff_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Staff Member from a Session",
)
async def delete_staff_from_session(
    session_id: UUID,
    staff_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Removes a staff member from the specified academic session."""
    service = SessionManagementService(db)
    result = await service.delete_staff(session_id, staff_id)
    await _handle_service_response(result)
    return None


@router.get(
    "/{session_id}/staff",
    response_model=sm_schemas.PaginatedStaffResponse,
    summary="Get Paginated Staff in a Session",
)
async def get_paginated_staff_in_session(
    session_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search_term: Optional[str] = Query(None),
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieves a paginated list of staff for a specific session."""
    service = SessionManagementService(db)
    result = await service.get_paginated_staff(session_id, page, page_size, search_term)
    if result is None:
        raise HTTPException(status_code=404, detail="No staff found for this session.")
    return result


# =========================================================================
# Exam Management Endpoints
# =========================================================================


@router.post(
    "/{session_id}/exams",
    response_model=GenericResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an Exam in a Session",
)
async def create_exam_in_session(
    session_id: UUID,
    payload: sm_schemas.ExamPayload,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Adds a new exam to the specified academic session."""
    service = SessionManagementService(db)
    result = await service.create_exam(session_id, payload.model_dump())
    return await _handle_service_response(result, status.HTTP_201_CREATED)


@router.put(
    "/{session_id}/exams/{exam_id}",
    response_model=GenericResponse,
    summary="Update an Exam in a Session",
)
async def update_exam_in_session(
    session_id: UUID,
    exam_id: UUID,
    payload: sm_schemas.ExamPayload,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Updates an existing exam within the specified academic session."""
    service = SessionManagementService(db)
    result = await service.update_exam(session_id, exam_id, payload.model_dump())
    return await _handle_service_response(result)


@router.delete(
    "/{session_id}/exams/{exam_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an Exam from a Session",
)
async def delete_exam_from_session(
    session_id: UUID,
    exam_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Removes an exam from the specified academic session."""
    service = SessionManagementService(db)
    result = await service.delete_exam(session_id, exam_id)
    await _handle_service_response(result)
    return None


@router.get(
    "/{session_id}/exams",
    response_model=sm_schemas.PaginatedExamsResponse,
    summary="Get Paginated Exams in a Session",
)
async def get_paginated_exams_in_session(
    session_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search_term: Optional[str] = Query(None),
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieves a paginated list of exams for a specific session."""
    service = SessionManagementService(db)
    result = await service.get_paginated_exams(session_id, page, page_size, search_term)
    if result is None:
        raise HTTPException(status_code=404, detail="No exams found for this session.")
    return result


# =========================================================================
# Staff Unavailability Endpoints
# =========================================================================


@router.post(
    "/{session_id}/staff-unavailability",
    response_model=GenericResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Staff Unavailability",
)
async def add_staff_unavailability(
    session_id: UUID,
    payload: sm_schemas.StaffUnavailabilityPayload,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Records a period when a staff member is unavailable."""
    service = SessionManagementService(db)
    result = await service.create_staff_unavailability(session_id, payload.model_dump())
    return await _handle_service_response(result, status.HTTP_201_CREATED)


@router.get(
    "/{session_id}/staff/{staff_id}/unavailability",
    response_model=Dict,
    summary="Get Staff Unavailability",
)
async def get_staff_unavailability_records(
    session_id: UUID,
    staff_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieves all unavailability records for a specific staff member."""
    service = SessionManagementService(db)
    result = await service.get_staff_unavailability(session_id, staff_id)
    return await _handle_service_response(result)


@router.delete(
    "/{session_id}/staff-unavailability/{unavailability_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Staff Unavailability",
)
async def delete_staff_unavailability_record(
    session_id: UUID,
    unavailability_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Deletes a specific staff unavailability record."""
    service = SessionManagementService(db)
    result = await service.delete_staff_unavailability(session_id, unavailability_id)
    await _handle_service_response(result)
    return None


# =========================================================================
# Other Data Retrieval Endpoints
# =========================================================================


@router.get(
    "/{session_id}/students",
    response_model=sm_schemas.PaginatedStudentsResponse,
    summary="Get Paginated Students in a Session",
)
async def get_paginated_students_in_session(
    session_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search_term: Optional[str] = Query(None),
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Retrieves a paginated list of students enrolled in a specific session."""
    service = SessionManagementService(db)
    result = await service.get_paginated_students(
        session_id, page, page_size, search_term
    )
    if result is None:
        raise HTTPException(
            status_code=404, detail="No students found for this session."
        )
    return result


@router.get(
    "/{session_id}/data-graph",
    response_model=sm_schemas.SessionDataGraphResponse,
    summary="Get Full Data Graph for a Session",
)
async def get_full_session_data_graph(
    session_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Retrieves a comprehensive, nested JSON object of all core data
    for a given session.
    """
    service = SessionManagementService(db)
    raw_result = await service.get_session_data_graph(session_id)
    if not raw_result:
        raise HTTPException(
            status_code=404,
            detail="Data graph could not be generated for this session. It may be empty.",
        )

    # The SQL function now returns a well-structured object.
    # We can pass it directly to the Pydantic model for validation and response.
    return raw_result
