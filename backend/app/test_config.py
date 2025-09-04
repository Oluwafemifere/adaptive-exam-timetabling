# test_config.py
from .config import get_settings

settings = get_settings()
print("DATABASE_URL:", settings.DATABASE_URL)
