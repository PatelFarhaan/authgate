import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Cookie

ADMIN_USERNAME: str = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD: str = os.environ.get("ADMIN_PASSWORD", "")
_SECRET: str = os.environ.get("ADMIN_SECRET_KEY") or os.environ.get("SECRET_KEY") or ""
if not _SECRET:
    raise RuntimeError(
        "ADMIN_SECRET_KEY (or SECRET_KEY) must be set before starting the admin panel"
    )
if len(_SECRET) < 64:
    raise RuntimeError(
        "ADMIN_SECRET_KEY is too short (minimum 64 characters). "
        "Generate one with: openssl rand -hex 32"
    )
SESSION_COOKIE: str = "admin_session"
EXPIRY_HOURS: int = 8
_ALGO: str = "HS256"


class NotAuthenticated(Exception):
    pass


def create_session_token() -> str:
    payload = {
        "adm": True,
        "exp": datetime.now(timezone.utc) + timedelta(hours=EXPIRY_HOURS),
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGO)


def verify_session_token(token: str) -> bool:
    try:
        claims = jwt.decode(token, _SECRET, algorithms=[_ALGO])
        return bool(claims.get("adm"))
    except jwt.PyJWTError:
        return False


def check_credentials(username: str, password: str) -> bool:
    if not ADMIN_PASSWORD:
        return False
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD


async def require_admin(
    admin_session: str | None = Cookie(default=None),
) -> bool:
    if not admin_session or not verify_session_token(admin_session):
        raise NotAuthenticated()
    return True
