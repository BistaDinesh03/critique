from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import AnalyticsEvent, User
from app.auth import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Owner usernames allowed to view dashboard
OWNER_USERNAMES = {"BistaDinesh03"}


def _parse_iso_datetime(value: Optional[str], param_name: str) -> Optional[datetime]:
    """Parse an ISO 8601 string into a UTC datetime."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {param_name} date format. Expected ISO 8601 (e.g. YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ).",
        )


@router.get("/dashboard")
def get_analytics_dashboard(
    start: Optional[str] = Query(None, description="Start datetime in ISO 8601 (inclusive)"),
    end: Optional[str] = Query(None, description="End datetime in ISO 8601 (exclusive)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Owner-only analytics dashboard."""
    if current_user.username not in OWNER_USERNAMES:
        raise HTTPException(status_code=403, detail="Not authorized")

    start_dt = _parse_iso_datetime(start, "start")
    end_dt = _parse_iso_datetime(end, "end")

    if start_dt and end_dt and start_dt >= end_dt:
        raise HTTPException(
            status_code=400,
            detail="Invalid date range: start must be earlier than end.",
        )

    filters = []
    if start_dt:
        filters.append(AnalyticsEvent.created_at >= start_dt.replace(tzinfo=None))
    if end_dt:
        filters.append(AnalyticsEvent.created_at < end_dt.replace(tzinfo=None))

    def count_event(name: str) -> int:
        q = db.query(func.count(AnalyticsEvent.id)).filter(AnalyticsEvent.event_name == name)
        for f in filters:
            q = q.filter(f)
        return q.scalar() or 0

    total_feedback_form_viewed = count_event("feedback_form_viewed")

    total_page_views = count_event("page_view")
    total_discover_views = count_event("discover_view")
    total_project_views = count_event("project_view")
    total_feedback_starts = count_event("feedback_start")
    total_feedback_submits = count_event("feedback_submit")
    total_project_submits = count_event("project_submit")
    total_login_prompts = count_event("login_prompt_shown")
    total_login_starts = count_event("login_started")
    total_login_successes = count_event("login_success")
    total_feedback_resumes = count_event("feedback_resume")
    total_feedback_submit_attempts = count_event("feedback_submit_attempt")
    total_feedback_submit_errors = count_event("feedback_submit_error")
    total_auth_method_github = count_event("auth_method_selected_github")
    total_auth_method_email = count_event("auth_method_selected_email")
    total_email_verification_sent = count_event("email_verification_sent")
    total_email_verification_success = count_event("email_verification_success")
    total_share_ui_shown = count_event("share_ui_shown")
    total_share_copy_link = count_event("share_copy_link")
    total_share_copy_post = count_event("share_copy_post")
    total_share_option_clicked = count_event("share_option_clicked")

    q_uv = db.query(func.count(func.distinct(AnalyticsEvent.visitor_id)))
    for f in filters:
        q_uv = q_uv.filter(f)
    unique_visitors = q_uv.scalar() or 0

    homepage_to_project = round((total_project_views / total_page_views) * 100, 1) if total_page_views > 0 else 0
    project_to_feedback = round((total_feedback_starts / total_project_views) * 100, 1) if total_project_views > 0 else 0
    feedback_to_submit = round((total_feedback_submits / total_feedback_starts) * 100, 1) if total_feedback_starts > 0 else 0
    feedback_to_project = round((total_project_submits / total_feedback_submits) * 100, 1) if total_feedback_submits > 0 else 0
    attempts_to_submit = round((total_feedback_submits / total_feedback_submit_attempts) * 100, 1) if total_feedback_submit_attempts > 0 else 0
    errors_to_attempts = round((total_feedback_submit_errors / total_feedback_submit_attempts) * 100, 1) if total_feedback_submit_attempts > 0 else 0
    attempts_per_start = round((total_feedback_submit_attempts / total_feedback_starts) * 100, 1) if total_feedback_starts > 0 else 0
    auth_selections_total = total_auth_method_github + total_auth_method_email
    github_share = round((total_auth_method_github / auth_selections_total) * 100, 1) if auth_selections_total > 0 else 0
    email_share = round((total_auth_method_email / auth_selections_total) * 100, 1) if auth_selections_total > 0 else 0
    email_success_rate = round((total_email_verification_success / total_email_verification_sent) * 100, 1) if total_email_verification_sent > 0 else 0

    return {
        "range": {
            "start": start_dt.isoformat() if start_dt else None,
            "end": end_dt.isoformat() if end_dt else None,
        },
        "totals": {
            "page_views": total_page_views,
            "discover_views": total_discover_views,
            "project_views": total_project_views,
            "feedback_form_viewed": total_feedback_form_viewed,
            "feedback_starts": total_feedback_starts,
            "feedback_submits": total_feedback_submits,
            "project_submits": total_project_submits,
            "unique_visitors": unique_visitors,
            "login_prompts_shown": total_login_prompts,
            "login_started": total_login_starts,
            "login_success": total_login_successes,
            "feedback_resumes": total_feedback_resumes,
            "feedback_submit_attempts": total_feedback_submit_attempts,
            "feedback_submit_errors": total_feedback_submit_errors,
            "auth_method_selected_github": total_auth_method_github,
            "auth_method_selected_email": total_auth_method_email,
            "email_verification_sent": total_email_verification_sent,
            "email_verification_success": total_email_verification_success,
            "share_ui_shown": total_share_ui_shown,
            "share_copy_link": total_share_copy_link,
            "share_copy_post": total_share_copy_post,
            "share_option_clicked": total_share_option_clicked,
        },
        "event_ratios": {
            "project_views_per_page_view": f"{homepage_to_project}%",
            "feedback_starts_per_project_view": f"{project_to_feedback}%",
            "feedback_submits_per_feedback_start": f"{feedback_to_submit}%",
            "project_submits_per_feedback_submit": f"{feedback_to_project}%",
            # Event ratios (count-to-count), NOT unique-user conversion rates.
            "feedback_submit_attempts_per_feedback_start": f"{attempts_per_start}%",
            "feedback_submits_per_feedback_submit_attempt": f"{attempts_to_submit}%",
            "feedback_submit_errors_per_feedback_submit_attempt": f"{errors_to_attempts}%",
            "github_auth_method_share": f"{github_share}%",
            "email_auth_method_share": f"{email_share}%",
            "email_verification_success_per_email_verification_sent": f"{email_success_rate}%",
        },
    }
