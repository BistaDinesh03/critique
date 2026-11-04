from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from urllib.parse import urlparse
import time
from app.database import get_db
from app.models import User, Project, Question, Response

router = APIRouter(prefix="/api", tags=["stats"])

_stats_cache = {
    "data": None,
    "expires_at": 0.0,
}
STATS_CACHE_TTL = 60.0  # seconds


def clear_stats_cache():
    """Reset stats cache for tests or updates."""
    _stats_cache["data"] = None
    _stats_cache["expires_at"] = 0.0


def _safe_avatar_url(url):
    """Return the avatar URL only if it is a plain https URL we may render.

    Avatar URLs originate from the GitHub API and live on the user row, so the
    scheme is re-checked before one is handed to the page. Anything else comes
    back as None and the frontend draws a local, deterministic fallback avatar
    instead of loading a broken or unsafe image.
    """
    if not isinstance(url, str) or not url or len(url) > 500:
        return None
    # No whitespace or control characters: a URL that needs escaping is not a
    # URL we are willing to render.
    if any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in url):
        return None
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    if parsed.username or parsed.password:
        return None
    return url


PUBLIC_MEMBER_LIMIT = 6


def _public_members(db: Session, limit: int = PUBLIC_MEMBER_LIMIT):
    """Return recent builders we may introduce by name and picture.

    Only accounts that own a project and carry a real, public identity are
    eligible: a non-synthetic username (GitHub login) and a plain https avatar.
    Email sign-ins carry a keyed placeholder username and no image, so they are
    deliberately not presented as named members. Requiring a project keeps the
    supporting copy ("builders sharing their projects") literally true.
    """
    rows = (
        db.query(User.username, User.avatar_url)
        .filter(User.avatar_url.isnot(None), User.projects.any())
        .order_by(User.created_at.desc())
        .limit(limit)
        .all()
    )

    members = []
    for username, avatar_url in rows:
        safe_url = _safe_avatar_url(avatar_url)
        if safe_url and username and not username.startswith("email_"):
            members.append({"username": username, "avatar_url": safe_url})
    return members


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Return real platform stats for social proof."""
    now = time.time()
    if _stats_cache["data"] is not None and now < _stats_cache["expires_at"]:
        return _stats_cache["data"]

    total_builders = db.query(func.count(User.id)).scalar() or 0
    total_projects = db.query(func.count(Project.id)).scalar() or 0
    total_questions = db.query(func.count(Question.id)).scalar() or 0
    total_responses = db.query(func.count(Response.id)).scalar() or 0

    # Most recent builders. Every builder is returned: one with an avatar URL
    # (GitHub) renders that image, one without renders the local fallback.
    users = (
        db.query(User.username, User.avatar_url)
        .order_by(User.created_at.desc())
        .limit(4)
        .all()
    )

    builders = [
        {"username": u[0], "avatar_url": _safe_avatar_url(u[1])}
        for u in users
    ]

    data = {
        "total_builders": total_builders,
        "total_projects": total_projects,
        "total_questions": total_questions,
        "total_responses": total_responses,
        "builders": builders,
        "public_members": _public_members(db),
    }
    _stats_cache["data"] = data
    _stats_cache["expires_at"] = now + STATS_CACHE_TTL
    return data
