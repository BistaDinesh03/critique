import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import User
from app.csrf import generate_csrf_token, set_csrf_cookie
from app.rate_limit import rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])

serializer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="session")

SESSION_COOKIE_NAME = "critique_session"


def create_session_token(user_id: int) -> str:
    """Create a signed session token for a user."""
    return serializer.dumps({"user_id": user_id})


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Dependency that returns the currently authenticated user."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        data = serializer.loads(token, max_age=86400 * 7)
        user_id = data.get("user_id")
    except (BadSignature, SignatureExpired):
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def get_current_user_optional(request: Request, db: Session = Depends(get_db)):
    """Dependency that returns the current user if authenticated, else None."""
    try:
        return get_current_user(request, db)
    except HTTPException:
        return None


RETURN_TO_COOKIE_NAME = "critique_return_to"


def _is_safe_return_path(path: str) -> bool:
    """Return True if path is a safe same-origin relative path."""
    if not path:
        return False
    # Must start with "/" (relative to origin)
    if not path.startswith("/"):
        return False
    # Reject protocol-relative URLs ("//evil.com")
    if path.startswith("//"):
        return False
    # Reject backslash tricks ("/\evil.com")
    if path.startswith("/\\"):
        return False
    # Reject anything containing a scheme separator
    if "://" in path:
        return False
    # Cap length to prevent abuse
    if len(path) > 500:
        return False
    return True


@router.get("/login")
def github_login(
    request: Request,
    return_to: str = None,
    _: None = Depends(rate_limit("auth")),
):
    """Redirect to GitHub OAuth. Optionally stores a safe return path."""
    github_auth_url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
        "&scope=read:user"
    )
    response = RedirectResponse(github_auth_url)
    if return_to and _is_safe_return_path(return_to):
        response.set_cookie(
            RETURN_TO_COOKIE_NAME,
            return_to,
            max_age=600,  # 10 minutes
            httponly=True,
            samesite="lax",
            secure=settings.SESSION_COOKIE_SECURE,
        )
    return response


@router.get("/callback")
async def github_callback(
    code: str,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit("auth")),
):
    """Handle GitHub OAuth callback and create session."""
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="GitHub authentication failed")

        user_response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        github_user = user_response.json()

    user = db.query(User).filter(User.github_id == github_user["id"]).first()
    if not user:
        user = User(
            github_id=github_user["id"],
            username=github_user["login"],
            avatar_url=github_user.get("avatar_url"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    session_token = create_session_token(user.id)
    csrf_token = generate_csrf_token()

    # Determine redirect target from safe return_to cookie
    redirect_target = "/"
    return_to = request.cookies.get(RETURN_TO_COOKIE_NAME)
    if return_to and _is_safe_return_path(return_to):
        redirect_target = return_to

    response = RedirectResponse(redirect_target)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_token,
        httponly=True,
        max_age=settings.SESSION_COOKIE_MAX_AGE,
        samesite="lax",
        secure=settings.SESSION_COOKIE_SECURE,
    )
    set_csrf_cookie(response, csrf_token)
    # Clear the return_to cookie
    response.delete_cookie(RETURN_TO_COOKIE_NAME)
    return response


@router.get("/logout")
def logout():
    """Clear the session and log out."""
    response = RedirectResponse("/")
    response.delete_cookie(SESSION_COOKIE_NAME)
    response.delete_cookie("critique_csrf")
    return response


@router.get("/check")
def check_auth(user: User = Depends(get_current_user)):
    """Check if the current user is authenticated."""
    return {"authenticated": True, "username": user.username}


@router.get("/csrf-token")
def get_csrf_token(request: Request):
    """Return the CSRF token for the current session."""
    token = request.cookies.get("critique_csrf")
    if not token:
        token = generate_csrf_token()
    return {"csrf_token": token}


