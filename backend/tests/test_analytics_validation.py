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


def test_valid_event_accepted():
    """Valid event name is accepted and recorded."""
    reset_rate_limits()
    cleanup_database()
    client = TestClient(app)

    response = client.post("/api/analytics/track?event_name=page_view")
    assert response.status_code == 200
    assert response.json()["ok"] == True

    db = SessionLocal()
    count = db.query(AnalyticsEvent).filter(AnalyticsEvent.event_name == "page_view").count()
    db.close()
    assert count == 1
    cleanup_database()


def test_null_event_rejected():
    """Empty/null event name returns 400 and creates no row."""
    reset_rate_limits()
    cleanup_database()
    client = TestClient(app)

    response = client.post("/api/analytics/track?event_name=")
    assert response.status_code == 400

    db = SessionLocal()
    count = db.query(AnalyticsEvent).count()
    db.close()
    assert count == 0
    cleanup_database()


def test_unknown_event_rejected():
    """Unknown event name returns 400 and creates no row."""
    reset_rate_limits()
    cleanup_database()
    client = TestClient(app)

    response = client.post("/api/analytics/track?event_name=malicious_event")
    assert response.status_code == 400

    db = SessionLocal()
    count = db.query(AnalyticsEvent).count()
    db.close()
    assert count == 0
    cleanup_database()


def test_injection_attempt_rejected():
    """SQL injection-like strings are rejected."""
    reset_rate_limits()
    cleanup_database()
    client = TestClient(app)

    response = client.post("/api/analytics/track?event_name='; DROP TABLE analytics_events; --")
    assert response.status_code == 400

    db = SessionLocal()
    count = db.query(AnalyticsEvent).count()
    db.close()
    assert count == 0
    cleanup_database()


def test_all_valid_events_accepted():
    """All 6 valid events are accepted."""
    reset_rate_limits()
    cleanup_database()
    client = TestClient(app)

    valid_events = [
        "page_view",
        "discover_view",
        "project_view",
        "feedback_start",
        "feedback_submit",
        "project_submit",
    ]

    for event in valid_events:
        response = client.post(f"/api/analytics/track?event_name={event}")
        assert response.status_code == 200, f"Event {event} failed"

    db = SessionLocal()
    count = db.query(AnalyticsEvent).count()
    db.close()
    assert count == 6
    cleanup_database()
