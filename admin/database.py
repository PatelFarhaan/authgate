import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

DATABASE_URL: str = os.environ.get("DATABASE_URL", "")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required")

# Tests set AUTHGATE_TEST=1 — NullPool prevents asyncpg connections being held
# across per-test event loops (same pattern as the main app).
_pool_kw = (
    {"poolclass": NullPool}
    if os.environ.get("AUTHGATE_TEST")
    else {"pool_pre_ping": True}
)
engine = create_async_engine(DATABASE_URL, echo=False, **_pool_kw)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass
