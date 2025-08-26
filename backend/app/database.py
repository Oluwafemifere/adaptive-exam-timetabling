# app/database.py
"""
Database configuration and connection management for the Adaptive Exam Timetabling System.
Provides SQLAlchemy engine, session management, and connection pooling.
"""

import os
import logging
from typing import Generator, Optional, Iterator
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine
import psycopg2
from contextlib import contextmanager


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the SQLAlchemy base class
Base = declarative_base()

class DatabaseManager:
    """Manages database connections, sessions, and connection pooling."""
    
    def __init__(self):
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        self._is_initialized = False
    
    def initialize(
        self,
        database_url: Optional[str] = None,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        echo: bool = False
    ) -> None:
        """
        Initialize the database connection with connection pooling.
        
        Args:
            database_url: PostgreSQL connection string
            pool_size: Number of connections to maintain in the pool
            max_overflow: Maximum number of connections to allow beyond pool_size
            pool_timeout: Timeout for getting connection from pool
            pool_recycle: Time in seconds to recycle connections
            echo: Whether to log SQL statements
        """
        if self._is_initialized:
            logger.warning("Database already initialized")
            return
        
        # Get database URL from environment or parameter
        db_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:password@localhost:5432/exam_system"
        )
        if not db_url:
            raise ValueError("Database URL is required")
        
        try:
            # Create engine with connection pooling
            self.engine = create_engine(
                db_url,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                pool_recycle=pool_recycle,
                pool_pre_ping=True,  # Validate connections before use
                echo=echo,
                isolation_level="READ_COMMITTED"
            )
            
            # Configure session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # Add event listeners
            self._setup_event_listeners()
            
            # Test connection
            self._test_connection()
            
            self._is_initialized = True
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _setup_event_listeners(self) -> None:
        """Setup SQLAlchemy event listeners for connection management."""
        
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set PostgreSQL connection parameters."""
            if hasattr(dbapi_connection, 'execute'):
                # Set timezone
                with dbapi_connection.cursor() as cursor:
                    cursor.execute("SET timezone TO 'UTC'")
        
        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Log when a connection is checked out from the pool."""
            logger.debug("Connection checked out from pool")
        
        @event.listens_for(self.engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Log when a connection is returned to the pool."""
            logger.debug("Connection returned to pool")
    
    def _test_connection(self) -> None:
        """Test database connection."""
        if not self.engine:
            raise RuntimeError("Engine not initialized")
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                result.fetchone()
                logger.info("Database connection test successful")
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Iterator[Session]:
        """
        Get a database session with automatic cleanup.
        
        Yields:
            Session: SQLAlchemy database session
        """
        if not self._is_initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        if not self.SessionLocal:
            raise RuntimeError("SessionLocal not initialized")
        
        session = self.SessionLocal()
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    @contextmanager
    def get_db_transaction(self) -> Iterator[Session]:
        """
        Get a database session with transaction management.
        
        Yields:
            Session: SQLAlchemy database session with transaction
        """
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized")
            
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            logger.error(f"Transaction error: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def create_all_tables(self) -> None:
        """Create all database tables."""
        if not self._is_initialized:
            raise RuntimeError("Database not initialized")
        
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("All tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def drop_all_tables(self) -> None:
        """Drop all database tables."""
        if not self._is_initialized:
            raise RuntimeError("Database not initialized")
        
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("All tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise
    
    def get_connection_info(self) -> dict:
        """Get database connection pool information."""
        if not self.engine:
            return {}
        
        pool = self.engine.pool
        try:
            return {
                "pool_size": getattr(pool, '_pool_size', 'N/A'),  # Use _pool_size or similar
                "checked_in": getattr(pool, '_checked_in', 0),
                "checked_out": getattr(pool, '_checked_out', 0),
                "overflow": getattr(pool, '_overflow', 0),
                "invalid": getattr(pool, '_invalid', 0)
            }
        except:
            return {"status": "Pool info not available"}
    
    def close(self) -> None:
        """Close all database connections."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")

# Global database manager instance
db_manager = DatabaseManager()

# Dependency function for FastAPI
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency to get database session.
    
    Yields:
        Session: Database session
    """
    if not db_manager._is_initialized:
        raise RuntimeError("Database not initialized. Call initialize() first.")
    
    if not db_manager.SessionLocal:
        raise RuntimeError("SessionLocal not initialized")
    
    session = db_manager.SessionLocal()
    try:
        yield session
    except Exception as e:
        logger.error(f"Database session error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def init_db(
    database_url: Optional[str] = None,
    create_tables: bool = False
) -> None:
    """
    Initialize database connection and optionally create tables.
    
    Args:
        database_url: Database connection string
        create_tables: Whether to create tables after initialization
    """
    db_manager.initialize(database_url=database_url)
    
    if create_tables:
        db_manager.create_all_tables()

# Health check function
def check_db_health() -> dict:
    """
    Check database health and return status.
    
    Returns:
        dict: Database health status
    """
    try:
        with db_manager.get_session() as session:
            session.execute(text("SELECT 1"))
            connection_info = db_manager.get_connection_info()
            
            return {
                "status": "healthy",
                "connection_pool": connection_info,
                "message": "Database is accessible"
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Database connection failed"
        }

class DatabaseError(Exception):
    """Custom database error class."""
    pass

# Connection retry decorator
def retry_db_operation(max_retries: int = 3, delay: float = 1.0):
    """
    Decorator to retry database operations on failure.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
    """
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
                            f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
                        )
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                    else:
                        logger.error(f"Database operation failed after {max_retries + 1} attempts")
            
            raise DatabaseError(f"Operation failed after {max_retries + 1} attempts") from last_exception
        
        return wrapper
    return decorator

# Export commonly used items
__all__ = [
    'Base',
    'DatabaseManager',
    'db_manager',
    'get_db',
    'init_db',
    'check_db_health',
    'DatabaseError',
    'retry_db_operation'
]