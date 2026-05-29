from __future__ import annotations
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id          = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username    = Column(String(100))
    full_name   = Column(String(200))
    role        = Column(String(12), nullable=False)
    added_by    = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    role_set_at = Column(DateTime, default=datetime.utcnow)


class ClubNight(Base):
    __tablename__ = "club_nights"
    id           = Column(Integer, primary_key=True)
    date         = Column(String(10), nullable=False, unique=True)
    day_of_week  = Column(String(3), nullable=False)
    opened_at    = Column(DateTime)
    closed_at    = Column(DateTime)
    hourly_stats = relationship("HourlyStat", back_populates="night", order_by="HourlyStat.recorded_at")


class HourlyStat(Base):
    __tablename__ = "hourly_stats"
    id             = Column(Integer, primary_key=True)
    night_id       = Column(Integer, ForeignKey("club_nights.id"), nullable=False, index=True)
    recorded_at    = Column(DateTime, nullable=False)
    is_manual_time = Column(Boolean, default=False)
    girls_entered  = Column(Integer, default=0)
    boys_entered   = Column(Integer, default=0)
    denied         = Column(Integer, default=0)
    left_count     = Column(Integer, default=0)  # итого ушло (girls_left + boys_left)
    girls_left     = Column(Integer, default=0)  # ушло девушек
    boys_left      = Column(Integer, default=0)  # ушло парней
    created_by     = Column(Integer, ForeignKey("users.id"))
    created_at     = Column(DateTime, default=datetime.utcnow)
    night          = relationship("ClubNight", back_populates="hourly_stats")
    edit_logs      = relationship("EditLog", back_populates="stat")


class EditLog(Base):
    __tablename__ = "edit_logs"
    id          = Column(Integer, primary_key=True)
    stat_id     = Column(Integer, ForeignKey("hourly_stats.id"), nullable=False)
    field_name  = Column(String(50), nullable=False)
    old_value   = Column(Text)
    new_value   = Column(Text)
    edited_by   = Column(Integer, ForeignKey("users.id"))
    edited_at   = Column(DateTime, default=datetime.utcnow)
    stat        = relationship("HourlyStat", back_populates="edit_logs")


class ClubSettings(Base):
    """Настройки клуба: цели, вместимость."""
    __tablename__ = "club_settings"
    id         = Column(Integer, primary_key=True)
    key        = Column(String(50), unique=True, nullable=False)
    value      = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)


# ─── Engine / Session ────────────────────────────────────
_engine = None
_factory = None


def _make_engine():
    from config import settings
    # Railway PostgreSQL имеет приоритет если установлен
    raw = settings.DATABASE_URL or settings.DB_URL

    if "postgresql" not in raw:
        return create_async_engine(raw, echo=False)

    # Конвертируем postgresql:// → postgresql+asyncpg://
    url = raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)

    import ssl as _ssl
    ssl_ctx = _ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = _ssl.CERT_NONE

    return create_async_engine(
        url,
        connect_args={"ssl": ssl_ctx, "statement_cache_size": 0},
        pool_size=5,
        max_overflow=10,
        echo=False,
    )


def _get_factory() -> async_sessionmaker:
    global _engine, _factory
    if _factory is None:
        _engine = _make_engine()
        _factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _factory


class _SessionCM:
    """AsyncSessionLocal() возвращает async context manager для сессии."""
    def __call__(self):
        return _get_factory()()


AsyncSessionLocal = _SessionCM()


async def init_db() -> None:
    from config import settings
    factory = _get_factory()
    engine = _engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from sqlalchemy import select
    # Superadmin
    async with factory() as session:
        res = await session.execute(select(User).where(User.telegram_id == settings.SUPERADMIN_ID))
        if not res.scalar_one_or_none():
            session.add(User(telegram_id=settings.SUPERADMIN_ID, role="superadmin", full_name="Superadmin"))
            await session.commit()
            logger.info("Superadmin created: %s", settings.SUPERADMIN_ID)

    # Дефолтные настройки клуба
    defaults = [
        ("max_capacity",    "200"),
        ("target_girls_pct","55"),
        ("target_fc_pct",   "90"),
        ("club_name",       "KIKI"),
    ]
    async with factory() as session:
        for key, val in defaults:
            res = await session.execute(select(ClubSettings).where(ClubSettings.key == key))
            if not res.scalar_one_or_none():
                session.add(ClubSettings(key=key, value=val))
        await session.commit()
