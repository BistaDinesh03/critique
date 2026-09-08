from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import AnalyticsEvent, User
from app.auth import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard")
def get_analytics_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Owner-only analytics dashboard."""
    # Only allow the platform owner (first user)
    if current_user.id != 1:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not authorized")

    # Count events
    total_page_views = db.query(func.count(AnalyticsEvent.id)).filter(
        AnalyticsEvent.event_name == "page_view"
    ).scalar() or 0

    total_project_views = db.query(func.count(AnalyticsEvent.id)).filter(
        AnalyticsEvent.event_name == "project_view"
    ).scalar() or 0

    total_feedback_starts = db.query(func.count(AnalyticsEvent.id)).filter(
        AnalyticsEvent.event_name == "feedback_start"
    ).scalar() or 0

    total_feedback_submits = db.query(func.count(AnalyticsEvent.id)).filter(
        AnalyticsEvent.event_name == "feedback_submit"
    ).scalar() or 0

    total_project_submits = db.query(func.count(AnalyticsEvent.id)).filter(
        AnalyticsEvent.event_name == "project_submit"
    ).scalar() or 0

    # Unique visitors
    unique_visitors = db.query(func.count(func.distinct(AnalyticsEvent.visitor_id))).scalar() or 0

    # Calculate conversion rates
    homepage_to_project = round((total_project_views / total_page_views) * 100, 1) if total_page_views > 0 else 0
    project_to_feedback = round((total_feedback_starts / total_project_views) * 100, 1) if total_project_views > 0 else 0
    feedback_to_submit = round((total_feedback_submits / total_feedback_starts) * 100, 1) if total_feedback_starts > 0 else 0
    feedback_to_project = round((total_project_submits / total_feedback_submits) * 100, 1) if total_feedback_submits > 0 else 0

    return {
        "totals": {
            "page_views": total_page_views,
            "project_views": total_project_views,
            "feedback_starts": total_feedback_starts,
            "feedback_submits": total_feedback_submits,
            "project_submits": total_project_submits,
            "unique_visitors": unique_visitors,
        },
        "conversion": {
            "homepage_to_project": f"{homepage_to_project}%",
            "project_to_feedback_start": f"{project_to_feedback}%",
            "feedback_start_to_submit": f"{feedback_to_submit}%",
            "feedback_to_project_submit": f"{feedback_to_project}%",
        },
    }
