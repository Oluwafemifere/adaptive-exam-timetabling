#C:\Users\fresh\OneDrive\Dokumen\thesis\proj\CODE\adaptive-exam-timetabling\backend\app\api\__init__.py
from fastapi import FastAPI
from app.api.v1.api import api_router
from .deps import oauth2_scheme, db_session, current_user

app = FastAPI(title="Baze Exam Timetabling API", version="1.0")
app.include_router(api_router)

__all__ = ["app", "api_router", "oauth2_scheme", "db_session", "current_user"]
