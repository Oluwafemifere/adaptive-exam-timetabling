# app/database.py
"""
Async database configuration and connection management.
Requires an async DB driver, e.g. postgresql+asyncpg://...
"""

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
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base model
Base = declarative_base()


class DatabaseManager:
    """Manages async SQLAlchemy engine and async session factory."""

    def __init__(self) -> None:
        self.engine: Optional[AsyncEngine] = None
        self.AsyncSessionLocal: Optional[async_sessionmaker] = None
        self._is_initialized = False

    async def initialize(
        self,
        database_url: Optional[str] = None,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        echo: bool = False,
    ) -> None:
        """
        Initialize async engine and async session factory.
        Use an async DB URL such as postgresql+asyncpg://user:pass@host/db
        """
        if self._is_initialized:
            logger.warning("Database already initialized")
            return

        db_url = database_url or os.getenv(
            "DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/exam_system"
        )
        if not db_url:
            raise ValueError("Database URL is required and must be async driver compatible")

        # convenience: convert common sync prefix to async one if user provided it
        if db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        try:
            # create async engine; pool options forwarded to the sync engine
            self.engine = create_async_engine(
                db_url,
                echo=echo,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                pool_recycle=pool_recycle,
                pool_pre_ping=True,
            )

            # async session factory
            self.AsyncSessionLocal = async_sessionmaker(
                self.engine, expire_on_commit=False, class_=AsyncSession
            )

            # setup event listeners on the underlying sync engine
            self._setup_event_listeners()

            # test connection
            await self._test_connection()

            self._is_initialized = True
            logger.info("Async database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize async database: {e}")
            raise

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
                # not fatal; ignore
                pass

        @event.listens_for(sync_engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            logger.debug("Connection checked out from pool")

        @event.listens_for(sync_engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            logger.debug("Connection returned to pool")

    async def _test_connection(self) -> None:
        """Run a lightweight query to ensure connectivity."""
        engine = self.engine
        if engine is None:
            raise RuntimeError("Engine not initialized")
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                logger.info("Database connection test successful")
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            raise

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Async context manager returning an AsyncSession.
        Usage:
            async with db_manager.get_session() as session:
                ...
        """
        if not self._is_initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        if not self.AsyncSessionLocal:
            raise RuntimeError("AsyncSessionLocal not initialized")

        async with self.AsyncSessionLocal() as session:
            try:
                yield session
            except Exception as e:
                logger.error(f"Async DB session error: {e}")
                await session.rollback()
                raise

    @asynccontextmanager
    async def get_db_transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Async context manager with commit on success and rollback on failure.
        Usage:
            async with db_manager.get_db_transaction() as session:
                ...
        """
        if not self.AsyncSessionLocal:
            raise RuntimeError("Database not initialized")
        async with self.AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                logger.error(f"Transaction error: {e}")
                await session.rollback()
                raise

    async def create_all_tables(self) -> None:
        """Create tables using async engine."""
        if not self._is_initialized:
            raise RuntimeError("Database not initialized")
        engine = self.engine
        if engine is None:
            raise RuntimeError("Engine not initialized")
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("All tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    async def drop_all_tables(self) -> None:
        """Drop tables using async engine."""
        if not self._is_initialized:
            raise RuntimeError("Database not initialized")
        engine = self.engine
        if engine is None:
            raise RuntimeError("Engine not initialized")
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            logger.info("All tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise

    async def get_connection_info(self) -> Dict[str, Any]:
        """Return pool information when available."""
        if not self.engine:
            return {}
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
    FastAPI dependency that yields an AsyncSession.
    Use in routes as: db: AsyncSession = Depends(get_db)
    """
    if not db_manager._is_initialized:
        raise RuntimeError("Database not initialized. Call initialize() first.")
    if not db_manager.AsyncSessionLocal:
        raise RuntimeError("AsyncSessionLocal not initialized")
    async with db_manager.AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise


async def init_db(database_url: Optional[str] = None, create_tables: bool = False) -> None:
    """
    Initialize the async database. Call this during app startup.
    Example:
        await init_db(os.getenv("DATABASE_URL"), create_tables=True)
    """
    await db_manager.initialize(database_url=database_url)
    if create_tables:
        await db_manager.create_all_tables()


async def check_db_health() -> Dict[str, Any]:
    """Async health check."""
    try:
        engine = db_manager.engine
        if engine is None:
            raise RuntimeError("Engine not initialized")
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            info = await db_manager.get_connection_info()
            return {"status": "healthy", "connection_pool": info, "message": "Database is accessible"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e), "message": "Database connection failed"}


class DatabaseError(Exception):
    """Custom database error."""
    pass


def retry_db_operation(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retrying sync callables that may use SQLAlchemy. Keep sync for simple wrappers."""
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
                        logger.warning(f"DB operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                        time.sleep(delay * (2 ** attempt))
                    else:
                        logger.error(f"DB operation failed after {max_retries + 1} attempts")
            raise DatabaseError(f"Operation failed after {max_retries + 1} attempts") from last_exception
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
