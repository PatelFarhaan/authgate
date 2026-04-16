import logging

from app.config import settings
from app.oauth.base import OAuthProvider
from app.oauth.github import GitHubOAuth
from app.oauth.gitlab import GitLabOAuth
from app.oauth.google import GoogleOAuth

logger = logging.getLogger("authgate")

_providers: dict[str, OAuthProvider] = {}
_initialized = False

PROVIDER_REGISTRY: dict[str, tuple[type[OAuthProvider], str, str]] = {
    "github": (GitHubOAuth, "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET"),
    "google": (GoogleOAuth, "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"),
    "gitlab": (GitLabOAuth, "GITLAB_CLIENT_ID", "GITLAB_CLIENT_SECRET"),
}

PROVIDER_DISPLAY = {
    "github": {"name": "GitHub", "color": "#333"},
    "google": {"name": "Google", "color": "#4285f4"},
    "gitlab": {"name": "GitLab", "color": "#fc6d26"},
}


def init_providers() -> None:
    global _initialized
    if _initialized:
        return

    explicit = [p.strip() for p in settings.ENABLED_PROVIDERS.split(",") if p.strip()]

    if explicit:
        _init_explicit(explicit)
    else:
        _init_autodetect()

    _initialized = True

    if _providers:
        names = ", ".join(_providers.keys())
        logger.info(f"Active providers: {names}")
    else:
        logger.warning(
            "No OAuth providers are active. "
            "The login page will show no sign-in options."
        )


def _init_explicit(requested: list[str]) -> None:
    for name in requested:
        if name not in PROVIDER_REGISTRY:
            logger.error(
                f"Provider '{name}' is not supported. "
                f"Available: {', '.join(PROVIDER_REGISTRY.keys())}"
            )
            continue

        cls, id_attr, secret_attr = PROVIDER_REGISTRY[name]
        client_id = getattr(settings, id_attr)
        client_secret = getattr(settings, secret_attr)

        if not client_id or not client_secret:
            logger.error(
                f"Provider '{name}' is enabled but missing credentials. "
                f"Set {id_attr} and {secret_attr} in your environment/secret."
            )
            continue

        _providers[name] = cls()
        logger.info(f"Provider '{name}' — configured")


def _init_autodetect() -> None:
    logger.info("ENABLED_PROVIDERS not set — auto-detecting from credentials")
    for name, (cls, id_attr, secret_attr) in PROVIDER_REGISTRY.items():
        client_id = getattr(settings, id_attr)
        client_secret = getattr(settings, secret_attr)
        if client_id and client_secret:
            _providers[name] = cls()
            logger.info(f"Provider '{name}' — auto-detected")


def get_enabled_providers() -> dict[str, OAuthProvider]:
    if not _initialized:
        init_providers()
    return _providers
