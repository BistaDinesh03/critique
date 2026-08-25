import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    APP_NAME: str = "Critique"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_URL: str = os.getenv("APP_URL", "http://127.0.0.1:8000")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./critique.db")

    # GitHub OAuth
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    GITHUB_REDIRECT_URI: str = os.getenv("GITHUB_REDIRECT_URI", "http://127.0.0.1:8000/auth/callback")


settings = Settings()
