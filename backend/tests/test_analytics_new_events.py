"""Regression tests for the Phase 4 analytics additions.

Covers:
- The two events that were previously blocked by the frontend allowlist mismatch.
- The four new auth/email events added in Phase 4.
- The dashboard totals and ratios for the new events.
- Zero-denominator behavior for the new ratios.
"""
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import AnalyticsEvent, User, Project
from app.rate_limit import reset_rate_limits


def cleanup_database():
    db = SessionLocal()
    try:
        db.query(AnalyticsEvent).delete()
        db.query(User).delete()
        db.query(Project).delete()
        db.commit()
    finally:
        db.close()


def _post_event(client, name, project_id=None):
    url = f"/api/analytics/track?event_name={name}"
    if project_id is not None:
        url += f"&project_id={project_id}"
    return client.post(url)


# ---------------- acceptance of new events ----------------

def test_feedback_submit_attempt_accepted():
    reset_rate_limits()
    cleanup_database()
    client = TestClient(app)

    r = _post_event(client, "feedback_submit_attempt", project_id=1)
    assert r.status_code == 200
    assert r.json()["ok"] is True

    db = SessionLocal()
    count = db.query(AnalyticsEvent).filter(
        AnalyticsEvent.event_name == "feedback_submit_attempt"
    ).count()
    db.close()
    assert count == 1
    cleanup_database()


def test_feedback_submit_error_accepted():
    reset_rate_limits()
    cleanup_database()
    client = TestClient(app)

    r = _post_event(client, "feedback_submit_error", project_id=1)
    assert r.status_code == 200
    assert r.json()["ok"] is True

    db = SessionLocal()
    count = db.query(AnalyticsEvent).filter(
        AnalyticsEvent.event_name == "feedback_submit_error"
    ).count()
    db.close()
    assert count == 1
    cleanup_database()


def test_new_auth_events_accepted():
    """All four new auth/email events are accepted and recorded."""
    reset_rate_limits()
    cleanup_database()
    client = TestClient(app)

    names = [
        "auth_method_selected_github",
        "auth_method_selected_email",
        "email_verification_sent",
        "email_verification_success",
    ]
    for n in names:
        r = _post_event(client, n, project_id=1)
        assert r.status_code == 200, f"{n} was rejected"
        assert r.json()["ok"] is True

    db = SessionLocal()
    total = db.query(AnalyticsEvent).count()
    db.close()
    assert total == 4
    cleanup_database()


def test_new_auth_event_names_are_in_allowlist_only():
    """Each new name is a distinct accepted event, not a substring of another."""
    reset_rate_limits()
    cleanup_database()
    client = TestClient(app)

    # A near-miss on a valid name must still be rejected.
    for bad in [
        "auth_method_selected",
        "email_verification",
        "email_verification_",
        " auth_method_selected_email",
        "auth_method_selected_email ",
    ]:
        r = _post_event(client, bad)
        assert r.status_code == 400, f"{bad!r} should have been rejected"

    db = SessionLocal()
    count = db.query(AnalyticsEvent).count()
    db.close()
    assert count == 0
    cleanup_database()


# ---------------- dashboard totals ----------------

def test_dashboard_reports_new_totals():
    from app.auth import get_current_user

    reset_rate_limits()
    cleanup_database()

    db = SessionLocal()
    owner = User(github_id=888888888, username="BistaDinesh03")
    db.add(owner)
    db.commit()
    db.refresh(owner)
    owner_id = owner.id
    db.close()

    # Seed events that the new totals will report.
    seed = {
        "feedback_submit_attempt": 3,
        "feedback_submit_error": 1,
        "auth_method_selected_github": 2,
        "auth_method_selected_email": 2,
        "email_verification_sent": 2,
        "email_verification_success": 1,
    }
    db = SessionLocal()
    try:
        for name, n in seed.items():
            for _ in range(n):
                db.add(AnalyticsEvent(
                    event_name=name,
                    visitor_id="test_visitor",
                ))
        db.commit()
    finally:
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
        data = r.json()

        totals = data["totals"]
        assert totals["feedback_submit_attempts"] == 3
        assert totals["feedback_submit_errors"] == 1
        assert totals["auth_method_selected_github"] == 2
        assert totals["auth_method_selected_email"] == 2
        assert totals["email_verification_sent"] == 2
        assert totals["email_verification_success"] == 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        db2.close()
        cleanup_database()


def test_dashboard_ratios_with_events():
    from app.auth import get_current_user

    reset_rate_limits()
    cleanup_database()

    db = SessionLocal()
    owner = User(github_id=777777777, username="BistaDinesh03")
    db.add(owner)
    db.commit()
    db.refresh(owner)
    owner_id = owner.id
    db.close()

    # 4 starts, 2 attempts, 1 submit, 1 error
    # 3 github, 1 email
    # 2 sent, 1 success
    seed = {
        "feedback_start": 4,
        "feedback_submit_attempt": 2,
        "feedback_submit": 1,
        "feedback_submit_error": 1,
        "auth_method_selected_github": 3,
        "auth_method_selected_email": 1,
        "email_verification_sent": 2,
        "email_verification_success": 1,
    }
    db = SessionLocal()
    try:
        for name, n in seed.items():
            for _ in range(n):
                db.add(AnalyticsEvent(event_name=name, visitor_id="test_visitor"))
        db.commit()
    finally:
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
        ratios = r.json()["event_ratios"]

        # attempts_per_start = 2/4 = 50.0
        assert ratios["feedback_submit_attempts_per_feedback_start"] == "50.0%"
        # submits_per_attempt = 1/2 = 50.0
        assert ratios["feedback_submits_per_feedback_submit_attempt"] == "50.0%"
        # errors_per_attempt = 1/2 = 50.0
        assert ratios["feedback_submit_errors_per_feedback_submit_attempt"] == "50.0%"
        # github share = 3/4 = 75.0
        assert ratios["github_auth_method_share"] == "75.0%"
        # email share = 1/4 = 25.0
        assert ratios["email_auth_method_share"] == "25.0%"
        # email success rate = 1/2 = 50.0
        assert ratios["email_verification_success_per_email_verification_sent"] == "50.0%"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        db2.close()
        cleanup_database()


def test_dashboard_ratios_zero_denominator_safe():
    """Empty database: every new ratio returns 0, no division-by-zero crash."""
    from app.auth import get_current_user

    reset_rate_limits()
    cleanup_database()

    db = SessionLocal()
    owner = User(github_id=666666666, username="BistaDinesh03")
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
        r = client.get("/api/analytics/dashboard")
        assert r.status_code == 200
        data = r.json()

        # Every total is present and zero.
        for key in [
            "feedback_submit_attempts",
            "feedback_submit_errors",
            "auth_method_selected_github",
            "auth_method_selected_email",
            "email_verification_sent",
            "email_verification_success",
        ]:
            assert data["totals"][key] == 0, f"{key} should be 0"

        # Every new ratio returns "0%" without raising.
        ratios = data["event_ratios"]
        for key in [
            "feedback_submit_attempts_per_feedback_start",
            "feedback_submits_per_feedback_submit_attempt",
            "feedback_submit_errors_per_feedback_submit_attempt",
            "github_auth_method_share",
            "email_auth_method_share",
            "email_verification_success_per_email_verification_sent",
        ]:
            assert ratios[key] == "0%", f"{key} should be 0%"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        db2.close()
        cleanup_database()


def test_dashboard_existing_ratios_unchanged():
    """The four original ratio keys still exist with the same values."""
    from app.auth import get_current_user

    reset_rate_limits()
    cleanup_database()

    db = SessionLocal()
    owner = User(github_id=555555555, username="BistaDinesh03")
    db.add(owner)
    db.commit()
    db.refresh(owner)
    owner_id = owner.id
    db.close()

    # 10 page_views, 2 project_views, 2 feedback_start, 1 feedback_submit
    seed = {
        "page_view": 10,
        "project_view": 2,
        "feedback_start": 2,
        "feedback_submit": 1,
    }
    db = SessionLocal()
    try:
        for name, n in seed.items():
            for _ in range(n):
                db.add(AnalyticsEvent(event_name=name, visitor_id="test_visitor"))
        db.commit()
    finally:
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
        ratios = r.json()["event_ratios"]

        # project_views_per_page_view = 2/10 = 20.0
        assert ratios["project_views_per_page_view"] == "20.0%"
        # feedback_starts_per_project_view = 2/2 = 100.0
        assert ratios["feedback_starts_per_project_view"] == "100.0%"
        # feedback_submits_per_feedback_start = 1/2 = 50.0
        assert ratios["feedback_submits_per_feedback_start"] == "50.0%"
        # project_submits_per_feedback_submit = 0/1 = 0.0
        assert ratios["project_submits_per_feedback_submit"] == "0.0%"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        db2.close()
        cleanup_database()