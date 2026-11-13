from http.cookies import SimpleCookie

import pytest
from app.analytics import VISITOR_COOKIE_MAX_AGE, VISITOR_COOKIE_NAME
from app.config import settings
from app.database import SessionLocal
from app.main import app
from app.models import AnalyticsEvent, Project, User
from app.rate_limit import reset_rate_limits
from fastapi.testclient import TestClient


def cleanup_database():
    db = SessionLocal()
    try:
        db.query(AnalyticsEvent).delete()
        db.query(User).delete()
        db.query(Project).delete()
        db.commit()
    finally:
        db.close()


def test_page_view_tracked():
    reset_rate_limits()
    cleanup_database()

    client = TestClient(app)
    response = client.post("/api/analytics/track?event_name=page_view")

    assert response.status_code == 200
    assert response.json()["ok"] == True

    # Verify event was created
    db = SessionLocal()
    count = db.query(AnalyticsEvent).filter(AnalyticsEvent.event_name == "page_view").count()
    db.close()
    assert count == 1

    cleanup_database()


def test_feedback_submit_tracked():
    reset_rate_limits()
    cleanup_database()

    client = TestClient(app)
    response = client.post("/api/analytics/track?event_name=feedback_submit")

    assert response.status_code == 200
    db = SessionLocal()
    count = db.query(AnalyticsEvent).filter(AnalyticsEvent.event_name == "feedback_submit").count()
    db.close()
    assert count == 1

    cleanup_database()


def test_dashboard_requires_auth():
    reset_rate_limits()
    cleanup_database()

    client = TestClient(app)
    response = client.get("/api/analytics/dashboard")
    assert response.status_code in (401, 403)

    cleanup_database()


def test_dashboard_event_ratios_naming():
    from app.auth import get_current_user

    reset_rate_limits()
    cleanup_database()

    db = SessionLocal()
    owner = User(github_id=999999999, username="BistaDinesh03")
    db.add(owner)
    db.commit()
    db.refresh(owner)
    owner_id = owner.id
    db.close()

    db2 = SessionLocal()
    owner = db2.query(User).filter(User.id == owner_id).first()

    def mock_get_current_user():
        return owner

    app.dependency_overrides[get_current_user] = mock_get_current_user
    try:
        client = TestClient(app)
        response = client.get("/api/analytics/dashboard")
        assert response.status_code == 200

        data = response.json()
        assert "event_ratios" in data
        assert "conversion" not in data

        ratios = data["event_ratios"]
        expected_fields = {
            "project_views_per_page_view",
            "feedback_starts_per_project_view",
            "feedback_submits_per_feedback_start",
            "project_submits_per_feedback_submit",
            "feedback_submit_attempts_per_feedback_start",
            "feedback_submits_per_feedback_submit_attempt",
            "feedback_submit_errors_per_feedback_submit_attempt",
            "github_auth_method_share",
            "email_auth_method_share",
            "email_verification_success_per_email_verification_sent",        }
        assert set(ratios.keys()) == expected_fields
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        db2.close()
        cleanup_database()


@pytest.mark.parametrize("secure", [False, True])
def test_visitor_cookie_flags_and_tracking(monkeypatch, secure):
    monkeypatch.setattr(settings, "SESSION_COOKIE_SECURE", secure)
    cleanup_database()
    try:
        with TestClient(app, base_url="https://testserver") as client:
            first = client.post("/api/analytics/track?event_name=page_view")
            assert first.status_code == 200
            assert first.json()["ok"] is True
            cookie = SimpleCookie()
            cookie.load(first.headers["set-cookie"])
            visitor = cookie[VISITOR_COOKIE_NAME]
            assert bool(visitor["secure"]) is secure
            assert visitor["httponly"]
            assert visitor["samesite"] == "lax"
            assert visitor["max-age"] == str(VISITOR_COOKIE_MAX_AGE)
            assert visitor["path"] == "/"

            second = client.post("/api/analytics/track?event_name=discover_view")
            assert second.status_code == 200
            assert second.json()["ok"] is True
            assert second.cookies[VISITOR_COOKIE_NAME] == visitor.value

            db = SessionLocal()
            try:
                events = db.query(AnalyticsEvent).all()
                assert len(events) == 2
                assert {event.visitor_id for event in events} == {visitor.value}
            finally:
                db.close()
    finally:
        cleanup_database()


@pytest.mark.parametrize("bad_cookie", ["a" * 200, "../../etc/passwd", "<script>alert(1)</script>", "not-valid-hex!"])
def test_malformed_or_oversized_visitor_cookie_is_discarded(bad_cookie):
    """Oversized or malformed critique_visitor cookie is rejected and replaced with a valid 32-hex id."""
    cleanup_database()
    try:
        with TestClient(app, base_url="https://testserver") as client:
            client.cookies.set(VISITOR_COOKIE_NAME, bad_cookie)
            res = client.post("/api/analytics/track?event_name=page_view")
            assert res.status_code == 200
            assert res.json()["ok"] is True

            cookie = SimpleCookie()
            cookie.load(res.headers["set-cookie"])
            visitor = cookie[VISITOR_COOKIE_NAME].value
            assert visitor != bad_cookie
            assert len(visitor) == 32
            assert all(c in "0123456789abcdef" for c in visitor)

            db = SessionLocal()
            try:
                events = db.query(AnalyticsEvent).all()
                assert len(events) == 1
                assert events[0].visitor_id == visitor
            finally:
                db.close()
    finally:
        cleanup_database()


# --- Dashboard response contract (#44) -------------------------------------
#
# The dashboard is consumed by the owner and by the point-in-time snapshots in
# docs/. A refactor that drops or renames a key must fail a test rather than
# silently corrupt those reports. These two tests pin the entire response shape
# and the zero-denominator behaviour of every ratio.

DASHBOARD_TOTALS_KEYS = {
    "page_views",
    "discover_views",
    "project_views",
    "feedback_form_viewed",
    "feedback_starts",
    "feedback_submits",
    "project_submits",
    "unique_visitors",
    "login_prompts_shown",
    "login_started",
    "login_success",
    "feedback_resumes",
    "feedback_submit_attempts",
    "feedback_submit_errors",
    "feedback_already_responded",
    "auth_method_selected_github",
    "auth_method_selected_email",
    "email_verification_sent",
    "email_verification_success",
    "share_ui_shown",
    "share_copy_link",
    "share_copy_post",
    "share_option_clicked",
}

DASHBOARD_RATIO_KEYS = {
    "project_views_per_page_view",
    "feedback_starts_per_project_view",
    "feedback_submits_per_feedback_start",
    "project_submits_per_feedback_submit",
    "feedback_submit_attempts_per_feedback_start",
    "feedback_submits_per_feedback_submit_attempt",
    "feedback_submit_errors_per_feedback_submit_attempt",
    "github_auth_method_share",
    "email_auth_method_share",
    "email_verification_success_per_email_verification_sent",
}


def _dashboard_client():
    """A TestClient whose current user is the owner, so the dashboard is 200."""
    from app.auth import get_current_user

    db = SessionLocal()
    owner = User(github_id=999999001, username="BistaDinesh03")
    db.add(owner)
    db.commit()
    db.refresh(owner)
    db.close()

    db = SessionLocal()
    owner = db.query(User).filter(User.github_id == 999999001).first()

    app.dependency_overrides[get_current_user] = lambda: owner
    return TestClient(app), db, get_current_user


def test_dashboard_response_contract_with_zero_denominators():
    """Every key is pinned, and every ratio is safe when its denominator is 0."""
    reset_rate_limits()
    cleanup_database()

    client, db, override = _dashboard_client()
    try:
        response = client.get("/api/analytics/dashboard")
        assert response.status_code == 200

        data = response.json()

        # The complete top-level contract. A key added, removed or renamed in
        # either branch fails here.
        assert set(data.keys()) == {"totals", "event_ratios"}
        assert set(data["totals"].keys()) == DASHBOARD_TOTALS_KEYS
        assert set(data["event_ratios"].keys()) == DASHBOARD_RATIO_KEYS

        # With no events every denominator is zero. No ZeroDivisionError, and
        # every ratio is the explicit "0%" fallback rather than None or NaN.
        assert all(value == 0 for value in data["totals"].values())
        assert all(value == "0%" for value in data["event_ratios"].values())
    finally:
        app.dependency_overrides.pop(override, None)
        db.close()
        cleanup_database()


def test_dashboard_ratios_from_a_controlled_fixture():
    """Ratios and totals are exact for a hand-built, non-zero event set."""
    reset_rate_limits()
    cleanup_database()

    counts = {
        "page_view": 10,
        "discover_view": 7,
        "project_view": 5,
        "feedback_form_viewed": 3,
        "feedback_start": 2,
        "feedback_submit": 1,
        "project_submit": 2,
        "login_prompt_shown": 5,
        "login_started": 4,
        "login_success": 3,
        "feedback_resume": 1,
        "feedback_submit_attempt": 2,
        "feedback_submit_error": 1,
        "feedback_already_responded": 1,
        "auth_method_selected_github": 3,
        "auth_method_selected_email": 1,
        "email_verification_sent": 4,
        "email_verification_success": 3,
        "share_ui_shown": 6,
        "share_copy_link": 2,
        "share_copy_post": 1,
        "share_option_clicked": 3,
    }

    db = SessionLocal()
    try:
        # Two extra visitors on page_view, so unique_visitors is exactly 3.
        for index in range(counts["page_view"]):
            visitor = "v1" if index < counts["page_view"] - 2 else "v%d" % (index - counts["page_view"] + 4)
            db.add(AnalyticsEvent(event_name="page_view", visitor_id=visitor))
        for event_name, count in counts.items():
            if event_name == "page_view":
                continue
            for _ in range(count):
                db.add(AnalyticsEvent(event_name=event_name, visitor_id="v1"))
        db.commit()
    finally:
        db.close()

    client, db, override = _dashboard_client()
    try:
        response = client.get("/api/analytics/dashboard")
        assert response.status_code == 200
        data = response.json()

        expected_totals = {
            "page_views": 10,
            "discover_views": 7,
            "project_views": 5,
            "feedback_form_viewed": 3,
            "feedback_starts": 2,
            "feedback_submits": 1,
            "project_submits": 2,
            "unique_visitors": 3,
            "login_prompts_shown": 5,
            "login_started": 4,
            "login_success": 3,
            "feedback_resumes": 1,
            "feedback_submit_attempts": 2,
            "feedback_submit_errors": 1,
            "feedback_already_responded": 1,
            "auth_method_selected_github": 3,
            "auth_method_selected_email": 1,
            "email_verification_sent": 4,
            "email_verification_success": 3,
            "share_ui_shown": 6,
            "share_copy_link": 2,
            "share_copy_post": 1,
            "share_option_clicked": 3,
        }
        assert set(expected_totals) == DASHBOARD_TOTALS_KEYS

        assert data["totals"] == expected_totals

        # 10 -> 5 = 50.0%, 5 -> 2 = 40.0%, 2 -> 1 = 50.0%, 1 -> 2 = 200.0%,
        # 2 -> 2 = 100.0%, 2 -> 1 = 50.0%, 2 -> 1 = 50.0%,
        # auth 3/4 = 75.0%, 1/4 = 25.0%, email 3/4 = 75.0%.
        assert data["event_ratios"] == {
            "project_views_per_page_view": "50.0%",
            "feedback_starts_per_project_view": "40.0%",
            "feedback_submits_per_feedback_start": "50.0%",
            "project_submits_per_feedback_submit": "200.0%",
            "feedback_submit_attempts_per_feedback_start": "100.0%",
            "feedback_submits_per_feedback_submit_attempt": "50.0%",
            "feedback_submit_errors_per_feedback_submit_attempt": "50.0%",
            "github_auth_method_share": "75.0%",
            "email_auth_method_share": "25.0%",
            "email_verification_success_per_email_verification_sent": "75.0%",
        }
    finally:
        app.dependency_overrides.pop(override, None)
        db.close()
        cleanup_database()
