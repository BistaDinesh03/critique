from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.analytics import track_event, get_or_create_visitor_id, set_visitor_cookie
from app.auth import get_current_user_optional
from app.models import User
from app.rate_limit import rate_limit

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

VALID_EVENTS = {
    "page_view",
    "discover_view",
    "project_view",
    "feedback_start",
    "feedback_submit",
    "project_submit",
}


@router.post("/track")
def track(
    event_name: str,
    request: Request,
    project_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
    _: None = Depends(rate_limit("analytics")),
):
    """Track an analytics event with strict validation."""
    if not event_name or event_name not in VALID_EVENTS:
        raise HTTPException(status_code=400, detail="Invalid event name")

    visitor_id = get_or_create_visitor_id(request)
    user_id = current_user.id if current_user else None

    success = track_event(
        db=db,
        event_name=event_name,
        visitor_id=visitor_id,
        user_id=user_id,
        project_id=project_id,
    )

    response = JSONResponse({"ok": success})
    set_visitor_cookie(response, visitor_id)
    return response
