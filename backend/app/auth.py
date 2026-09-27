import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import User
from app.csrf import generate_csrf_token, set_csrf_cookie, require_csrf
from app.rate_limit import rate_limit
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from pydantic import BaseModel, Field
from app.models import EmailLoginToken
from app.email import send_login_link

router = APIRouter(prefix="/auth", tags=["auth"])

# --- Per-email cooldown for magic-link requests ---
# Separate from the IP-based rate limiter in app/rate_limit.py.
# Keyed on normalized email to prevent one IP from spamming a single inbox
# and to prevent a single email from being bombed from many IPs.
_EMAIL_COOLDOWN = {}
_EMAIL_COOLDOWN_SECONDS = 60


def _email_cooldown_check_and_set(normalized_email: str) -> bool:
    """Return True if a cooldown is active (block request).

    Otherwise record the request time and return False (allow).
    """
    now = time.time()
    last = _EMAIL_COOLDOWN.get(normalized_email)
    if last is not None and (now - last) < _EMAIL_COOLDOWN_SECONDS:
        return True
    _EMAIL_COOLDOWN[normalized_email] = now
    return False

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


# ---------------------------------------------------------------------------
# GitHub OAuth `state` (login CSRF protection)
#
# The state is generated at initiation, sent to GitHub, and its signed twin is
# kept in an httponly cookie that only this browser holds. The callback accepts
# a state only if that cookie proves we issued it (signature + age) and the
# query value matches it exactly. The accepted state is then dropped from the
# cookie, so it is single-use. No state value is ever logged.
# ---------------------------------------------------------------------------

OAUTH_STATE_COOKIE_NAME = "critique_oauth_state"
OAUTH_STATE_MAX_AGE = 600  # seconds; mirrors the return_to cookie lifetime
OAUTH_STATE_MAX_PENDING = 3  # newest-first cap on in-flight attempts per browser

# Separate salt from the session serializer: a state can never be replayed as
# a session token (or vice versa), and neither can be forged without SECRET_KEY.
oauth_state_serializer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="oauth_state")


def _generate_oauth_state() -> str:
    """Cryptographically random, URL-safe state value."""
    return secrets.token_urlsafe(32)


def _sign_pending_states(states: list) -> str:
    """Serialize the browser's pending states into a signed cookie value."""
    return oauth_state_serializer.dumps({"states": list(states)})


def _load_pending_states(raw: Optional[str]) -> list:
    """Return this browser's pending states, or [] if the cookie is absent,
    expired, malformed, or signed by someone who is not us."""
    if not raw:
        return []
    try:
        data = oauth_state_serializer.loads(raw, max_age=OAUTH_STATE_MAX_AGE)
    except (BadSignature, SignatureExpired, ValueError, TypeError):
        return []
    if not isinstance(data, dict):
        return []
    states = data.get("states")
    if not isinstance(states, list):
        return []
    return [s for s in states if isinstance(s, str) and s and len(s) <= 128]


def _state_is_valid(pending: list, state: Optional[str]) -> bool:
    """True only if `state` is one of this browser's server-issued pending states.

    Comparison is constant time; non-ASCII input is rejected before comparing
    (hmac.compare_digest rejects non-ASCII strings).
    """
    if not state or not state.isascii():
        return False
    return any(hmac.compare_digest(candidate, state) for candidate in pending)


def _set_pending_states_cookie(response, pending: list) -> None:
    """Persist the remaining pending states, or clear the cookie when empty."""
    if pending:
        response.set_cookie(
            OAUTH_STATE_COOKIE_NAME,
            _sign_pending_states(pending),
            max_age=OAUTH_STATE_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=settings.SESSION_COOKIE_SECURE,
        )
    else:
        response.delete_cookie(OAUTH_STATE_COOKIE_NAME)


@router.get("/login")
def github_login(
    request: Request,
    return_to: str = None,
    _: None = Depends(rate_limit("auth")),
):
    """Redirect to GitHub OAuth with a per-browser, single-use state."""
    state = _generate_oauth_state()
    pending = _load_pending_states(request.cookies.get(OAUTH_STATE_COOKIE_NAME))
    # Newest attempt first; earlier in-flight attempts in this browser stay
    # valid so opening login in two tabs does not break the first one.
    pending = [state] + [s for s in pending if s != state]
    pending = pending[:OAUTH_STATE_MAX_PENDING]

    github_auth_url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
        "&scope=read:user"
        f"&state={state}"
    )
    response = RedirectResponse(github_auth_url)
    _set_pending_states_cookie(response, pending)
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
    state: Optional[str] = None,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit("auth")),
):
    """Handle GitHub OAuth callback, validating state, and create session."""
    # Validate state before contacting GitHub: missing, unknown, expired,
    # forged, or replayed states are rejected outright.
    pending = _load_pending_states(request.cookies.get(OAUTH_STATE_COOKIE_NAME))
    if not _state_is_valid(pending, state):
        raise HTTPException(status_code=400, detail="Invalid or missing OAuth state")

    # Single-use: this state is dropped from the browser's pending list on the
    # response we are about to return, success or failure.
    remaining = [s for s in pending if not hmac.compare_digest(s, state)]

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
            # Same status and body as the previous HTTPException, but it also
            # persists consumption of the accepted state.
            failure = JSONResponse(
                status_code=400, content={"detail": "GitHub authentication failed"}
            )
            _set_pending_states_cookie(failure, remaining)
            return failure

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
    # Persist consumption of the accepted state (single-use).
    _set_pending_states_cookie(response, remaining)
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

# ============================================================================
# Passwordless email authentication
# ============================================================================

def _normalize_email(raw: str) -> str:
    """Trim and lowercase. No Gmail dot/plus folding."""
    return (raw or "").strip().lower()


def _is_plausible_email(addr: str) -> bool:
    """Conservative format check. Not full RFC validation, by design."""
    if not addr or len(addr) > 320:
        return False
    if " " in addr or "\t" in addr or "\n" in addr:
        return False
    if addr.count("@") != 1:
        return False
    local, _, domain = addr.partition("@")
    if not local or not domain:
        return False
    if "." not in domain:
        return False
    return True


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()


def _client_ip_for_hash(request: Request) -> str:
    cf = request.headers.get("cf-connecting-ip")
    if cf:
        return cf
    return request.client.host if request.client else "unknown"


class EmailStartRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    return_to: Optional[str] = None


@router.post("/email/start")
def email_start(
    payload: EmailStartRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
    __: None = Depends(rate_limit("email_login_start")),
):
    """Request a magic link. Always returns a generic success response."""
    normalized = _normalize_email(payload.email)

    # Per-email cooldown. Silently accept but do not send if on cooldown.
    cooldown_active = False
    if _is_plausible_email(normalized):
        cooldown_active = _email_cooldown_check_and_set(normalized)

    # Validate return_to with the existing safe-return helper.
    return_to = None
    if payload.return_to and _is_safe_return_path(payload.return_to):
        return_to = payload.return_to

    if _is_plausible_email(normalized) and not cooldown_active:
        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=15)

        row = EmailLoginToken(
            email=normalized,
            token_hash=token_hash,
            created_at=now,
            expires_at=expires_at,
            used_at=None,
            requester_ip_hash=_hash_ip(_client_ip_for_hash(request)),
            return_to=return_to,
        )
        db.add(row)
        db.commit()

        # Send. Failure is swallowed intentionally; the response is identical either way.
        try:
            send_login_link(normalized, raw_token)
        except Exception:
            pass

    # Generic response regardless of whether email exists, is valid, or is on cooldown.
    return {"ok": True}


@router.get("/email/verify")
def email_verify(
    token: str,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit("email_login_verify")),
):
    """Consume a magic-link token, establish a session, and redirect."""
    if not token or len(token) > 200:
        return RedirectResponse("/?error=email_link")

    token_hash = _hash_token(token)
    now = datetime.now(timezone.utc)

    # Atomic consume: UPDATE ... WHERE used_at IS NULL AND expires_at > now RETURNING *.
    from sqlalchemy import update as sa_update
    stmt = (
        sa_update(EmailLoginToken)
        .where(EmailLoginToken.token_hash == token_hash)
        .where(EmailLoginToken.used_at.is_(None))
        .where(EmailLoginToken.expires_at > now)
        .values(used_at=now)
        .returning(
            EmailLoginToken.id,
            EmailLoginToken.email,
            EmailLoginToken.return_to,
        )
    )
    result = db.execute(stmt).first()
    if not result:
        db.rollback()
        return RedirectResponse("/?error=email_link")

    token_id, normalized_email, stored_return_to = result
    db.commit()

    # Find or create the user.
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user:
        # Synthetic username derived from SHA-256 of normalized email.
        # "email_" prefix cannot collide with GitHub logins (GitHub usernames
        # may only contain alphanumerics and hyphens).
        synthetic = "email_" + hashlib.sha256(normalized_email.encode("utf-8")).hexdigest()[:16]
        user = User(
            email=normalized_email,
            username=synthetic,
        )
        db.add(user)
        try:
            db.commit()
        except Exception:
            # Race: another verification created the user. Reload.
            db.rollback()
            user = db.query(User).filter(User.email == normalized_email).first()
            if not user:
                return RedirectResponse("/?error=email_link")
        else:
            db.refresh(user)

    # Determine redirect target from stored return_to, re-validated.
    redirect_target = "/"
    if stored_return_to and _is_safe_return_path(stored_return_to):
        redirect_target = stored_return_to

    session_token = create_session_token(user.id)
    csrf_token = generate_csrf_token()

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
    return response
