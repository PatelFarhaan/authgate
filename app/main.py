import logging
import os
from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.database import Base, engine
from app.jwt_handler import jwt_handler
from app.oauth import PROVIDER_DISPLAY, get_enabled_providers, init_providers
from app.routes import api, auth, health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("authgate")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")
    jwt_handler.initialize()
    logger.info("JWT keys loaded")
    init_providers()
    yield
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    docs_url="/docs" if os.getenv("AUTHGATE_DEBUG") else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_builtin_templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=_builtin_templates_dir)

app.include_router(auth.router)
app.include_router(api.router)
app.include_router(health.router)

# Serve local logo file at /static/logo if APP_LOGO_PATH is configured
_logo_path = settings.APP_LOGO_PATH
if _logo_path and os.path.isfile(_logo_path):
    import mimetypes

    _logo_media_type = mimetypes.guess_type(_logo_path)[0] or "image/png"

    @app.get("/static/logo")
    async def serve_logo():
        return FileResponse(_logo_path, media_type=_logo_media_type)


@app.get("/")
async def root():
    return RedirectResponse("/login")


@app.get("/.well-known/jwks.json")
async def jwks():
    return jwt_handler.get_jwks()


def _build_login_context(request: Request):
    redirect_url = request.query_params.get("redirect_url", "")
    error = request.query_params.get("error", "")
    authenticated = request.query_params.get("authenticated", "")
    theme_param = request.query_params.get("theme", "")
    if theme_param in ("light", "dark"):
        theme = theme_param
    elif settings.DEFAULT_THEME in ("light", "dark"):
        theme = settings.DEFAULT_THEME
    else:
        theme = ""  # "auto" — let the template handle it via prefers-color-scheme

    providers = get_enabled_providers()
    provider_list = [
        {
            **PROVIDER_DISPLAY.get(name, {}),
            "id": name,
            "url": (
                f"/auth/{name}?redirect_url={quote(redirect_url, safe='')}"
                if redirect_url
                else f"/auth/{name}"
            ),
        }
        for name in providers
    ]

    # Prefer local logo file served at /static/logo over external URL
    if settings.APP_LOGO_PATH and os.path.isfile(settings.APP_LOGO_PATH):
        logo_url = "/static/logo"
    else:
        logo_url = settings.APP_LOGO_URL

    return {
        "request": request,
        "app_name": settings.APP_NAME,
        "app_logo_url": logo_url,
        "app_tagline": settings.APP_TAGLINE,
        "accent_color": settings.ACCENT_COLOR,
        "providers": provider_list,
        "error": error,
        "authenticated": authenticated,
        "theme": theme if theme in ("light", "dark") else "",
    }


def _render_custom_template(request: Request, filename: str, context: dict):
    custom_dir = os.environ.get("CUSTOM_TEMPLATES_DIR", "")
    if not custom_dir:
        custom_path = settings.CUSTOM_LOGIN_TEMPLATE
        if custom_path:
            custom_dir = os.path.dirname(os.path.abspath(custom_path))
    if custom_dir and os.path.isfile(os.path.join(custom_dir, filename)):
        return Jinja2Templates(directory=custom_dir).TemplateResponse(
            request, filename, context
        )
    return None


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    ctx = _build_login_context(request)
    custom_path = settings.CUSTOM_LOGIN_TEMPLATE
    if custom_path and os.path.isfile(custom_path):
        custom_dir = os.path.dirname(os.path.abspath(custom_path))
        custom_name = os.path.basename(custom_path)
        return Jinja2Templates(directory=custom_dir).TemplateResponse(
            request, custom_name, ctx
        )
    return templates.TemplateResponse(request, "login.html", ctx)


@app.get("/login{design_num}", response_class=HTMLResponse)
async def login_variant(request: Request, design_num: int):
    ctx = _build_login_context(request)
    resp = _render_custom_template(request, f"v{design_num}.html", ctx)
    if resp:
        return resp
    return templates.TemplateResponse(request, "login.html", ctx)


@app.get("/logout")
async def logout(request: Request):
    redirect_url = request.query_params.get("redirect_url", "/login")
    response = RedirectResponse(redirect_url)
    response.delete_cookie(settings.COOKIE_NAME, domain=settings.COOKIE_DOMAIN or None)
    return response
