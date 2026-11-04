from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.database import SessionLocal
from app.main import app
from app.models import AnalyticsEvent, User


def test_analytics_dashboard_date_range_filtering():
    """Verify start and end query parameters filter events properly."""
    db = SessionLocal()
    try:
        db.query(AnalyticsEvent).delete()
        db.query(User).delete()
        db.commit()

        owner = User(github_id=999999999, username="BistaDinesh03")
        db.add(owner)
        db.commit()
        db.refresh(owner)
        owner_id = owner.id

        now = datetime(2026, 11, 4, 12, 0, 0)
        t_before = now - timedelta(days=2)
        t_start = now - timedelta(days=1)
        t_mid = now
        t_end = now + timedelta(days=1)
        t_after = now + timedelta(days=2)

        # Seed events:
        # Before range: 1 page_view
        # Exactly at start: 1 page_view
        # Inside range: 1 page_view, 1 feedback_start
        # Exactly at end: 1 page_view (should be excluded as end is exclusive)
        # After range: 1 page_view
        e1 = AnalyticsEvent(event_name="page_view", visitor_id="v1", created_at=t_before)
        e2 = AnalyticsEvent(event_name="page_view", visitor_id="v2", created_at=t_start)
        e3 = AnalyticsEvent(event_name="page_view", visitor_id="v3", created_at=t_mid)
        e4 = AnalyticsEvent(event_name="feedback_start", visitor_id="v3", created_at=t_mid)
        e5 = AnalyticsEvent(event_name="page_view", visitor_id="v4", created_at=t_end)
        e6 = AnalyticsEvent(event_name="page_view", visitor_id="v5", created_at=t_after)
        db.add_all([e1, e2, e3, e4, e5, e6])
        db.commit()
    finally:
        db.close()

    db2 = SessionLocal()
    owner = db2.query(User).filter(User.id == owner_id).first()

    app.dependency_overrides[get_current_user] = lambda: owner
    try:
        client = TestClient(app)

        # 1. Unfiltered (all-time)
        res_all = client.get("/api/analytics/dashboard")
        assert res_all.status_code == 200
        data_all = res_all.json()
        assert data_all["range"] == {"start": None, "end": None}
        assert data_all["totals"]["page_views"] == 5
        assert data_all["totals"]["feedback_starts"] == 1
        assert data_all["totals"]["unique_visitors"] == 5

        # 2. Filtered range: start to end
        start_str = t_start.isoformat() + "Z"
        end_str = t_end.isoformat() + "Z"
        res_range = client.get(f"/api/analytics/dashboard?start={start_str}&end={end_str}")
        assert res_range.status_code == 200
        data_range = res_range.json()
        assert data_range["range"]["start"] is not None
        assert data_range["range"]["end"] is not None
        # Inclusive of t_start (e2), mid (e3), exclusive of t_end (e5) -> 2 page_views
        assert data_range["totals"]["page_views"] == 2
        assert data_range["totals"]["feedback_starts"] == 1
        assert data_range["totals"]["unique_visitors"] == 2  # v2, v3

        # 3. Start only: >= t_mid
        mid_str = t_mid.isoformat() + "Z"
        res_start = client.get(f"/api/analytics/dashboard?start={mid_str}")
        assert res_start.status_code == 200
        data_start = res_start.json()
        assert data_start["totals"]["page_views"] == 3  # mid, end, after

        # 4. End only: < t_mid
        res_end = client.get(f"/api/analytics/dashboard?end={mid_str}")
        assert res_end.status_code == 200
        data_end = res_end.json()
        assert data_end["totals"]["page_views"] == 2  # before, start

        # 5. Invalid date string returns 400
        res_inv = client.get("/api/analytics/dashboard?start=not-a-date")
        assert res_inv.status_code == 400
        assert "Invalid start date format" in res_inv.json()["detail"]

        # 6. Reversed range (start >= end) returns 400
        res_rev = client.get(f"/api/analytics/dashboard?start={end_str}&end={start_str}")
        assert res_rev.status_code == 400
        assert "start must be earlier than end" in res_rev.json()["detail"]

        # 7. Naive datetime strings without 'Z' or offset are treated as UTC
        res_naive = client.get(f"/api/analytics/dashboard?start={t_start.isoformat()}&end={t_end.isoformat()}")
        assert res_naive.status_code == 200
        data_naive = res_naive.json()
        assert data_naive["totals"]["page_views"] == 2
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        db2.close()
        db_cleanup = SessionLocal()
        db_cleanup.query(AnalyticsEvent).delete()
        db_cleanup.query(User).delete()
        db_cleanup.commit()
        db_cleanup.close()
