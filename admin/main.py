import logging
import math
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_, select

from admin.auth import (
    EXPIRY_HOURS,
    SESSION_COOKIE,
    NotAuthenticated,
    check_credentials,
    create_session_token,
    require_admin,
)
from admin.database import async_session, engine
from admin.models import User, UserProvider

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("authgate.admin")

PAGE_SIZE = 20
_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AuthGate Admin")
    yield
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(title="AuthGate Admin", docs_url=None, redoc_url=None, lifespan=lifespan)

_templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=_templates_dir)


def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%b %d, %Y")


templates.env.filters["fmtdt"] = _fmt_dt


@app.exception_handler(NotAuthenticated)
async def _not_authenticated(
    request: Request, exc: NotAuthenticated
) -> RedirectResponse:
    return RedirectResponse("/login", status_code=302)


# ── Health ────────────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Root ──────────────────────────────────────────────────────────────────────


@app.get("/")
async def root():
    return RedirectResponse("/dashboard")


# ── Auth ──────────────────────────────────────────────────────────────────────


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    return templates.TemplateResponse(request, "login.html", {"error": error})


@app.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(default=""),
    password: str = Form(default=""),
):
    if not check_credentials(username, password):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Invalid username or password."},
            status_code=401,
        )
    token = create_session_token()
    resp = RedirectResponse("/dashboard", status_code=302)
    resp.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite="lax",
        max_age=EXPIRY_HOURS * 3600,
    )
    return resp


@app.get("/logout")
async def logout():
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie(SESSION_COOKIE)
    return resp


# ── Dashboard ─────────────────────────────────────────────────────────────────


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, _: bool = Depends(require_admin)):
    async with async_session() as db:
        total = (await db.execute(select(func.count()).select_from(User))).scalar_one()
        active = (
            await db.execute(
                select(func.count())
                .select_from(User)
                .where(User.is_active == True)  # noqa: E712
            )
        ).scalar_one()
        provider_rows = (
            await db.execute(
                select(UserProvider.provider, func.count().label("n")).group_by(
                    UserProvider.provider
                )
            )
        ).all()
        since = datetime.now(timezone.utc) - timedelta(days=7)
        recent = (
            await db.execute(
                select(func.count()).select_from(User).where(User.created_at >= since)
            )
        ).scalar_one()

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "active_page": "dashboard",
            "total": total,
            "active": active,
            "disabled": total - active,
            "providers": {row.provider: row.n for row in provider_rows},
            "recent": recent,
        },
    )


# ── Users ─────────────────────────────────────────────────────────────────────


@app.get("/users", response_class=HTMLResponse)
async def users_list(
    request: Request,
    page: int = 1,
    q: str = "",
    provider: str = "",
    status: str = "",
    _: bool = Depends(require_admin),
):
    page = max(1, page)
    offset = (page - 1) * PAGE_SIZE

    async with async_session() as db:
        base = select(User)

        if q:
            base = base.where(
                or_(User.email.ilike(f"%{q}%"), User.name.ilike(f"%{q}%"))
            )
        if provider:
            base = base.where(User.providers.any(UserProvider.provider == provider))
        if status == "active":
            base = base.where(User.is_active == True)  # noqa: E712
        elif status == "disabled":
            base = base.where(User.is_active == False)  # noqa: E712

        total = (
            await db.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        rows = (
            (
                await db.execute(
                    base.order_by(User.created_at.desc())
                    .offset(offset)
                    .limit(PAGE_SIZE)
                )
            )
            .scalars()
            .all()
        )

    return templates.TemplateResponse(
        request,
        "users.html",
        {
            "active_page": "users",
            "users": rows,
            "total": total,
            "page": page,
            "total_pages": max(1, math.ceil(total / PAGE_SIZE)),
            "q": q,
            "provider_filter": provider,
            "status_filter": status,
        },
    )


@app.post("/users/{user_id}/toggle")
async def toggle_user(
    user_id: str,
    redirect_to: str = Form(default="/users"),
    _: bool = Depends(require_admin),
):
    async with async_session() as db:
        user = await db.get(User, user_id)
        if user:
            user.is_active = not user.is_active
            await db.commit()
    target = redirect_to if redirect_to.startswith("/") else "/users"
    return RedirectResponse(target, status_code=302)


@app.post("/users/{user_id}/delete")
async def delete_user(
    user_id: str,
    _: bool = Depends(require_admin),
):
    async with async_session() as db:
        user = await db.get(User, user_id)
        if user:
            await db.delete(user)
            await db.commit()
    return RedirectResponse("/users", status_code=302)
