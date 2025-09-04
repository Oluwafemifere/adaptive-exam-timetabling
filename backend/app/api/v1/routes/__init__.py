# backend\app\api\v1\routes\__init__.py
from fastapi import APIRouter
from .auth import router as auth_router
from .jobs import router as jobs_router

# from .timetables import router as timetables_router
from .uploads import router as uploads_router
from .websockets import router as websockets_router

# 🔥 FIX: Uncomment and import the scheduling router
# from .scheduling import router as scheduling_router

# Create a main router that includes all sub-routers
router = APIRouter()

# Include all route modules with their respective prefixes
router.include_router(auth_router, prefix="/auth", tags=["authentication"])
router.include_router(jobs_router, prefix="/jobs", tags=["background jobs"])
# router.include_router(
#     timetables_router, prefix="/timetables", tags=["timetable management"]
# )
router.include_router(uploads_router, prefix="/uploads", tags=["file uploads"])
router.include_router(websockets_router, prefix="/ws", tags=["websockets"])

# 🔥 FIX: Add the scheduling router that was commented out
# router.include_router(scheduling_router, prefix="/scheduling", tags=["scheduling"])

# Export the main router for use in the main API
__all__ = ["router"]
