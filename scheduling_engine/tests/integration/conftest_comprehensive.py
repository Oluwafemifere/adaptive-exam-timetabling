# scheduling_engine/tests/integration/conftest_comprehensive.py

"""
Comprehensive pytest configuration for constraint integration tests.

Provides fixtures, configuration, and environment setup for the comprehensive
constraint integration test suite.
"""

import pytest
import asyncio
import logging
import os
from pathlib import Path
from typing import Optional
from uuid import uuid4
from datetime import date, timedelta

# Import test configuration
from test_comprehensive_constraint_integration import (
    TestConfiguration,
    ComprehensiveConstraintTester,
    setup_logging,
)


# Configure pytest-asyncio
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()

    yield loop

    # Close the loop
    try:
        loop.close()
    except RuntimeError:
        pass  # Loop may already be closed


@pytest.fixture(scope="session")
def test_configuration():
    """Create test configuration based on environment variables"""

    # Check for quick test mode
    quick_mode = os.getenv("TEST_QUICK_MODE", "0") == "1"

    # Check for custom solver time
    max_solver_time = int(os.getenv("TEST_MAX_SOLVER_TIME", "30"))

    # Check for solver log settings
    disable_solver_logs = os.getenv("TEST_DISABLE_SOLVER_LOGS", "0") == "1"

    if quick_mode:
        # Reduced configuration for quick tests
        config = TestConfiguration(
            num_students=100,
            num_courses=8,
            num_exams=10,
            num_rooms=15,
            num_time_slots=3,
            num_instructors=10,
            num_staff=3,
            exam_period_days=10,
            max_solver_time_seconds=15,
            enable_presolve_logging=not disable_solver_logs,
            enable_search_logging=not disable_solver_logs,
        )
    else:
        # Full configuration for comprehensive tests
        config = TestConfiguration(
            num_students=300,
            num_courses=15,
            num_exams=15,
            num_rooms=8,
            num_time_slots=3,
            num_instructors=10,
            num_staff=6,
            exam_period_days=10,
            max_solver_time_seconds=max_solver_time,
            enable_presolve_logging=not disable_solver_logs,
            enable_search_logging=not disable_solver_logs,
        )

    return config


@pytest.fixture(scope="session")
def comprehensive_tester(test_configuration):
    """Create comprehensive constraint tester instance"""

    # Setup logging for the test session
    setup_logging()

    # Create tester
    tester = ComprehensiveConstraintTester(test_configuration)

    return tester


@pytest.fixture
def session_id():
    """Generate unique session ID for each test"""
    return uuid4()


@pytest.fixture
def exam_period():
    """Generate test exam period dates"""
    start_date = date.today() + timedelta(days=30)
    end_date = start_date + timedelta(days=14)
    return start_date, end_date


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers and options"""

    # Add custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (may take more than 30 seconds)"
    )
    config.addinivalue_line("markers", "solver: marks tests that require CP-SAT solver")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "performance: marks tests as performance tests")

    # Set up logging for pytest
    logging.getLogger("pytest").setLevel(logging.INFO)


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""

    for item in items:
        # Mark solver-related tests
        if "solver" in item.name.lower():
            item.add_marker(pytest.mark.solver)

        # Mark integration tests
        if "integration" in item.name.lower():
            item.add_marker(pytest.mark.integration)

        # Mark performance tests
        if "performance" in item.name.lower():
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)


def pytest_runtest_setup(item):
    """Setup before each test runs"""

    # Check for environment requirements
    if item.get_closest_marker("solver"):
        try:
            import ortools
        except ImportError:
            pytest.skip("OR-Tools not available")

    # Log test start
    test_logger = logging.getLogger("pytest.test")
    test_logger.info(f"Starting test: {item.name}")


def pytest_runtest_teardown(item, nextitem):
    """Cleanup after each test runs"""

    # Log test completion
    test_logger = logging.getLogger("pytest.test")
    test_logger.info(f"Completed test: {item.name}")


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Custom terminal summary after test run"""

    print("\n" + "=" * 60)
    print("COMPREHENSIVE CONSTRAINT TEST SUMMARY")
    print("=" * 60)

    # Get test statistics
    passed = len(terminalreporter.stats.get("passed", []))
    failed = len(terminalreporter.stats.get("failed", []))
    skipped = len(terminalreporter.stats.get("skipped", []))
    errors = len(terminalreporter.stats.get("error", []))

    total = passed + failed + skipped + errors

    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")

    if failed > 0 or errors > 0:
        print(f"\n {failed + errors} test(s) failed")
        print("Check the detailed logs for more information")
    else:
        print(f"\n All {passed} tests passed successfully!")

    # Show log file location
    logs_dir = Path("test_logs")
    if logs_dir.exists():
        log_files = list(logs_dir.glob("*.log"))
        if log_files:
            latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
            print(f" Detailed logs: {latest_log}")

    print("=" * 60)


# Pytest command line options
def pytest_addoption(parser):
    """Add custom command line options"""

    parser.addoption(
        "--quick",
        action="store_true",
        default=False,
        help="Run quick tests with reduced data size",
    )

    parser.addoption(
        "--solver-time", type=int, default=30, help="Maximum solver time in seconds"
    )

    parser.addoption(
        "--no-solver-logs",
        action="store_true",
        default=False,
        help="Disable detailed solver logs",
    )
