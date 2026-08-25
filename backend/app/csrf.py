import secrets
import hmac
from fastapi import HTTPException, Request
from app.config import settings

CSRF_COOKIE_NAME = "critique_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"


def generate_csrf_token() -> str:
    """Generate a random CSRF token."""
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response, token: str):
    """Set the CSRF token as a cookie."""
    response.set_cookie(
        CSRF_COOKIE_NAME,
        token,
        httponly=False,  # Must be readable by JavaScript
        max_age=settings.SESSION_COOKIE_MAX_AGE,
        samesite="lax",
        secure=settings.SESSION_COOKIE_SECURE,
    )


def verify_csrf_token(request: Request) -> bool:
    """Verify that the CSRF token in header matches the cookie."""
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)

    if not cookie_token or not header_token:
        return False

    return hmac.compare_digest(cookie_token, header_token)


def require_csrf(request: Request):
    """Dependency that raises 403 if CSRF token is invalid."""
    if not verify_csrf_token(request):
        raise HTTPException(status_code=403, detail="Invalid or missing CSRF token")
