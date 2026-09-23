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
        }
        assert set(ratios.keys()) == expected_fields
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        db2.close()
        cleanup_database()
