from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from urllib.parse import urlparse
from app.database import get_db
from app.models import User, Project

router = APIRouter(prefix="/api", tags=["stats"])


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


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Return real platform stats for social proof."""
    total_builders = db.query(func.count(User.id)).scalar()
    total_projects = db.query(func.count(Project.id)).scalar()

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

    return {
        "total_builders": total_builders,
        "total_projects": total_projects,
        "builders": builders,
    }
