# backend/app/core/config.py
from pathlib import Path
from typing import Optional, List
import pprint

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database and auth
    DATABASE_URL: str = Field(
        default="postgresql://user:pass@localhost/dbname",
        validation_alias="DATABASE_URL",
    )
    JWT_SECRET_KEY: str = Field(default="mysecret", validation_alias="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60, validation_alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    BCRYPT_SALT_ROUNDS: int = Field(default=12, validation_alias="BCRYPT_SALT_ROUNDS")

    # SMTP / email
    SMTP_HOST: Optional[str] = Field(default=None, validation_alias="SMTP_HOST")
    SMTP_USER: Optional[str] = Field(default=None, validation_alias="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(default=None, validation_alias="SMTP_PASSWORD")
    SMTP_FROM: Optional[str] = Field(default=None, validation_alias="SMTP_FROM")
    SMTP_PORT: int = Field(default=587, validation_alias="SMTP_PORT")
    SMTP_SERVER: str = Field(default="localhost", validation_alias="SMTP_SERVER")
    SMTP_STARTTLS: bool = Field(default=True, validation_alias="SMTP_STARTTLS")
    SMTP_SSL_TLS: bool = Field(default=False, validation_alias="SMTP_SSL_TLS")
    MAIL_TEMPLATE_FOLDER: str = Field(
        default=str(
            Path(__file__).parent.parent / "services" / "notification" / "templates"
        ),
        validation_alias="MAIL_TEMPLATE_FOLDER",
    )

    # Redis + Celery
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0", validation_alias="REDIS_URL"
    )

    # Celery broker (RabbitMQ) and backend (Redis)
    CELERY_BROKER_URL: str = Field(
        default="amqp://guest:guest@localhost:5672//",
        validation_alias="CELERY_BROKER_URL",
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/1", validation_alias="CELERY_RESULT_BACKEND"
    )

    # Security
    SECRET_KEY: str = Field(
        default="your-super-secret-key-change-this-in-production",
        validation_alias="SECRET_KEY",
    )

    # Environment
    ENV: str = Field(default="development", validation_alias="ENV")
    DEBUG: bool = Field(default=False, validation_alias="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:5173",
        ],
        validation_alias="CORS_ORIGINS",
    )

    # File uploads
    UPLOAD_DIR: str = Field(default="./uploads", validation_alias="UPLOAD_DIR")
    MAX_UPLOAD_SIZE: int = Field(default=10485760, validation_alias="MAX_UPLOAD_SIZE")
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=[".csv", ".xlsx", ".xls"],
        validation_alias="ALLOWED_EXTENSIONS",
    )

    @field_validator("CORS_ORIGINS", "ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def parse_json_strings(cls, v):
        if isinstance(v, str):
            try:
                # Try to parse as JSON
                return json.loads(v)
            except json.JSONDecodeError:
                # Fallback to comma-separated string
                return [item.strip() for item in v.split(",") if item.strip()]
        return v


# module-level singleton
settings = Settings()


# Run tests directly from this file
if __name__ == "__main__":
    output_file = Path(__file__).parent / "config_test_results.txt"
    data = settings.model_dump()

    # Pretty-print env values
    with output_file.open("w", encoding="utf-8") as f:
        f.write("Loaded Settings from .env\n")
        f.write("=" * 40 + "\n")
        f.write(pprint.pformat(data, indent=2))
        f.write("\n\nDerived values:\n")
        f.write(f"CORS origins: {settings.CORS_ORIGINS}\n")
        f.write(f"Allowed extensions: {settings.ALLOWED_EXTENSIONS}\n")

    print(f"Config test results written to {output_file}")
