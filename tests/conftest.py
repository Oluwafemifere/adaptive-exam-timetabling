# tests/conftest.py
import asyncio
import logging
import pytest
from backend.app.tasks.celery_app import celery_app
import pytest_asyncio
from backend.app.models.users import User
from uuid import uuid4


# Set event loop policy for Windows at session start
@pytest.fixture(scope="session", autouse=True)
def event_loop_policy():
    """Use SelectorEventLoop on Windows to avoid Proactor issues."""
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# Apply eager mode only for non-integration tests
def pytest_configure(config):
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        filename="all_logs.log",
        filemode="w",
    )
    if not config.getoption("-m") or "integration" not in config.getoption("-m"):
        celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)


@pytest_asyncio.fixture
async def test_user(test_session):
    unique_email = f"test_{uuid4()}@example.com"
    user = User(id=uuid4(), email=unique_email, first_name="Test", last_name="User")
    test_session.add(user)
    await test_session.commit()
    return user
