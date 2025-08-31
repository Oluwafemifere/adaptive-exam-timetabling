# backend/app/tests/conftest.py

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.database import get_db
from app.models import Base

# Use your actual database URL (not a test database)
ASYNC_DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/postgres"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create database engine using the existing database"""
    engine = create_async_engine(
        ASYNC_DATABASE_URL,
        echo=True,  # Set to True to see SQL queries for debugging
        poolclass=NullPool,
    )

    # Verify connection and that the schema exists
    async with engine.connect() as conn:
        # Check if the exam_system schema exists
        result = await conn.execute(
            text(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'exam_system'"
            )
        )
        schema_exists = result.scalar()
        assert (
            schema_exists is not None
        ), "exam_system schema does not exist in the database"

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session with proper cleanup."""
    async_session = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )

    async with async_session() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest_asyncio.fixture
async def client(test_session) -> AsyncGenerator:
    """Create test HTTP client with database override."""

    async def override_get_db():
        try:
            yield test_session
        finally:
            await test_session.rollback()

    app.dependency_overrides[get_db] = override_get_db

    from httpx import AsyncClient, ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# Event loop fixture for session scope
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for session scope."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()
