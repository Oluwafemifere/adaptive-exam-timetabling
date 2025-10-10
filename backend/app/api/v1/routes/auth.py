# backend/app/api/v1/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import db_session

# MODIFIED: Core auth functions now handle token creation with role
from ....core.auth import authenticate_user, create_token_for_user
from ....services.user_management import AuthenticationService
from ....schemas.system import GenericResponse

# MODIFIED: Schema now includes the role and new registration models
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
    # Use the core authentication function which is more direct.
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # create_token_for_user now returns a dictionary matching the updated Token schema
    token_data = await create_token_for_user(user)
    return token_data


# --- NEW: Student Self-Registration Endpoint ---
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
    Allows a student who is already in the database to create their user account.
    """
    service = AuthenticationService(db)
    result = await service.self_register_student(
        matric_number=register_in.matric_number,
        email=register_in.email,
        password=register_in.password,
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


# --- NEW: Staff Self-Registration Endpoint ---
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
    Allows a staff member who is already in the database to create their user account.
    """
    service = AuthenticationService(db)
    result = await service.self_register_staff(
        staff_number=register_in.staff_number,
        email=register_in.email,
        password=register_in.password,
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
