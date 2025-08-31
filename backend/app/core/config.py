# app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
from typing import Optional, List


class Settings(BaseSettings):
    # Database and auth
    DATABASE_URL: str = Field(default="postgresql://user:pass@localhost/dbname")
    JWT_SECRET_KEY: str = Field(default="mysecret")
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)
    BCRYPT_SALT_ROUNDS: int = Field(default=12)

    # SMTP / email - CONSISTENT NAMING
    SMTP_HOST: Optional[str] = Field(default=None)
    SMTP_USER: Optional[str] = Field(default=None)
    SMTP_PASSWORD: Optional[str] = Field(default=None)
    SMTP_FROM: Optional[str] = Field(default=None)
    SMTP_PORT: int = Field(default=587)
    SMTP_SERVER: str = Field(default="localhost")
    SMTP_STARTTLS: bool = Field(default=True)
    SMTP_SSL_TLS: bool = Field(default=False)
    MAIL_TEMPLATE_FOLDER: str = Field(
        default=str(
            Path(__file__).parent.parent / "services" / "notification" / "templates"
        )
    )

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Security (additional)
    SECRET_KEY: str = Field(default="your-super-secret-key-change-this-in-production")

    # Environment
    ENV: str = Field(default="development", alias="ENVIRONMENT")
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")

    # CORS
    CORS_ORIGINS: str = Field(default="http://localhost:3000,http://localhost:8000")

    # File uploads
    UPLOAD_DIR: str = Field(default="./uploads")
    MAX_UPLOAD_SIZE: int = Field(default=10485760)  # 10MB
    ALLOWED_EXTENSIONS: str = Field(default=".csv,.xlsx,.xls")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Allow extra fields from environment variables
        extra = "ignore"  # This will ignore extra fields instead of raising errors

    @property
    def cors_origins_list(self) -> List[str]:
        """Convert comma-separated CORS origins to list"""
        return [
            origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()
        ]

    @property
    def allowed_extensions_list(self) -> List[str]:
        """Convert comma-separated extensions to list"""
        return [
            ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",") if ext.strip()
        ]


# module-level singleton for convenient import elsewhere
settings = Settings()
