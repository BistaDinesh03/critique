import secrets
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import AnalyticsEvent

VISITOR_COOKIE_NAME = "critique_visitor"
VISITOR_COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year


def _generate_visitor_id() -> str:
    return secrets.token_hex(16)


def get_or_create_visitor_id(request) -> str:
    visitor_id = request.cookies.get(VISITOR_COOKIE_NAME)
    if not visitor_id:
        visitor_id = _generate_visitor_id()
    return visitor_id


def set_visitor_cookie(response, visitor_id: str):
    response.set_cookie(
        VISITOR_COOKIE_NAME,
        visitor_id,
        max_age=VISITOR_COOKIE_MAX_AGE,
        httponly=False,
        samesite="lax",
        secure=False,
    )


def track_event(
    db: Session,
    event_name: str,
    visitor_id: str,
    user_id: int = None,
    project_id: int = None,
) -> bool:
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
