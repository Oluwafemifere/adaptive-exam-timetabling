# backend/app/api/v1/routes/__init__.py
from fastapi import APIRouter
from .auth import router as auth_router
from .jobs import router as jobs_router
from .uploads import router as uploads_router
from .websockets import router as websockets_router

# Import the new and restored routers
from .scheduling import router as scheduling_router
from .courses import router as courses_router
from .rooms import router as rooms_router
from .exams import router as exams_router
from .timetables import router as timetables_router
from .users import router as users_router

# Create a main router that includes all sub-routers
router = APIRouter()

# Include all route modules with their respective prefixes and tags
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(users_router, prefix="/users", tags=["User Management"])

# Core Data Management
router.include_router(courses_router, prefix="/courses", tags=["Courses"])
router.include_router(rooms_router, prefix="/rooms", tags=["Rooms & Venues"])
router.include_router(exams_router, prefix="/exams", tags=["Exams"])

# Scheduling & Timetables
router.include_router(
    scheduling_router, prefix="/scheduling", tags=["Scheduling Engine"]
)
router.include_router(
    timetables_router, prefix="/timetables", tags=["Timetable Management"]
)
router.include_router(jobs_router, prefix="/jobs", tags=["Background Jobs"])

# Utilities
router.include_router(uploads_router, prefix="/uploads", tags=["File Uploads"])
router.include_router(websockets_router, prefix="/ws", tags=["WebSockets"])


# Export the main router for use in the main API
__all__ = ["router"]
