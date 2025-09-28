# backend\app\config.py
"""
Configuration management for the Adaptive Exam Timetabling System.
Uses Pydantic for settings validation and environment variable management.
"""

import os
from typing import Optional, List, Dict, Any
from functools import lru_cache
from pathlib import Path


from pydantic import BaseModel, Field, field_validator, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Application settings
    APP_NAME: str = "Adaptive Exam Timetabling System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = Field(default="development", alias="ENV")

    # Database settings
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/postgres",
        alias="DATABASE_URL",
    )
    DATABASE_POOL_SIZE: int = Field(default=10, alias="DB_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, alias="DB_MAX_OVERFLOW")
    DATABASE_POOL_TIMEOUT: int = Field(default=30, alias="DB_POOL_TIMEOUT")
    DATABASE_POOL_RECYCLE: int = Field(default=3600, alias="DB_POOL_RECYCLE")
    DATABASE_SCHEMA: str = Field(default="exam_system", alias="DATABASE_SCHEMA")
    DATABASE_ECHO: bool = Field(default=False, alias="DATABASE_ECHO")
    # Redis settings (for Celery and caching)
    REDIS_URL: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    REDIS_CELERY_DB: int = Field(default=1, alias="REDIS_CELERY_DB")
    REDIS_CACHE_DB: int = Field(default=0, alias="REDIS_CACHE_DB")

    # Security settings
    SECRET_KEY: str = Field(
        default="your-secret-key-here-change-in-production",
        alias="SECRET_KEY",
    )
    JWT_SECRET_KEY: str = Field(
        default="jwt-secret-key-change-in-production",
        alias="JWT_SECRET_KEY",
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS settings
    ALLOWED_HOSTS: List[str] = Field(default=["*"], alias="ALLOWED_HOSTS")
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        alias="CORS_ORIGINS",
    )

    # File upload settings
    UPLOAD_DIR: str = Field(default="./uploads", alias="UPLOAD_DIR")
    MAX_UPLOAD_SIZE: int = Field(
        default=10 * 1024 * 1024, alias="MAX_UPLOAD_SIZE"
    )  # 10MB
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=[".csv", ".xlsx", ".xls"],
        alias="ALLOWED_EXTENSIONS",
    )

    # Backup settings
    BACKUP_DIR: str = Field(default="./backups", alias="BACKUP_DIR")
    BACKUP_S3_BUCKET: Optional[str] = Field(default=None, alias="BACKUP_S3_BUCKET")

    # AWS settings
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(
        default=None, alias="AWS_SECRET_ACCESS_KEY"
    )
    AWS_REGION: str = Field(default="us-east-1", alias="AWS_REGION")

    # Email settings
    SMTP_HOST: Optional[str] = Field(default=None, alias="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, alias="SMTP_PORT")
    SMTP_USERNAME: Optional[str] = Field(default=None, alias="SMTP_USERNAME")
    SMTP_PASSWORD: Optional[str] = Field(default=None, alias="SMTP_PASSWORD")
    SMTP_TLS: bool = Field(default=True, alias="SMTP_TLS")
    EMAIL_FROM: str = Field(default="noreply@baze.edu.ng", alias="SMTP_FROM")

    # Scheduling engine settings
    SCHEDULING_TIMEOUT_SECONDS: int = Field(
        default=900, alias="SCHEDULING_TIMEOUT"
    )  # 15 minutes
    CPSAT_TIME_LIMIT_SECONDS: int = Field(
        default=300, alias="CPSAT_TIME_LIMIT"
    )  # 5 minutes
    GA_TIME_LIMIT_SECONDS: int = Field(default=600, alias="GA_TIME_LIMIT")  # 10 minutes
    GA_POPULATION_SIZE: int = Field(default=50, alias="GA_POPULATION_SIZE")
    GA_GENERATIONS: int = Field(default=100, alias="GA_GENERATIONS")
    GA_MUTATION_RATE: float = Field(default=0.1, alias="GA_MUTATION_RATE")
    GA_CROSSOVER_RATE: float = Field(default=0.8, alias="GA_CROSSOVER_RATE")

    # Celery settings
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: List[str] = ["json"]
    CELERY_TIMEZONE: str = "UTC"
    CELERY_ENABLE_UTC: bool = True

    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", alias="LOG_LEVEL")
    LOG_FILE: Optional[str] = Field(default=None, alias="LOG_FILE")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # WebSocket settings
    WEBSOCKET_MAX_CONNECTIONS: int = Field(default=100, alias="WS_MAX_CONNECTIONS")
    WEBSOCKET_HEARTBEAT_INTERVAL: int = Field(default=30, alias="WS_HEARTBEAT_INTERVAL")

    # Monitoring settings
    METRICS_ENABLED: bool = Field(default=True, alias="METRICS_ENABLED")
    HEALTH_CHECK_INTERVAL: int = Field(default=60, alias="HEALTH_CHECK_INTERVAL")

    # University-specific settings
    UNIVERSITY_NAME: str = Field(default="Baze University", alias="UNIVERSITY_NAME")
    UNIVERSITY_CODE: str = Field(default="BU", alias="UNIVERSITY_CODE")
    ACADEMIC_YEAR_START_MONTH: int = Field(
        default=9, alias="ACADEMIC_YEAR_START_MONTH"
    )  # September
    DEFAULT_EXAM_DURATION: int = Field(
        default=180, alias="DEFAULT_EXAM_DURATION"
    )  # 3 hours

    # Validators
    @field_validator("CELERY_BROKER_URL")
    def set_celery_broker_url(
        cls, v: Optional[str], info: ValidationInfo
    ) -> Optional[str]:
        """Build a Redis-based broker URL if not provided."""
        if v is None:
            redis_url = info.data.get("REDIS_URL") or "redis://localhost:6379/0"
            # ensure base redis url without trailing db
            base = redis_url.rsplit("/", 1)[0]
            redis_db = info.data.get("REDIS_CELERY_DB", 1)
            return f"{base}/{redis_db}"
        return v

    @field_validator("CELERY_RESULT_BACKEND")
    def set_celery_result_backend(
        cls, v: Optional[str], info: ValidationInfo
    ) -> Optional[str]:
        """Build a Redis-based result backend if not provided."""
        if v is None:
            redis_url = info.data.get("REDIS_URL") or "redis://localhost:6379/0"
            base = redis_url.rsplit("/", 1)[0]
            redis_db = info.data.get("REDIS_CELERY_DB", 1)
            return f"{base}/{redis_db}"
        return v

    @field_validator("UPLOAD_DIR", "BACKUP_DIR")
    def create_directories(cls, v: str) -> str:
        """Ensure directories exist."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @field_validator(
        "CORS_ORIGINS", "ALLOWED_HOSTS", "ALLOWED_EXTENSIONS", mode="before"
    )
    def parse_comma_separated(cls, v):
        """Parse comma-separated strings into lists when values come from environment."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @property
    def database_config(self) -> Dict[str, Any]:
        """Get database configuration for SQLAlchemy."""
        return {
            "pool_size": self.DATABASE_POOL_SIZE,
            "max_overflow": self.DATABASE_MAX_OVERFLOW,
            "pool_timeout": self.DATABASE_POOL_TIMEOUT,
            "pool_recycle": self.DATABASE_POOL_RECYCLE,
            "echo": self.DATABASE_ECHO,
            "schema": self.DATABASE_SCHEMA,
        }

    @property
    def is_production(self) -> bool:
        return (self.ENVIRONMENT or "").lower() == "production"


class DevelopmentSettings(Settings):
    """Development environment settings."""

    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"


class ProductionSettings(Settings):
    """Production environment settings."""

    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"


class TestingSettings(Settings):
    """Testing environment settings."""

    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/exam_system_test"


def get_settings_for_environment(environment: str) -> Settings:
    """Get settings for specific environment."""
    env_lower = (environment or "").lower()

    if env_lower == "production":
        return ProductionSettings()
    if env_lower in ("test", "testing"):
        return TestingSettings()
    return DevelopmentSettings()


def get_settings() -> Settings:
    """Convenience loader. Reads ENV or ENVIRONMENT from environment variables."""
    env = os.getenv("ENV") or os.getenv("ENVIRONMENT") or "development"
    return get_settings_for_environment(env)


# Configuration validation
def validate_settings(settings: Settings) -> List[str]:
    """Validate settings and return list of issues."""
    issues: List[str] = []

    # Database validation
    if not settings.DATABASE_URL:
        issues.append("DATABASE_URL is required")

    # Security validation
    if settings.is_production:
        if settings.SECRET_KEY == "your-secret-key-here-change-in-production":
            issues.append("SECRET_KEY must be changed in production")

        if settings.JWT_SECRET_KEY == "jwt-secret-key-change-in-production":
            issues.append("JWT_SECRET_KEY must be changed in production")

        if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32:
            issues.append("SECRET_KEY should be at least 32 characters long")

    # Email validation
    if settings.SMTP_HOST and not settings.SMTP_USERNAME:
        issues.append("SMTP_USERNAME is required when SMTP_HOST is set")

    # File upload validation
    if settings.MAX_UPLOAD_SIZE < 1024 * 1024:  # 1MB
        issues.append("MAX_UPLOAD_SIZE should be at least 1MB")

    # AWS validation
    if settings.BACKUP_S3_BUCKET:
        if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
            issues.append("AWS credentials required for S3 backup")

    return issues


# Logging configuration
def setup_logging(settings: Settings):
    """Setup logging configuration."""
    import logging
    import logging.handlers

    # Set log level
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Create formatters
    formatter = logging.Formatter(settings.LOG_FORMAT)

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if settings.LOG_FILE:
        log_file = Path(settings.LOG_FILE)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            str(log_file),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)


# Export main components
__all__ = [
    "Settings",
    "get_settings",
    "get_settings_for_environment",
    "validate_settings",
    "setup_logging",
    "DevelopmentSettings",
    "ProductionSettings",
    "TestingSettings",
]

# if __name__ == "__main__":
#     # Test configuration loading
#     settings = get_settings()

#     print("=" * 50)
#     print("Environment Variables from .env:")
#     print("=" * 50)

#     # Print all settings alphabetically
#     for field_name in sorted(settings.model_fields.keys()):
#         value = getattr(settings, field_name)
#         print(f"{field_name}: {value}")

#     print("=" * 50)

#     # Validate settings
#     issues = validate_settings(settings)
#     if issues:
#         print("Validation Issues:")
#         for issue in issues:
#             print(f"⚠️  {issue}")
#     else:
#         print("✅ All settings are valid!")

#     print("=" * 50)
