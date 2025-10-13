# backend/app/api/v1/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session
from ....core.auth import authenticate_user, create_token_for_user
from ....services.user_management import AuthenticationService
from ....services.data_retrieval import (
    DataRetrievalService,
)  # FIX: Import DataRetrievalService
from ....schemas.system import GenericResponse
from ....schemas.auth import Token, StudentSelfRegister, StaffSelfRegister

router = APIRouter()


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(db_session),
):
    """
    Authenticates a user and returns an access token along with their role.
    """
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_data = await create_token_for_user(user)
    # FIX: The create_token_for_user service was not adding the role to the
    # response dictionary. We add it here from the authenticated user object
    # to ensure the response conforms to the Token schema.
    token_data["role"] = user.role
    return token_data


@router.post(
    "/register/student",
    response_model=GenericResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Student Self-Registration",
)
async def self_register_student(
    register_in: StudentSelfRegister,
    db: AsyncSession = Depends(db_session),
):
    """
    Allows a student to create their user account against the active academic session.
    """
    # FIX: Fetch active session to pass its ID to the service.
    data_service = DataRetrievalService(db)
    active_session = await data_service.get_active_academic_session()
    if not active_session or not active_session.get("id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active academic session found. Self-registration is currently disabled.",
        )
    session_id = active_session["id"]

    service = AuthenticationService(db)
    result = await service.self_register_student(
        matric_number=register_in.matric_number,
        email=register_in.email,
        password=register_in.password,
        session_id=session_id,  # Pass the active session ID
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Student registration failed."),
        )
    return GenericResponse(
        success=True,
        message="Student user account created successfully.",
        data={"user_id": result.get("user_id")},
    )


@router.post(
    "/register/staff",
    response_model=GenericResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Staff Self-Registration",
)
async def self_register_staff(
    register_in: StaffSelfRegister,
    db: AsyncSession = Depends(db_session),
):
    """
    Allows a staff member to create their user account against the active academic session.
    """
    # FIX: Fetch active session to pass its ID to the service.
    data_service = DataRetrievalService(db)
    active_session = await data_service.get_active_academic_session()
    if not active_session or not active_session.get("id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active academic session found. Self-registration is currently disabled.",
        )
    session_id = active_session["id"]

    service = AuthenticationService(db)
    result = await service.self_register_staff(
        staff_number=register_in.staff_number,
        email=register_in.email,
        password=register_in.password,
        session_id=session_id,  # Pass the active session ID
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Staff registration failed."),
        )
    return GenericResponse(
        success=True,
        message="Staff user account created successfully.",
        data={"user_id": result.get("user_id")},
    )
