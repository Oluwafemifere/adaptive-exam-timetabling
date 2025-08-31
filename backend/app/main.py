# backend\app\main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging

# Import your components
from app.api.v1.api import api_router
from app.database import init_db
from app.config import get_settings


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    # Startup
    logger.info("Starting up the application...")
    try:
        # Initialize database
        await init_db(database_url=settings.DATABASE_URL, create_tables=True)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down the application...")
    from app.database import db_manager

    await db_manager.close()


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Baze University Exam Scheduler API",
    description="Adaptive Exam Timetabling System for Baze University",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to Baze University Exam Scheduler API",
        "version": "1.0.0",
        "status": "active",
    }


@app.get("/health")
async def health_check():
    from app.database import check_db_health

    db_health = await check_db_health()
    return {
        "status": "healthy" if db_health["status"] == "healthy" else "unhealthy",
        "service": "backend",
        "database": db_health,
    }


@app.get("/api/v1/test")
async def test_endpoint():
    return {"message": "Backend is running successfully!", "test": "passed"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
