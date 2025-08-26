from fastapi import FastAPI
from app.api.v1.api import api_router
from app.core.config import Settings

app = FastAPI(title="Baze Exam Timetabling API", version="1.0")
app.include_router(api_router)
