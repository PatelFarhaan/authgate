"""
Test fixtures for AuthGate E2E tests.

AUTHGATE_CONFIG, DATABASE_URL, and AUTHGATE_TEST must be set before any
app.* imports because app/database.py initialises the engine at import time.
With AUTHGATE_TEST=1, app/database.py uses NullPool so asyncpg connections
are never held across per-test event loops.
"""

import os

os.environ.setdefault("AUTHGATE_CONFIG", "tests/authgate.test.yaml")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://authgate:authgate@localhost:5432/authgate_test",
)
os.environ.setdefault("AUTHGATE_TEST", "1")

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.database import Base, async_session  # noqa: E402
from app.database import engine as db_engine  # noqa: E402
from app.jwt_handler import jwt_handler  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402, F401 — registers models with Base.metadata
    User,
    UserProvider,
)

# ---------------------------------------------------------------------------
# HTTP client — function-scoped, one event loop per test.
#
# httpx.ASGITransport does NOT send ASGI lifespan events, so the app's
# lifespan startup (create_all, jwt_handler.initialize) never runs
# automatically.  We replicate startup here before yielding the client.
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client():
    # Replicate lifespan startup: create tables and initialise JWT keys.
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    if jwt_handler.private_key is None:
        jwt_handler.initialize()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as c:
        yield c
        async with db_engine.begin() as conn:
            await conn.execute(text("DELETE FROM user_providers"))
            await conn.execute(text("DELETE FROM users"))


# ---------------------------------------------------------------------------
# Raw DB session — depends on `client` so create_all has already run.
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db(client):
    async with async_session() as session:
        yield session


# ---------------------------------------------------------------------------
# Stock test users
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def active_user(db):
    user = User(
        email="alice@example.com",
        name="Alice Example",
        avatar_url="https://avatars.githubusercontent.com/u/1001",
    )
    db.add(user)
    await db.flush()
    db.add(UserProvider(user_id=user.id, provider="github", provider_id="gh-1001"))
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def inactive_user(db):
    user = User(
        email="bob@example.com",
        name="Bob Example",
        avatar_url="",
        is_active=False,
    )
    db.add(user)
    await db.flush()
    db.add(UserProvider(user_id=user.id, provider="github", provider_id="gh-2001"))
    await db.commit()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def active_user_token(active_user):
    return jwt_handler.create_token(
        active_user.id, active_user.email, active_user.name, "github"
    )


@pytest_asyncio.fixture
async def inactive_user_token(inactive_user):
    return jwt_handler.create_token(
        inactive_user.id, inactive_user.email, inactive_user.name, "github"
    )
