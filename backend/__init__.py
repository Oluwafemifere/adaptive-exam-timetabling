# backend/__init__.py

"""
Backend package for Adaptive Exam Timetabling System.
Exposes all core modules and components.
"""

from .app import (
    AppError,
    InfeasibleProblemError,
    JobAccessDeniedError,
    JobNotFoundError,
    SchedulingError,
    scheduling,
    notification,
    export,
    data_validation,
    data_retrieval,
    data_management,
    DatabaseSeeder,
)

from .app.database import (
    Base,
    DatabaseManager,
    db_manager,
    get_db,
    init_db,
    check_db_health,
    DatabaseError,
    retry_db_operation,
)

from .app.config import (
    Settings,
    get_settings,
    get_settings_for_environment,
    validate_settings,
    setup_logging,
    DevelopmentSettings,
    ProductionSettings,
    TestingSettings,
)

from .app.main import app

# Re-export all important components
__all__ = [
    # Core components
    "AppError",
    "SchedulingError",
    "InfeasibleProblemError",
    "JobNotFoundError",
    "JobAccessDeniedError",
    # Services
    "scheduling",
    "notification",
    "export",
    "data_validation",
    "data_retrieval",
    "data_management",
    "DatabaseSeeder",
    # Database
    "Base",
    "DatabaseManager",
    "db_manager",
    "get_db",
    "init_db",
    "check_db_health",
    "DatabaseError",
    "retry_db_operation",
    # Configuration
    "Settings",
    "get_settings",
    "get_settings_for_environment",
    "validate_settings",
    "setup_logging",
    "DevelopmentSettings",
    "ProductionSettings",
    "TestingSettings",
    # Main application
    "app",
]
