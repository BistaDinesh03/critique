import secrets
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import AnalyticsEvent


def _generate_visitor_id() -> str:
    """Generate a random anonymous visitor ID."""
    return secrets.token_hex(16)


def get_or_create_visitor_id(request) -> str:
    """Get existing visitor ID from cookie or create new."""
    visitor_id = request.cookies.get("critique_visitor")
    if not visitor_id:
        visitor_id = _generate_visitor_id()
    return visitor_id


def track_event(
    db: Session,
    event_name: str,
    visitor_id: str,
    user_id: int = None,
    project_id: int = None,
) -> bool:
    """Record an analytics event. Returns True on success, False on failure."""
    try:
        event = AnalyticsEvent(
            event_name=event_name,
            visitor_id=visitor_id,
            user_id=user_id,
            project_id=project_id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(event)
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
