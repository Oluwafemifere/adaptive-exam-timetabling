# scheduling_engine/tests/conftest.py

"""
Pytest configuration and fixtures for scheduling engine tests.
"""

import pytest
import asyncio
import logging
from uuid import UUID, uuid4
from datetime import date, timedelta

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


# Pytest asyncio configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def session_id():
    """Generate a test session ID"""
    return uuid4()


@pytest.fixture
def exam_period():
    """Generate test exam period dates"""
    start_date = date.today() + timedelta(days=30)
    end_date = start_date + timedelta(days=14)
    return start_date, end_date
