# backend/app/api/v1/routes/__init__.py
from fastapi import APIRouter
from .auth import router as auth_router
from .jobs import router as jobs_router
from .uploads import router as uploads_router
from .websockets import router as websockets_router
from .scheduling import router as scheduling_router
from .courses import router as courses_router
from .rooms import router as rooms_router
from .exams import router as exams_router
from .timetables import router as timetables_router
from .users import router as users_router
from .academic_sessions import router as sessions_router
from .session_setup import router as session_setup_router
from .seeding import router as seeding_router
from .versions import router as versions_router
from .system import router as system_router
from .admin import router as admin_router
from .roles import router as roles_router
from .schedules import router as schedules_router
from .scenarios import router as scenarios_router
from .portal import router as portal_router
from .dashboard import router as dashboard_router
from .notifications import router as notifications_router
from .profile import router as profile_router
from .staging import router as staging_router

# Import the new configurations router
from .configurations import router as configurations_router

# Create a main router that includes all sub-routers
router = APIRouter()

# Include all route modules with their respective prefixes and tags
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(users_router, prefix="/users", tags=["User Management"])
router.include_router(roles_router, prefix="/roles", tags=["Role Management"])
router.include_router(profile_router, prefix="/profile", tags=["User Profile"])

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
router.include_router(scenarios_router, prefix="/scenarios", tags=["Scenarios"])
router.include_router(jobs_router, prefix="/jobs", tags=["Background Jobs"])
router.include_router(schedules_router, prefix="/schedules", tags=["Schedules"])
router.include_router(sessions_router, prefix="/sessions", tags=["Academic Sessions"])

# System & Administration
router.include_router(versions_router, prefix="/versions", tags=["Versions"])
# NEW: Include the dedicated configurations router
router.include_router(
    configurations_router,
    prefix="/configurations",
    tags=["System & Constraint Configurations"],
)
router.include_router(
    system_router, prefix="/system", tags=["System Administration"]
)  # Renamed tag for clarity
router.include_router(admin_router, prefix="/admin", tags=["Administration"])
router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
router.include_router(
    notifications_router, prefix="/notifications", tags=["Notifications"]
)


# User Portals
router.include_router(portal_router, prefix="/portal", tags=["User Portal"])

# Utilities
router.include_router(uploads_router, prefix="/uploads", tags=["File Uploads"])
router.include_router(websockets_router, prefix="/ws", tags=["WebSockets"])
router.include_router(
    session_setup_router, prefix="/setup", tags=["Session Setup Wizard"]
)
router.include_router(seeding_router, prefix="/seeding", tags=["Data Seeding Status"])
router.include_router(
    staging_router,
    prefix="/staging-records",  # Using a distinct prefix
    tags=["Staging Area Management"],
)


# Export the main router for use in the main API
__all__ = ["router"]
