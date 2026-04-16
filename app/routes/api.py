from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.jwt_handler import jwt_handler
from app.models import User
from app.schemas import TokenVerifyResponse, UserInfo

router = APIRouter(prefix="/api")


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get(settings.COOKIE_NAME)


@router.get("/verify", response_model=TokenVerifyResponse)
async def verify(request: Request):
    token = _extract_token(request)
    if not token:
        return TokenVerifyResponse(valid=False)

    claims = jwt_handler.verify_token(token)
    if not claims:
        return TokenVerifyResponse(valid=False)

    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == claims["sub"]))
        user = result.scalar_one_or_none()

    if not user or not user.is_active:
        return TokenVerifyResponse(valid=False)

    return TokenVerifyResponse(
        valid=True,
        user=UserInfo(
            id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            providers=[
                p.provider
                for p in sorted(user.providers, key=lambda p: p.linked_at, reverse=True)
            ],
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        ),
    )


@router.get("/userinfo", response_model=UserInfo)
async def userinfo(request: Request):
    token = _extract_token(request)
    if not token:
        raise HTTPException(401, "Not authenticated")

    claims = jwt_handler.verify_token(token)
    if not claims:
        raise HTTPException(401, "Invalid token")

    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == claims["sub"]))
        user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(401, "User not found")

    return UserInfo(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        providers=[
            p.provider
            for p in sorted(user.providers, key=lambda p: p.linked_at, reverse=True)
        ],
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )
