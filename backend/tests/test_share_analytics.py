"""The analytics contract around the optional-sharing events.

Phase 7 of the sharing pass. Four events were added -- ``share_ui_shown``,
``share_copy_link``, ``share_copy_post``, ``share_option_clicked`` -- and
the rule for adding them is that both allowlists move together: the array in
``static/analytics.js`` and the set in ``app/routes_analytics.py`` must be
identical, or events are silently dropped in production. The dashboard
reports them as plain action counts; an opened compose window is never a
completed share, and no event can carry personal content because the
tracking row has no free-text column at all.
"""

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import AnalyticsEvent, User
from app.rate_limit import reset_rate_limits
from app.routes_analytics import VALID_EVENTS as BACKEND_EVENTS

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"

SHARE_EVENTS = {
    "share_ui_shown",
    "share_copy_link",
    "share_copy_post",
    "share_option_clicked",
}


def cleanup_database():
    db = SessionLocal()
    try:
        db.query(AnalyticsEvent).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


def frontend_events():
    """The allowlist the browser actually sends against."""
    source = (STATIC_DIR / "analytics.js").read_text(encoding="utf-8")
    block = re.search(r"VALID_EVENTS = \[(.*?)\]", source, re.S)
    assert block, "analytics.js no longer defines a VALID_EVENTS array"
    return set(re.findall(r"'([a-z_]+)'", block.group(1)))


def _post_event(client, name, project_id=None):
    url = f"/api/analytics/track?event_name={name}"
    if project_id is not None:
        url += f"&project_id={project_id}"
    return client.post(url)


# ---------------------------------------------------------------------------
# The allowlists stay in step
# ---------------------------------------------------------------------------


def test_frontend_and_backend_allowlists_are_identical():
    """Every event the page can send is accepted by the API, and vice versa."""
    assert frontend_events() == set(BACKEND_EVENTS)


def test_the_share_events_are_allowed_on_both_sides():
    assert SHARE_EVENTS <= set(BACKEND_EVENTS)
    assert SHARE_EVENTS <= frontend_events()


def test_all_preexisting_events_are_still_allowed():
    """Adding share events must not disturb the established contract."""
    established = {
        "page_view",
        "discover_view",
        "project_view",
        "feedback_start",
        "feedback_submit",
        "feedback_submit_attempt",
        "feedback_submit_error",
        "project_submit",
        "login_prompt_shown",
        "login_started",
        "login_success",
        "feedback_resume",
        "auth_method_selected_github",
        "auth_method_selected_email",
        "email_verification_sent",
        "email_verification_success",
    }
    assert established <= set(BACKEND_EVENTS)
    assert established <= frontend_events()


# ---------------------------------------------------------------------------
# The endpoint's behaviour
# ---------------------------------------------------------------------------


def test_share_events_are_accepted_and_recorded():
    reset_rate_limits()
    cleanup_database()
    client = TestClient(app)

    for name in sorted(SHARE_EVENTS):
        r = _post_event(client, name, project_id=9)
        assert r.status_code == 200, f"{name} was rejected"
        assert r.json()["ok"] is True

    db = SessionLocal()
    for name in SHARE_EVENTS:
        count = db.query(AnalyticsEvent).filter(
            AnalyticsEvent.event_name == name
        ).count()
        assert count == 1, f"{name} not recorded"
    db.close()
    cleanup_database()


def test_share_event_near_misses_are_rejected():
    reset_rate_limits()
    cleanup_database()
    client = TestClient(app)

    for bad in [
        "share_ui",
        "share_ui_shown ",
        "share_copy_links",
        "Share_ui_shown",
        "share_copy_post_x",
    ]:
        r = _post_event(client, bad)
        assert r.status_code == 400, f"{bad!r} should have been rejected"

    db = SessionLocal()
    assert db.query(AnalyticsEvent).count() == 0
    db.close()
    cleanup_database()


def test_share_events_carry_no_personal_payload():
    """The row has fixed columns only: no free text can travel with a share."""
    columns = {column.name for column in AnalyticsEvent.__table__.columns}
    assert columns == {
        "id",
        "event_name",
        "visitor_id",
        "user_id",
        "project_id",
        "created_at",
    }

    # Extra query parameters (an email, a title, a post body) are ignored:
    # the endpoint reads only the fields it declares.
    reset_rate_limits()
    cleanup_database()
    client = TestClient(app)
    r = client.post(
        "/api/analytics/track?event_name=share_copy_post"
        "&project_id=9&email=someone@example.com&text=secret+post"
    )
    assert r.status_code == 200

    db = SessionLocal()
    row = db.query(AnalyticsEvent).filter(
        AnalyticsEvent.event_name == "share_copy_post"
    ).one()
    assert row.project_id == 9
    as_dict = {key: getattr(row, key) for key in columns}
    assert "someone@example.com" not in repr(as_dict)
    assert "secret post" not in repr(as_dict)
    db.close()
    cleanup_database()


# ---------------------------------------------------------------------------
# The owner dashboard
# ---------------------------------------------------------------------------


def test_dashboard_reports_share_totals_as_plain_action_counts():
    from app.auth import get_current_user

    reset_rate_limits()
    cleanup_database()

    db = SessionLocal()
    owner = User(github_id=777777777, username="BistaDinesh03")
    db.add(owner)
    db.commit()
    db.refresh(owner)
    owner_id = owner.id

    seed = {
        "share_ui_shown": 4,
        "share_copy_link": 2,
        "share_copy_post": 3,
        "share_option_clicked": 1,
    }
    for name, n in seed.items():
        for _ in range(n):
            db.add(AnalyticsEvent(event_name=name, visitor_id="test_visitor"))
    db.commit()
    db.close()

    db2 = SessionLocal()
    owner = db2.query(User).filter(User.id == owner_id).first()

    def mock_get_current_user():
        return owner

    app.dependency_overrides[get_current_user] = mock_get_current_user
    try:
        client = TestClient(app)
        r = client.get("/api/analytics/dashboard")
        assert r.status_code == 200
        totals = r.json()["totals"]
        for name, n in seed.items():
            assert totals[name] == n, f"dashboard total for {name}"
        # No ratio pretends an opened compose window was a successful share.
        ratios = r.json()["event_ratios"]
        assert not [k for k in ratios if k.startswith("share_")]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        db2.close()
        cleanup_database()
