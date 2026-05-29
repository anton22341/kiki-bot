"""Московское время для всего проекта."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta

MSK = timezone(timedelta(hours=3))


def now_msk() -> datetime:
    """Текущее время Москва (naive datetime, без tzinfo)."""
    return datetime.now(MSK).replace(tzinfo=None)


def to_msk(dt: datetime) -> datetime:
    """Конвертирует UTC datetime в московское (naive)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(MSK).replace(tzinfo=None)
