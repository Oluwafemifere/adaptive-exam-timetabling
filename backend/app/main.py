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
from .config import get_settings
from .logging_config import LOGGING_CONFIG

# Get a logger for this specific module
logger = logging.getLogger(__name__)

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


# CORS middleware
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://frontend:80",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
    from .database import check_db_health

    db_health = await check_db_health()
    return {
        "status": "healthy" if db_health["status"] == "healthy" else "unhealthy",
        "service": "backend",
        "database": db_health,
    }


@app.get("/api/v1/test")
async def test_endpoint():
    # Example of an endpoint that will raise an error
    # x = 1 / 0
    return {"message": "Backend is running successfully!", "test": "passed"}


if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=LOGGING_CONFIG,
    )
