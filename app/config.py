from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AuthGate"
    APP_LOGO_URL: str = ""
    APP_TAGLINE: str = "Secure authentication for your apps"
    ACCENT_COLOR: str = "#6366f1"
    CUSTOM_LOGIN_TEMPLATE: str = ""

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    BASE_URL: str = ""
    GITHUB_REDIRECT_PATH: str = ""
    GOOGLE_REDIRECT_PATH: str = ""
    GITLAB_REDIRECT_PATH: str = ""
    SECRET_KEY: str = "change-me-in-production"
    ALLOWED_REDIRECTS: str = ""
    CORS_ORIGINS: str = ""

    DATABASE_URL: str = ""

    JWT_EXPIRY_HOURS: int = 24
    JWT_KEYS_DIR: str = "./keys"
    COOKIE_NAME: str = "authgate_token"
    COOKIE_DOMAIN: str = ""
    COOKIE_SECURE: bool = False

    # Comma-separated list of providers to enable: "github,google,gitlab"
    # Empty = auto-detect from available credentials (local dev convenience)
    ENABLED_PROVIDERS: str = ""

    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    GITLAB_CLIENT_ID: str = ""
    GITLAB_CLIENT_SECRET: str = ""
    GITLAB_BASE_URL: str = "https://gitlab.com"

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
