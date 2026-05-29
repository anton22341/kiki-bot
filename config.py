from __future__ import annotations
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN:     str
    SUPERADMIN_ID: int
    WEBAPP_URL:    str = ""
    DB_URL:        str = "sqlite+aiosqlite:///./kiki.db"
    DATABASE_URL:  str = ""  # Railway PostgreSQL auto-injected

    class Config:
        env_file = ".env"


settings = Settings()
