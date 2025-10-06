# backend/app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging

# Import your components
from .api.v1.api import api_router
from .database import init_db
from .config import get_settings  # Correctly aliased as settings below
from .logging_config import LOGGING_CONFIG

# Get a logger for this specific module
logger = logging.getLogger(__name__)

# Load application settings from the configuration file/environment
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    logger.info("Starting up the application...")
    try:
        await init_db(database_url=settings.DATABASE_URL, create_tables=True)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise

    yield

    logger.info("Shutting down the application...")
    from .database import db_manager

    await db_manager.close()


app = FastAPI(
    title="Baze University Exam Scheduler API",
    description="Adaptive Exam Timetabling System for Baze University",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch any unhandled exceptions and log them with a full traceback.
    Returns a generic 500 error to the client to avoid leaking details.
    """
    logger.error(
        f"Unhandled exception for request {request.method} {request.url}: {exc}",
        exc_info=True,  # This is the key to getting the traceback
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."},
    )


# --- FIX: Use the CORS_ORIGINS from the settings file ---
# This makes the configuration dynamic and manageable through your .env file,
# which is the correct way to handle environment-specific settings.


# Include API routes from the v1 api module
app.include_router(api_router, prefix="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint providing basic API information."""
    return {
        "message": "Welcome to Baze University Exam Scheduler API",
        "version": "1.0.0",
        "status": "active",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint to verify service and database connectivity."""
    from .database import check_db_health

    db_health = await check_db_health()
    return {
        "status": "healthy" if db_health["status"] == "healthy" else "unhealthy",
        "service": "backend",
        "database": db_health,
    }


# This test endpoint is now part of the main API router,
# you can remove it from here if it's defined in api_router to avoid duplication.
# If not, it can remain here.
# @app.get("/api/v1/test")
# async def test_endpoint():
#     return {"message": "Backend is running successfully!", "test": "passed"}


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=LOGGING_CONFIG,
    )
