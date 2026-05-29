from __future__ import annotations
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN:     str
    SUPERADMIN_ID: int
    WEBAPP_URL:    str = ""
    DB_URL:        str = "sqlite+aiosqlite:///./kiki.db"

    class Config:
        env_file = ".env"


settings = Settings()
