import fnmatch
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.jwt_handler import jwt_handler
from app.models import User
from app.oauth import get_enabled_providers

router = APIRouter()


def _get_base_url(request: Request) -> str:
    if settings.BASE_URL:
        return settings.BASE_URL.rstrip("/")
    return str(request.base_url).rstrip("/")


def _validate_redirect(url: str) -> bool:
    allowed = [p.strip() for p in settings.ALLOWED_REDIRECTS.split(",") if p.strip()]
    if not allowed:
        return False
    return any(fnmatch.fnmatch(url, pattern) for pattern in allowed)


@router.get("/auth/{provider}")
async def auth_start(provider: str, request: Request):
    providers = get_enabled_providers()
    if provider not in providers:
        return RedirectResponse("/login?error=invalid_provider")

    redirect_url = request.query_params.get("redirect_url", "")
    if redirect_url and not _validate_redirect(redirect_url):
        return RedirectResponse("/login?error=invalid_redirect")

    state = jwt_handler.create_state_token(redirect_url)
    callback_uri = _get_base_url(request) + f"/auth/{provider}/callback"
    authorize_url = providers[provider].get_authorize_url(state, callback_uri)

    return RedirectResponse(authorize_url)


@router.get("/auth/{provider}/callback")
async def auth_callback(provider: str, request: Request):
    providers = get_enabled_providers()
    if provider not in providers:
        return RedirectResponse("/login?error=invalid_provider")

    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    if error:
        return RedirectResponse(f"/login?error={error}")
    if not code or not state:
        return RedirectResponse("/login?error=missing_params")

    redirect_url = jwt_handler.verify_state_token(state)
    if redirect_url is None:
        return RedirectResponse("/login?error=invalid_state")

    callback_uri = _get_base_url(request) + f"/auth/{provider}/callback"

    try:
        access_token = await providers[provider].get_token(code, callback_uri)
        oauth_user = await providers[provider].get_user(access_token)
    except Exception:
        return RedirectResponse("/login?error=provider_error")

    if not oauth_user.email:
        return RedirectResponse("/login?error=no_email")

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.email == oauth_user.email)
        )
        user = result.scalar_one_or_none()

        if user:
            user.last_login_at = datetime.now(timezone.utc)
            user.name = oauth_user.name or user.name
            user.avatar_url = oauth_user.avatar_url or user.avatar_url
            user.provider = provider
            user.provider_id = oauth_user.id
        else:
            user = User(
                email=oauth_user.email,
                name=oauth_user.name,
                avatar_url=oauth_user.avatar_url,
                provider=provider,
                provider_id=oauth_user.id,
            )
            session.add(user)

        await session.commit()
        await session.refresh(user)

    token = jwt_handler.create_token(user.id, user.email, user.name, user.provider)

    if redirect_url:
        separator = "&" if "?" in redirect_url else "?"
        target = f"{redirect_url}{separator}token={token}"
    else:
        target = "/login?authenticated=true"

    resp = RedirectResponse(target, status_code=302)
    resp.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.JWT_EXPIRY_HOURS * 3600,
        domain=settings.COOKIE_DOMAIN or None,
    )
    return resp
