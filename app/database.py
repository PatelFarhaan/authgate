import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings

# Tests set AUTHGATE_TEST=1 to avoid asyncpg connections being held across
# per-test event loops.  NullPool creates and closes a connection on every
# request, so nothing survives when a test's event loop is torn down.
_pool_kw = (
    {"poolclass": NullPool}
    if os.environ.get("AUTHGATE_TEST")
    else {"pool_pre_ping": True}
)
engine = create_async_engine(settings.DATABASE_URL, echo=False, **_pool_kw)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session
