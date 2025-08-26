from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    DATABASE_URL: str = Field(default="postgresql://user:pass@localhost/dbname")
    JWT_SECRET_KEY: str = Field(default="mysecret")
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)
    BCRYPT_SALT_ROUNDS: int = Field(default=12)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
