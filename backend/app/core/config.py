# app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    # Database and auth
    DATABASE_URL: str = Field(default="postgresql://user:pass@localhost/dbname")
    JWT_SECRET_KEY: str = Field(default="mysecret")
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)
    BCRYPT_SALT_ROUNDS: int = Field(default=12)

    # SMTP / email
    SMTP_USER: Optional[str] = Field(default=None)
    SMTP_PASSWORD: Optional[str] = Field(default=None)
    SMTP_FROM: Optional[str] = Field(default=None)
    SMTP_PORT: int = Field(default=587)
    SMTP_SERVER: str = Field(default="localhost")
    SMTP_STARTTLS: bool = Field(default=True)
    SMTP_SSL_TLS: bool = Field(default=False)
    MAIL_TEMPLATE_FOLDER: str = Field(default=str(Path(__file__).parent.parent / "services" / "notification" / "templates"))

    #Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")


    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# module-level singleton for convenient import elsewhere
settings = Settings()
