# backend\app\api\v1\api.py
from fastapi import APIRouter
from ...api.v1.routes import router as routes_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(routes_router)
