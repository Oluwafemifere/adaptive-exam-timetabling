from fastapi import APIRouter
from app.api.v1.routes import auth, uploads, timetables, jobs, websockets

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router,       prefix="/auth",       tags=["auth"])
api_router.include_router(uploads.router,    prefix="/upload",     tags=["uploads"])
api_router.include_router(timetables.router, prefix="/timetables", tags=["timetables"])
api_router.include_router(jobs.router,       prefix="/jobs",       tags=["jobs"])
api_router.include_router(websockets.router, prefix="/ws",         tags=["websockets"])
