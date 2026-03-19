import logging
import os
from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
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

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)

app.include_router(auth.router)
app.include_router(api.router)
app.include_router(health.router)


@app.get("/")
async def root():
    return RedirectResponse("/login")


@app.get("/.well-known/jwks.json")
async def jwks():
    return jwt_handler.get_jwks()


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    redirect_url = request.query_params.get("redirect_url", "")
    error = request.query_params.get("error", "")
    authenticated = request.query_params.get("authenticated", "")

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

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "app_name": settings.APP_NAME,
            "app_logo_url": settings.APP_LOGO_URL,
            "app_tagline": settings.APP_TAGLINE,
            "accent_color": settings.ACCENT_COLOR,
            "providers": provider_list,
            "error": error,
            "authenticated": authenticated,
        },
    )


@app.post("/logout")
async def logout():
    from fastapi.responses import JSONResponse

    response = JSONResponse({"status": "logged_out"})
    response.delete_cookie(
        settings.COOKIE_NAME, domain=settings.COOKIE_DOMAIN or None
    )
    return response
