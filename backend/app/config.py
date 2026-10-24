import os
import secrets
import sys

from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


def _resolve_secret_key(app_env: str) -> str:
    """Return the session/OAuth signing key, never an empty one.

    An empty SECRET_KEY would let anyone forge session and OAuth-state
    tokens (itsdangerous happily signs with an empty HMAC key). In production
    we refuse to start rather than sign with a guessable key. Outside
    production we fall back to a random per-process key so local runs still
    work, with a warning that sessions will not survive a restart.
    """
    key = os.getenv("SECRET_KEY", "")
    if key:
        return key
    if app_env.lower() == "production":
        raise RuntimeError(
            "SECRET_KEY is not set. Refusing to start with an empty signing key: "
            "set SECRET_KEY in the environment (see .env.example)."
        )
    print(
        "WARNING: SECRET_KEY is not set; using a random per-process signing key. "
        "Sessions and OAuth state will not survive a restart. Set SECRET_KEY in .env.",
        file=sys.stderr,
    )
    return secrets.token_urlsafe(32)



class Settings:
    """Application settings loaded from environment variables."""

    APP_NAME: str = "Critique"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_URL: str = os.getenv("APP_URL", "http://127.0.0.1:8000")
    SECRET_KEY: str = _resolve_secret_key(os.getenv("APP_ENV", "development"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./critique.db")

    # GitHub OAuth
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    GITHUB_REDIRECT_URI: str = os.getenv("GITHUB_REDIRECT_URI", "http://127.0.0.1:8000/auth/callback")

    # Security
    SESSION_COOKIE_SECURE: bool = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_COOKIE_MAX_AGE: int = int(os.getenv("SESSION_COOKIE_MAX_AGE", "604800"))  # 7 days

    # Email (Resend) — passwordless magic link
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "")

    @property
    def is_production(self) -> bool:
        """Whether the app is running in production mode."""
        return self.APP_ENV.lower() == "production"


settings = Settings()
