import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.database import SessionLocal
from app.models import Project, User

client = TestClient(app)


def test_homepage_and_discover_canonical_ignores_query_strings():
    r1 = client.get("/?auth=cancelled")
    assert r1.status_code == 200
    assert '<link rel="canonical" href="http://127.0.0.1:8000/">' in r1.text

    r2 = client.get("/discover?page=2&sort=recent")
    assert r2.status_code == 200
    assert '<link rel="canonical" href="http://127.0.0.1:8000/discover">' in r2.text


def test_project_detail_and_results_canonical_per_request():
    db = SessionLocal()
    u = User(username="canonical_tester", github_id=987123)
    db.add(u)
    db.commit()
    db.refresh(u)
    user_id = u.id

    p1 = Project(title="Canonical Project 1", description="desc", owner_id=user_id)
    p2 = Project(title="Canonical Project 2", description="desc", owner_id=user_id)
    db.add_all([p1, p2])
    db.commit()
    p1_id, p2_id = p1.id, p2.id
    db.close()

    try:
        r_p1 = client.get(f"/project/{p1_id}")
        assert r_p1.status_code == 200
        assert f'<link rel="canonical" href="http://127.0.0.1:8000/project/{p1_id}">' in r_p1.text

        r_p2 = client.get(f"/project/{p2_id}")
        assert r_p2.status_code == 200
        assert f'<link rel="canonical" href="http://127.0.0.1:8000/project/{p2_id}">' in r_p2.text

        r_p1_res = client.get(f"/project/{p1_id}/results")
        assert r_p1_res.status_code == 200
        assert f'<link rel="canonical" href="http://127.0.0.1:8000/project/{p1_id}/results">' in r_p1_res.text
    finally:
        db = SessionLocal()
        db.query(Project).filter(Project.id.in_([p1_id, p2_id])).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()
        db.close()


def test_canonical_honors_app_url(monkeypatch):
    monkeypatch.setattr(settings, "APP_URL", "https://critique.example.com")
    r = client.get("/discover")
    assert r.status_code == 200
    assert '<link rel="canonical" href="https://critique.example.com/discover">' in r.text


def test_404_page_has_no_canonical():
    r = client.get("/nonexistent-page-url", headers={"Accept": "text/html"})
    assert r.status_code == 404
    assert 'rel="canonical"' not in r.text
