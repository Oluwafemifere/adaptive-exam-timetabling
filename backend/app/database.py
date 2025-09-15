# app/database.py

"""
Updated database.py to handle schema-aware connections properly
"""

import asyncio
import os
import logging
from typing import Optional, AsyncGenerator, Dict, Any
from contextlib import asynccontextmanager

from sqlalchemy import text, event
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()


class DatabaseManager:
    """Manages async SQLAlchemy engine and async session factory with schema support."""

    def __init__(self) -> None:
        self.engine: Optional[AsyncEngine] = None
        self.AsyncSessionLocal: Optional[async_sessionmaker] = None
        self._is_initialized = False
        self._loop = None

    async def initialize(
        self,
        database_url: Optional[str] = None,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        echo: bool = False,
        schema: str = "exam_system",
        max_retries: int = 3,
        retry_delay: int = 1,
    ) -> None:
        """
        Initialize async engine and async session factory with schema support.
        Retries on failure.
        """
        current_loop = asyncio.get_running_loop()
        if self._is_initialized and self._loop == current_loop:
            logger.warning("Database already initialized")
            return

        db_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:password@localhost:5432/exam_system",
        )

        if not db_url:
            raise ValueError(
                "Database URL is required and must be async driver compatible"
            )

        # Convert sync prefix to async if needed
        if db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        last_error = None
        for attempt in range(max_retries):
            try:
                # Create async engine with schema support
                self.engine = create_async_engine(
                    db_url,
                    echo=echo,
                    pool_size=pool_size,
                    max_overflow=max_overflow,
                    pool_timeout=pool_timeout,
                    pool_recycle=pool_recycle,
                    pool_pre_ping=True,
                    connect_args={
                        "server_settings": {"search_path": f"{schema},public"}
                    },
                    future=True,
                )

                # Async session factory with schema awareness
                self.AsyncSessionLocal = async_sessionmaker(
                    bind=self.engine, expire_on_commit=False, class_=AsyncSession
                )

                # Setup event listeners
                self._setup_event_listeners()

                # Test connection
                await self._test_connection(schema)

                self._is_initialized = True
                self._loop = current_loop
                logger.info(
                    f"Async database initialized successfully with schema: {schema}"
                )
                return
            except Exception as e:
                last_error = e
                logger.error(
                    f"Database initialization attempt {attempt + 1}/{max_retries} failed: {e}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))

        # If all retries failed
        raise RuntimeError(
            f"Failed to initialize async database after {max_retries} attempts"
        ) from last_error

    def _setup_event_listeners(self) -> None:
        """Attach listeners to underlying sync engine for connection-level events."""
        if not self.engine:
            return

        sync_engine = getattr(self.engine, "sync_engine", None)
        if not sync_engine:
            return

        @event.listens_for(sync_engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            try:
                with dbapi_connection.cursor() as cursor:
                    cursor.execute("SET timezone TO 'UTC'")
            except Exception:
                pass

        @event.listens_for(sync_engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            logger.debug("Connection checked out from pool")

        @event.listens_for(sync_engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            logger.debug("Connection returned to pool")

    async def _test_connection(self, schema: str = "exam_system") -> None:
        """Run a lightweight query to ensure connectivity and schema access."""
        engine = self.engine
        if engine is None:
            raise RuntimeError("Engine not initialized")

        try:
            async with engine.connect() as conn:
                # Test basic connection
                await conn.execute(text("SELECT 1"))

                # Test schema access
                await conn.execute(text(f"SET search_path TO {schema}, public"))

                logger.info(
                    f"Database connection and schema '{schema}' access test successful"
                )

        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            raise

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Async context manager returning an AsyncSession with schema set.
        """
        if not self._is_initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        if not self.AsyncSessionLocal:
            raise RuntimeError("AsyncSessionLocal not initialized")

        async with self.AsyncSessionLocal() as session:
            try:
                # Ensure correct schema is set for each session
                await session.execute(text("SET search_path TO exam_system, public"))
                yield session
            except Exception as e:
                logger.error(f"Async DB session error: {e}")
                await session.rollback()
                raise

    @asynccontextmanager
    async def get_db_transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Async context manager with commit on success and rollback on failure.
        """
        if not self.AsyncSessionLocal:
            raise RuntimeError("Database not initialized")

        async with self.AsyncSessionLocal() as session:
            try:
                # Ensure correct schema
                await session.execute(text("SET search_path TO exam_system, public"))
                yield session
                await session.commit()
            except Exception as e:
                logger.error(f"Transaction error: {e}")
                logger.error(f"Transaction error details: {e}")
                logger.error(f"Error type: {type(e).__name__}")
                import traceback

                logger.error(f"Transaction traceback: {traceback.format_exc()}")
                await session.rollback()
                raise

    async def create_all_tables(self, schema: str = "exam_system") -> None:
        """Create tables using async engine in specified schema."""
        if not self._is_initialized:
            raise RuntimeError("Database not initialized")

        engine = self.engine
        if engine is None:
            raise RuntimeError("Engine not initialized")

        try:
            async with engine.begin() as conn:
                # Create schema if it doesn't exist
                await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))

                # Set search path
                await conn.execute(text(f"SET search_path TO {schema}, public"))

                # Create tables
                await conn.run_sync(Base.metadata.create_all)

            logger.info(f"All tables created successfully in schema: {schema}")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    async def drop_all_tables(self, schema: str = "exam_system") -> None:
        """Drop tables using async engine from specified schema."""
        if not self._is_initialized:
            raise RuntimeError("Database not initialized")

        engine = self.engine
        if engine is None:
            raise RuntimeError("Engine not initialized")

        try:
            async with engine.begin() as conn:
                # Disable foreign key constraints
                await conn.execute(text(f"SET CONSTRAINTS ALL DEFERRED"))
                # Drop tables
                await conn.run_sync(Base.metadata.drop_all)
            logger.info(f"All tables dropped successfully from schema: {schema}")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise

    async def ensure_schema_exists(self, schema: str = "exam_system") -> None:
        """Ensure the database schema exists."""
        if not self.engine:
            raise RuntimeError("Engine not initialized")

        try:
            async with self.engine.begin() as conn:
                await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
                logger.info(f"Schema '{schema}' ensured to exist")
        except Exception as e:
            logger.error(f"Failed to ensure schema exists: {e}")
            raise

    async def get_connection_info(self) -> Dict[str, Any]:
        """Return pool information when available."""
        if not self.engine:
            return {"status": "Engine not initialized"}

        pool = getattr(self.engine.sync_engine, "pool", None)
        if not pool:
            return {"status": "Pool info not available"}

        try:
            return {
                "pool_size": getattr(pool, "_pool_size", "N/A"),
                "checked_in": getattr(pool, "_checked_in", 0),
                "checked_out": getattr(pool, "_checked_out", 0),
                "overflow": getattr(pool, "_overflow", 0),
                "invalid": getattr(pool, "_invalid", 0),
            }
        except Exception:
            return {"status": "Pool info not available"}

    async def close(self) -> None:
        """Dispose the async engine."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")


# Global manager
db_manager = DatabaseManager()


# FastAPI dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an AsyncSession with proper schema.
    """
    if not db_manager._is_initialized:
        raise RuntimeError("Database not initialized. Call initialize() first.")
    if not db_manager.AsyncSessionLocal:
        raise RuntimeError("AsyncSessionLocal not initialized")

    async with db_manager.AsyncSessionLocal() as session:
        try:
            # Ensure correct schema for each request
            await session.execute(text("SET search_path TO exam_system, public"))
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise


async def init_db(
    database_url: Optional[str] = None,
    create_tables: bool = False,
    schema: str = "exam_system",
) -> None:
    """
    Initialize the async database with schema support.
    """
    await db_manager.initialize(database_url=database_url, schema=schema)

    if create_tables:
        await db_manager.ensure_schema_exists(schema)
        await db_manager.create_all_tables(schema)


async def check_db_health() -> Dict[str, Any]:
    """Async health check with schema verification."""
    try:
        engine = db_manager.engine
        if engine is None:
            raise RuntimeError("Engine not initialized")

        async with engine.connect() as conn:
            # Test basic connection
            await conn.execute(text("SELECT 1"))

            # Test schema access
            await conn.execute(text("SET search_path TO exam_system, public"))

            info = await db_manager.get_connection_info()
            return {
                "status": "healthy",
                "connection_pool": info,
                "message": "Database is accessible with schema support",
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Database connection failed",
        }


class DatabaseError(Exception):
    """Custom database error."""

    pass


def retry_db_operation(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retrying database operations."""
    import time
    from functools import wraps

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except SQLAlchemyError as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"DB operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
                        )
                        time.sleep(delay * (2**attempt))
                    else:
                        logger.error(
                            f"DB operation failed after {max_retries + 1} attempts"
                        )
                        raise DatabaseError(
                            f"Operation failed after {max_retries + 1} attempts"
                        ) from last_exception
            return wrapper

        return decorator


__all__ = [
    "Base",
    "DatabaseManager",
    "db_manager",
    "get_db",
    "init_db",
    "check_db_health",
    "DatabaseError",
    "retry_db_operation",
]
