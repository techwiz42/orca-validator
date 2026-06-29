"""Async SQLAlchemy engine + session factory.

Pool config carries forward agent_framework's hard-won lessons (see
docs/design/AUTH_LOGIN_SESSION_RACE.md in that repo): pool_pre_ping recovers
server-dropped connections; pool_timeout fails fast on exhaustion rather than
stalling (an unbounded checkout wait is itself part of what widens session races).
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.app.config import get_settings

settings = get_settings()


def _asyncpg_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


engine = create_async_engine(
    _asyncpg_url(settings.DATABASE_URL),
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
