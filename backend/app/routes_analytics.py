from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.analytics import track_event, get_or_create_visitor_id, set_visitor_cookie
from app.auth import get_current_user_optional
from app.models import User

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.post("/track")
def track(
    event_name: str,
    request: Request,
    project_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Track an analytics event and set visitor cookie if missing."""
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
