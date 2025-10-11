# backend/app/api/v1/routes/staging.py
"""API endpoints for managing individual records in staging tables."""

from uuid import UUID
from datetime import date
from typing import Callable, Coroutine, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session, current_user
from ....models.users import User
from ....services.seeding.staging_service import StagingService
from ....schemas.system import GenericResponse
from ....schemas import staging as staging_schemas

router = APIRouter()


# Helper function to handle exceptions and commit transaction
async def _execute_and_respond(
    db: AsyncSession,
    service_action: Callable[[], Coroutine[Any, Any, None]],
    success_message: str,
):
    """
    Executes a given service action, commits the transaction, and returns a
    standardized response. Rolls back on failure.
    """
    try:
        await service_action()
        await db.commit()
        return GenericResponse(success=True, message=success_message)
    except Exception as e:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Operation failed: {e}",
        )


# =================================================================
# Get All Staged Data for a Session
# =================================================================


@router.get("/{session_id}", response_model=staging_schemas.StagedSessionData)
async def get_staged_session_data(
    session_id: UUID,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """
    Retrieve all staged data for a given session ID.

    This endpoint provides a complete snapshot of the data that has been uploaded
    and is ready for review and editing before being finalized.
    """
    service = StagingService(db)
    try:
        data = await service.get_session_data(session_id)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching session data: {e}",
        )


# =================================================================
# Buildings Endpoints
# =================================================================


@router.post("/{session_id}/buildings", response_model=GenericResponse)
async def add_staged_building(
    session_id: UUID,
    building_in: staging_schemas.BuildingCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Add a new building to the staging table for a session."""
    service = StagingService(db)

    async def action():
        await service.add_building(session_id, **building_in.model_dump())

    return await _execute_and_respond(db, action, "Building added successfully.")


@router.put("/{session_id}/buildings/{code}", response_model=GenericResponse)
async def update_staged_building(
    session_id: UUID,
    code: str,
    building_in: staging_schemas.BuildingUpdate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Update an existing building in the staging table."""
    service = StagingService(db)
    update_data = building_in.model_dump(exclude_unset=True)

    async def action():
        await service.update_building(session_id, code, **update_data)

    return await _execute_and_respond(db, action, "Building updated successfully.")


@router.delete("/{session_id}/buildings/{code}", response_model=GenericResponse)
async def delete_staged_building(
    session_id: UUID,
    code: str,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Delete a building from the staging table."""
    service = StagingService(db)

    async def action():
        await service.delete_building(session_id, code)

    return await _execute_and_respond(db, action, "Building deleted successfully.")


# =================================================================
# Course Departments Endpoints
# =================================================================


@router.post("/{session_id}/course-departments", response_model=GenericResponse)
async def add_staged_course_department(
    session_id: UUID,
    data_in: staging_schemas.CourseDepartmentCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Link a course to a department in the staging table."""
    service = StagingService(db)

    async def action():
        await service.add_course_department(session_id, **data_in.model_dump())

    return await _execute_and_respond(
        db, action, "Course department link added successfully."
    )


@router.delete(
    "/{session_id}/course-departments/{course_code}/{department_code}",
    response_model=GenericResponse,
)
async def delete_staged_course_department(
    session_id: UUID,
    course_code: str,
    department_code: str,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Delete a course-department link from the staging table."""
    service = StagingService(db)

    async def action():
        await service.delete_course_department(session_id, course_code, department_code)

    return await _execute_and_respond(
        db, action, "Course department link deleted successfully."
    )


# =================================================================
# Course Faculties Endpoints
# =================================================================


@router.post("/{session_id}/course-faculties", response_model=GenericResponse)
async def add_staged_course_faculty(
    session_id: UUID,
    data_in: staging_schemas.CourseFacultyCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Link a course to a faculty in the staging table."""
    service = StagingService(db)

    async def action():
        await service.add_course_faculty(session_id, **data_in.model_dump())

    return await _execute_and_respond(
        db, action, "Course faculty link added successfully."
    )


@router.delete(
    "/{session_id}/course-faculties/{course_code}/{faculty_code}",
    response_model=GenericResponse,
)
async def delete_staged_course_faculty(
    session_id: UUID,
    course_code: str,
    faculty_code: str,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Delete a course-faculty link from the staging table."""
    service = StagingService(db)

    async def action():
        await service.delete_course_faculty(session_id, course_code, faculty_code)

    return await _execute_and_respond(
        db, action, "Course faculty link deleted successfully."
    )


# =================================================================
# Course Instructors Endpoints
# =================================================================


@router.post("/{session_id}/course-instructors", response_model=GenericResponse)
async def add_staged_course_instructor(
    session_id: UUID,
    data_in: staging_schemas.CourseInstructorCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Assign an instructor to a course in the staging table."""
    service = StagingService(db)

    async def action():
        await service.add_course_instructor(session_id, **data_in.model_dump())

    return await _execute_and_respond(
        db, action, "Course instructor added successfully."
    )


@router.delete(
    "/{session_id}/course-instructors/{staff_number}/{course_code}",
    response_model=GenericResponse,
)
async def delete_staged_course_instructor(
    session_id: UUID,
    staff_number: str,
    course_code: str,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Delete a course-instructor assignment from the staging table."""
    service = StagingService(db)

    async def action():
        await service.delete_course_instructor(session_id, staff_number, course_code)

    return await _execute_and_respond(
        db, action, "Course instructor deleted successfully."
    )


# =================================================================
# Course Registrations Endpoints
# =================================================================


@router.post("/{session_id}/course-registrations", response_model=GenericResponse)
async def add_staged_course_registration(
    session_id: UUID,
    data_in: staging_schemas.CourseRegistrationCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Add a student course registration to the staging table."""
    service = StagingService(db)

    async def action():
        await service.add_course_registration(session_id, **data_in.model_dump())

    return await _execute_and_respond(
        db, action, "Course registration added successfully."
    )


@router.put(
    "/{session_id}/course-registrations/{student_matric_number}/{course_code}",
    response_model=GenericResponse,
)
async def update_staged_course_registration(
    session_id: UUID,
    student_matric_number: str,
    course_code: str,
    data_in: staging_schemas.CourseRegistrationUpdate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Update a course registration in the staging table."""
    service = StagingService(db)

    async def action():
        await service.update_course_registration(
            session_id,
            student_matric_number,
            course_code,
            data_in.registration_type,
        )

    return await _execute_and_respond(
        db, action, "Course registration updated successfully."
    )


@router.delete(
    "/{session_id}/course-registrations/{student_matric_number}/{course_code}",
    response_model=GenericResponse,
)
async def delete_staged_course_registration(
    session_id: UUID,
    student_matric_number: str,
    course_code: str,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Delete a course registration from the staging table."""
    service = StagingService(db)

    async def action():
        await service.delete_course_registration(
            session_id, student_matric_number, course_code
        )

    return await _execute_and_respond(
        db, action, "Course registration deleted successfully."
    )


# =================================================================
# Courses Endpoints
# =================================================================


@router.post("/{session_id}/courses", response_model=GenericResponse)
async def add_staged_course(
    session_id: UUID,
    course_in: staging_schemas.CourseCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Add a new course to the staging table."""
    service = StagingService(db)

    async def action():
        await service.add_course(session_id, **course_in.model_dump())

    return await _execute_and_respond(db, action, "Course added successfully.")


@router.put("/{session_id}/courses/{code}", response_model=GenericResponse)
async def update_staged_course(
    session_id: UUID,
    code: str,
    course_in: staging_schemas.CourseUpdate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Update a course in the staging table."""
    service = StagingService(db)
    update_data = course_in.model_dump(exclude_unset=True)

    async def action():
        await service.update_course(session_id, code, **update_data)

    return await _execute_and_respond(db, action, "Course updated successfully.")


@router.delete("/{session_id}/courses/{code}", response_model=GenericResponse)
async def delete_staged_course(
    session_id: UUID,
    code: str,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Delete a course from the staging table."""
    service = StagingService(db)

    async def action():
        await service.delete_course(session_id, code)

    return await _execute_and_respond(db, action, "Course deleted successfully.")


# =================================================================
# Departments Endpoints
# =================================================================


@router.post("/{session_id}/departments", response_model=GenericResponse)
async def add_staged_department(
    session_id: UUID,
    department_in: staging_schemas.DepartmentCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Add a new department to the staging table."""
    service = StagingService(db)

    async def action():
        await service.add_department(session_id, **department_in.model_dump())

    return await _execute_and_respond(db, action, "Department added successfully.")


@router.put("/{session_id}/departments/{code}", response_model=GenericResponse)
async def update_staged_department(
    session_id: UUID,
    code: str,
    department_in: staging_schemas.DepartmentUpdate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Update a department in the staging table."""
    service = StagingService(db)
    update_data = department_in.model_dump(exclude_unset=True)

    async def action():
        await service.update_department(session_id, code, **update_data)

    return await _execute_and_respond(db, action, "Department updated successfully.")


@router.delete("/{session_id}/departments/{code}", response_model=GenericResponse)
async def delete_staged_department(
    session_id: UUID,
    code: str,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Delete a department from the staging table."""
    service = StagingService(db)

    async def action():
        await service.delete_department(session_id, code)

    return await _execute_and_respond(db, action, "Department deleted successfully.")


# =================================================================
# Faculties Endpoints
# =================================================================


@router.post("/{session_id}/faculties", response_model=GenericResponse)
async def add_staged_faculty(
    session_id: UUID,
    faculty_in: staging_schemas.FacultyCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Add a new faculty to the staging table."""
    service = StagingService(db)

    async def action():
        await service.add_faculty(session_id, **faculty_in.model_dump())

    return await _execute_and_respond(db, action, "Faculty added successfully.")


@router.put("/{session_id}/faculties/{code}", response_model=GenericResponse)
async def update_staged_faculty(
    session_id: UUID,
    code: str,
    faculty_in: staging_schemas.FacultyUpdate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Update a faculty in the staging table."""
    service = StagingService(db)
    update_data = faculty_in.model_dump(exclude_unset=True)

    async def action():
        await service.update_faculty(session_id, code, **update_data)

    return await _execute_and_respond(db, action, "Faculty updated successfully.")


@router.delete("/{session_id}/faculties/{code}", response_model=GenericResponse)
async def delete_staged_faculty(
    session_id: UUID,
    code: str,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Delete a faculty from the staging table."""
    service = StagingService(db)

    async def action():
        await service.delete_faculty(session_id, code)

    return await _execute_and_respond(db, action, "Faculty deleted successfully.")


# =================================================================
# Programmes Endpoints
# =================================================================


@router.post("/{session_id}/programmes", response_model=GenericResponse)
async def add_staged_programme(
    session_id: UUID,
    programme_in: staging_schemas.ProgrammeCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Add a new programme to the staging table."""
    service = StagingService(db)

    async def action():
        await service.add_programme(session_id, **programme_in.model_dump())

    return await _execute_and_respond(db, action, "Programme added successfully.")


@router.put("/{session_id}/programmes/{code}", response_model=GenericResponse)
async def update_staged_programme(
    session_id: UUID,
    code: str,
    programme_in: staging_schemas.ProgrammeUpdate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Update a programme in the staging table."""
    service = StagingService(db)
    update_data = programme_in.model_dump(exclude_unset=True)

    async def action():
        await service.update_programme(session_id, code, **update_data)

    return await _execute_and_respond(db, action, "Programme updated successfully.")


@router.delete("/{session_id}/programmes/{code}", response_model=GenericResponse)
async def delete_staged_programme(
    session_id: UUID,
    code: str,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Delete a programme from the staging table."""
    service = StagingService(db)

    async def action():
        await service.delete_programme(session_id, code)

    return await _execute_and_respond(db, action, "Programme deleted successfully.")


# =================================================================
# Rooms Endpoints
# =================================================================


@router.post("/{session_id}/rooms", response_model=GenericResponse)
async def add_staged_room(
    session_id: UUID,
    room_in: staging_schemas.RoomCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Add a new room to the staging table."""
    service = StagingService(db)

    async def action():
        await service.add_room(session_id, **room_in.model_dump())

    return await _execute_and_respond(db, action, "Room added successfully.")


@router.put("/{session_id}/rooms/{code}", response_model=GenericResponse)
async def update_staged_room(
    session_id: UUID,
    code: str,
    room_in: staging_schemas.RoomUpdate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Update a room in the staging table."""
    service = StagingService(db)
    update_data = room_in.model_dump(exclude_unset=True)

    async def action():
        await service.update_room(session_id, code, **update_data)

    return await _execute_and_respond(db, action, "Room updated successfully.")


@router.delete("/{session_id}/rooms/{code}", response_model=GenericResponse)
async def delete_staged_room(
    session_id: UUID,
    code: str,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Delete a room from the staging table."""
    service = StagingService(db)

    async def action():
        await service.delete_room(session_id, code)

    return await _execute_and_respond(db, action, "Room deleted successfully.")


# =================================================================
# Staff Endpoints
# =================================================================


@router.post("/{session_id}/staff", response_model=GenericResponse)
async def add_staged_staff(
    session_id: UUID,
    staff_in: staging_schemas.StaffCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Add a new staff member to the staging table."""
    service = StagingService(db)

    async def action():
        await service.add_staff(session_id, **staff_in.model_dump())

    return await _execute_and_respond(db, action, "Staff member added successfully.")


@router.put("/{session_id}/staff/{staff_number}", response_model=GenericResponse)
async def update_staged_staff(
    session_id: UUID,
    staff_number: str,
    staff_in: staging_schemas.StaffUpdate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Update a staff member in the staging table."""
    service = StagingService(db)
    update_data = staff_in.model_dump(exclude_unset=True)

    async def action():
        await service.update_staff(session_id, staff_number, **update_data)

    return await _execute_and_respond(db, action, "Staff member updated successfully.")


@router.delete("/{session_id}/staff/{staff_number}", response_model=GenericResponse)
async def delete_staged_staff(
    session_id: UUID,
    staff_number: str,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Delete a staff member from the staging table."""
    service = StagingService(db)

    async def action():
        await service.delete_staff(session_id, staff_number)

    return await _execute_and_respond(db, action, "Staff member deleted successfully.")


# =================================================================
# Staff Unavailability Endpoints
# =================================================================


@router.post("/{session_id}/staff-unavailability", response_model=GenericResponse)
async def add_staged_staff_unavailability(
    session_id: UUID,
    data_in: staging_schemas.StaffUnavailabilityCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Add a staff unavailability record to the staging table."""
    service = StagingService(db)

    async def action():
        await service.add_staff_unavailability(session_id, **data_in.model_dump())

    return await _execute_and_respond(
        db, action, "Staff unavailability record added successfully."
    )


@router.put(
    "/{session_id}/staff-unavailability/{staff_number}/{unavailable_date}/{period_name}",
    response_model=GenericResponse,
)
async def update_staged_staff_unavailability(
    session_id: UUID,
    staff_number: str,
    unavailable_date: date,
    period_name: str,
    data_in: staging_schemas.StaffUnavailabilityUpdate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Update a staff unavailability record in the staging table."""
    service = StagingService(db)

    async def action():
        await service.update_staff_unavailability(
            session_id,
            staff_number,
            unavailable_date,
            period_name,
            data_in.reason,
        )

    return await _execute_and_respond(
        db, action, "Staff unavailability record updated successfully."
    )


@router.delete(
    "/{session_id}/staff-unavailability/{staff_number}/{unavailable_date}/{period_name}",
    response_model=GenericResponse,
)
async def delete_staged_staff_unavailability(
    session_id: UUID,
    staff_number: str,
    unavailable_date: date,
    period_name: str,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Delete a staff unavailability record from the staging table."""
    service = StagingService(db)

    async def action():
        await service.delete_staff_unavailability(
            session_id, staff_number, unavailable_date, period_name
        )

    return await _execute_and_respond(
        db, action, "Staff unavailability record deleted successfully."
    )


# =================================================================
# Students Endpoints
# =================================================================


@router.post("/{session_id}/students", response_model=GenericResponse)
async def add_staged_student(
    session_id: UUID,
    student_in: staging_schemas.StudentCreate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Add a new student to the staging table."""
    service = StagingService(db)

    async def action():
        await service.add_student(session_id, **student_in.model_dump())

    return await _execute_and_respond(db, action, "Student added successfully.")


@router.put("/{session_id}/students/{matric_number}", response_model=GenericResponse)
async def update_staged_student(
    session_id: UUID,
    matric_number: str,
    student_in: staging_schemas.StudentUpdate,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Update a student in the staging table."""
    service = StagingService(db)
    update_data = student_in.model_dump(exclude_unset=True)

    async def action():
        await service.update_student(session_id, matric_number, **update_data)

    return await _execute_and_respond(db, action, "Student updated successfully.")


@router.delete("/{session_id}/students/{matric_number}", response_model=GenericResponse)
async def delete_staged_student(
    session_id: UUID,
    matric_number: str,
    db: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    """Delete a student from the staging table."""
    service = StagingService(db)

    async def action():
        await service.delete_student(session_id, matric_number)

    return await _execute_and_respond(db, action, "Student deleted successfully.")
