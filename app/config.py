"""
AuthGate configuration loader.

Loads configuration from a YAML file (authgate.yaml or path set by AUTHGATE_CONFIG env var).
Supports $VAR syntax in string values to read from environment variables.
"""

import logging as _logging
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Environment-variable resolution for YAML values
# ---------------------------------------------------------------------------

_ENV_VAR_RE = re.compile(r"^\$([A-Za-z_][A-Za-z0-9_]*)$")


def _resolve_env_vars(value: Any) -> Any:
    """Replace `$VAR` strings with the corresponding environment variable."""
    if isinstance(value, str):
        m = _ENV_VAR_RE.match(value.strip())
        if m:
            return os.environ.get(m.group(1), "")
    return value


def _walk_and_resolve(obj: Any) -> Any:
    """Recursively walk a parsed YAML tree and resolve $VAR references."""
    if isinstance(obj, dict):
        return {k: _walk_and_resolve(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_walk_and_resolve(item) for item in obj]
    return _resolve_env_vars(obj)


# ---------------------------------------------------------------------------
# Settings class
# ---------------------------------------------------------------------------


class Settings:
    """Flat settings object consumed by the rest of the codebase."""

    # -- app --
    APP_NAME: str = "AuthGate"
    APP_LOGO_URL: str = ""
    APP_LOGO_PATH: str = ""
    APP_TAGLINE: str = "Secure authentication for your apps"
    ACCENT_COLOR: str = "#0060F0"
    DEFAULT_THEME: str = "light"
    CUSTOM_LOGIN_TEMPLATE: str = ""

    # -- server --
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    BASE_URL: str = ""
    SECRET_KEY: str = "change-me-in-production"
    ALLOWED_REDIRECTS: str = ""
    CORS_ORIGINS: str = ""

    # -- database --
    DATABASE_URL: str = ""

    # -- jwt --
    JWT_EXPIRY_HOURS: int = 24
    JWT_KEYS_DIR: str = "./keys"
    COOKIE_NAME: str = "authgate_token"
    COOKIE_DOMAIN: str = ""
    COOKIE_SECURE: bool = False

    # -- providers (derived from connectors) --
    ENABLED_PROVIDERS: str = ""

    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_REDIRECT_PATH: str = ""

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_PATH: str = ""

    GITLAB_CLIENT_ID: str = ""
    GITLAB_CLIENT_SECRET: str = ""
    GITLAB_REDIRECT_PATH: str = ""
    GITLAB_BASE_URL: str = "https://gitlab.com"

    # -- raw connector list --
    connectors: list = []

    def __init__(self, **overrides: Any):
        for key, value in overrides.items():
            setattr(self, key, value)


# ---------------------------------------------------------------------------
# YAML -> flat Settings mapping
# ---------------------------------------------------------------------------


def _settings_from_yaml(cfg: dict) -> Settings:
    """Map the nested YAML structure to flat Settings attributes."""
    kw: dict[str, Any] = {}

    # -- app --
    app = cfg.get("app", {})
    kw["APP_NAME"] = app.get("name", Settings.APP_NAME)
    kw["APP_LOGO_URL"] = app.get("logoUrl", Settings.APP_LOGO_URL)
    kw["APP_LOGO_PATH"] = app.get("logoPath", Settings.APP_LOGO_PATH)
    kw["APP_TAGLINE"] = app.get("tagline", Settings.APP_TAGLINE)
    kw["ACCENT_COLOR"] = app.get("accentColor", Settings.ACCENT_COLOR)
    kw["DEFAULT_THEME"] = app.get("defaultTheme", Settings.DEFAULT_THEME)
    kw["CUSTOM_LOGIN_TEMPLATE"] = app.get(
        "customLoginTemplate", Settings.CUSTOM_LOGIN_TEMPLATE
    )

    # -- server --
    server = cfg.get("server", {})
    kw["HOST"] = server.get("host", Settings.HOST)
    kw["PORT"] = int(server.get("port", Settings.PORT))
    kw["BASE_URL"] = server.get("baseUrl", Settings.BASE_URL)
    kw["SECRET_KEY"] = server.get("secretKey", Settings.SECRET_KEY)

    allowed = server.get("allowedRedirects", [])
    kw["ALLOWED_REDIRECTS"] = (
        ",".join(allowed) if isinstance(allowed, list) else str(allowed)
    )

    cors = server.get("corsOrigins", [])
    kw["CORS_ORIGINS"] = ",".join(cors) if isinstance(cors, list) else str(cors)

    # -- database --
    db = cfg.get("database", {})
    kw["DATABASE_URL"] = db.get("url", Settings.DATABASE_URL)

    # -- jwt --
    jwt = cfg.get("jwt", {})
    kw["JWT_EXPIRY_HOURS"] = int(jwt.get("expiryHours", Settings.JWT_EXPIRY_HOURS))
    kw["JWT_KEYS_DIR"] = jwt.get("keysDir", Settings.JWT_KEYS_DIR)
    kw["COOKIE_NAME"] = jwt.get("cookieName", Settings.COOKIE_NAME)
    kw["COOKIE_DOMAIN"] = jwt.get("cookieDomain", Settings.COOKIE_DOMAIN)
    cookie_secure = jwt.get("cookieSecure", Settings.COOKIE_SECURE)
    kw["COOKIE_SECURE"] = (
        cookie_secure
        if isinstance(cookie_secure, bool)
        else str(cookie_secure).lower() == "true"
    )

    # -- connectors --
    connectors = cfg.get("connectors", [])
    kw["connectors"] = connectors
    provider_ids = []

    for conn in connectors:
        ctype = conn.get("type", "").lower()
        cconfig = conn.get("config", {})

        if ctype == "github":
            kw["GITHUB_CLIENT_ID"] = cconfig.get("clientID", "")
            kw["GITHUB_CLIENT_SECRET"] = cconfig.get("clientSecret", "")
            kw["GITHUB_REDIRECT_PATH"] = cconfig.get("redirectPath", "")
            if kw["GITHUB_CLIENT_ID"] and kw["GITHUB_CLIENT_SECRET"]:
                provider_ids.append("github")

        elif ctype == "google":
            kw["GOOGLE_CLIENT_ID"] = cconfig.get("clientID", "")
            kw["GOOGLE_CLIENT_SECRET"] = cconfig.get("clientSecret", "")
            kw["GOOGLE_REDIRECT_PATH"] = cconfig.get("redirectPath", "")
            if kw["GOOGLE_CLIENT_ID"] and kw["GOOGLE_CLIENT_SECRET"]:
                provider_ids.append("google")

        elif ctype == "gitlab":
            kw["GITLAB_CLIENT_ID"] = cconfig.get("clientID", "")
            kw["GITLAB_CLIENT_SECRET"] = cconfig.get("clientSecret", "")
            kw["GITLAB_REDIRECT_PATH"] = cconfig.get("redirectPath", "")
            kw["GITLAB_BASE_URL"] = cconfig.get("baseUrl", Settings.GITLAB_BASE_URL)
            if kw["GITLAB_CLIENT_ID"] and kw["GITLAB_CLIENT_SECRET"]:
                provider_ids.append("gitlab")

    kw["ENABLED_PROVIDERS"] = ",".join(provider_ids)

    return Settings(**kw)


# ---------------------------------------------------------------------------
# Load configuration
# ---------------------------------------------------------------------------


def _load_settings() -> Settings:
    config_path = os.environ.get("AUTHGATE_CONFIG", "authgate.yaml")

    if not Path(config_path).is_file():
        raise FileNotFoundError(
            f"Config file not found: {config_path}. "
            "Create an authgate.yaml or set AUTHGATE_CONFIG to the correct path."
        )

    with open(config_path, "r") as f:
        raw = yaml.safe_load(f) or {}

    resolved = _walk_and_resolve(raw)
    return _settings_from_yaml(resolved)


try:
    settings = _load_settings()
except FileNotFoundError as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)


_reload_logger = _logging.getLogger("authgate.config")

# Hot reload is enabled by default so local dev works out of the box.
# Set AUTHGATE_HOT_RELOAD=0 in production to skip per-request file reads
# and rely on restart-on-deploy instead.
_HOT_RELOAD: bool = os.environ.get("AUTHGATE_HOT_RELOAD", "1").lower() not in (
    "0",
    "false",
)

_reload_cache: Settings | None = None
_reload_snapshot: bytes = b""


def reload_settings() -> Settings:
    """Return settings, optionally re-parsing the config file on change.

    When AUTHGATE_HOT_RELOAD=0 (production): returns the startup-time
    settings singleton immediately — zero overhead, config is stable.

    When AUTHGATE_HOT_RELOAD=1 (default / dev): reads the raw file bytes on
    every call.  The OS page cache keeps tiny files in memory so this costs
    microseconds, not disk I/O.  YAML is only re-parsed when the bytes
    differ from the last snapshot.  Falls back to the startup-time singleton
    on any error.
    """
    if not _HOT_RELOAD:
        return settings

    global _reload_cache, _reload_snapshot

    config_path = os.environ.get("AUTHGATE_CONFIG", "authgate.yaml")
    try:
        raw = Path(config_path).read_bytes()
    except OSError:
        return _reload_cache if _reload_cache is not None else settings

    if _reload_cache is None or raw != _reload_snapshot:
        try:
            _reload_cache = _load_settings()
            _reload_snapshot = raw
            _reload_logger.info("Config reloaded from %s", config_path)
        except Exception as exc:
            _reload_logger.warning(
                "Config reload failed (%s) — continuing with previous settings", exc
            )

    return _reload_cache if _reload_cache is not None else settings
