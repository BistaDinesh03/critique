from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import Project, Question, Response, User
from app.auth import get_current_user, get_current_user_optional
from app.rate_limit import reset_rate_limits


def cleanup_database():
    db = SessionLocal()
    try:
        # Delete in dependency order so foreign keys can be enforced.
        from app.models import AnalyticsEvent, ProjectView, Question, Response
        db.query(AnalyticsEvent).delete()
        db.query(ProjectView).delete()
        db.query(Response).delete()
        db.query(Question).delete()
        db.query(Project).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


def test_xss_in_project_title(auth_client):
    """Test that script tags in project title are not executed (stored as text)."""
    reset_rate_limits()
    cleanup_database()
    
    # Submit project with XSS payload in title
    xss_payload = '<script>alert("XSS")</script>'
    payload = {
        "project_data": {
            "title": xss_payload,
            "description": "Test",
            "url": None,
            "image_url": None,
        },
        "question_data": {"text": "Test?"},
    }
    response = auth_client.post("/api/projects/", json=payload)
    assert response.status_code == 201
    
    # Get the project and verify the title is stored as-is (not sanitized server-side)
    project_id = response.json()["project"]["id"]
    get_resp = auth_client.get(f"/api/projects/{project_id}")
    data = get_resp.json()
    assert data["project"]["title"] == xss_payload
    
    # The frontend should escape this when rendering (tested by frontend)
    cleanup_database()


def test_xss_in_suggestion(auth_client):
    """Test that script tags in suggestion are accepted but not executed."""
    reset_rate_limits()
    cleanup_database()
    
    # Create project
    payload = {
        "project_data": {"title": "XSS Test", "description": None, "url": None, "image_url": None},
        "question_data": {"text": "Test?"},
    }
    create_resp = auth_client.post("/api/projects/", json=payload)
    project_id = create_resp.json()["project"]["id"]

    saved = {
        get_current_user: app.dependency_overrides.pop(get_current_user, None),
        get_current_user_optional: app.dependency_overrides.pop(get_current_user_optional, None),
    }

    # Submit response with XSS payload
    xss_payload = '<img src="x" onerror="alert(1)">'
    response_payload = {
        "clarity": "very_clear",
        "would_use": "yes",
        "suggestion": xss_payload,
    }

    # Reviewer's client: point the endpoint at the reviewer (the fixture's
    # owner overrides were popped above) and attach any matching CSRF
    # cookie/header pair -- require_csrf only checks the two agree.
    db = SessionLocal()
    try:
        reviewer = User(github_id=222222, username="reviewer")
        db.add(reviewer)
        db.commit()
        db.refresh(reviewer)
    finally:
        db.close()

    token = "xss_test_token"
    reviewer_client = TestClient(app)
    reviewer_client.cookies.set("critique_csrf", token)
    reviewer_client.headers["X-CSRF-Token"] = token
    app.dependency_overrides[get_current_user] = lambda: reviewer
    app.dependency_overrides[get_current_user_optional] = lambda: reviewer

    response = reviewer_client.post(f"/api/projects/{project_id}/responses", json=response_payload)
    assert response.status_code == 201

    for dep, mock in saved.items():
        if mock is None:
            app.dependency_overrides.pop(dep, None)
        else:
            app.dependency_overrides[dep] = mock

    # Verify stored in database and retrieved accurately
    with SessionLocal() as db:
        r = db.query(Response).filter(Response.suggestion == xss_payload).first()
        assert r is not None
        assert r.suggestion == xss_payload

    get_resp = auth_client.get(f"/api/projects/{project_id}/results")
    assert get_resp.status_code == 200
    resps = get_resp.json()["responses"]
    assert len(resps) == 1
    assert resps[0]["suggestion"] == xss_payload
    
    # The suggestion should be stored as-is but escaped on render
    cleanup_database()


def test_invalid_url_rejected(auth_client):
    """Test that invalid URL is rejected and not persisted."""
    reset_rate_limits()
    cleanup_database()
    
    payload = {
        "project_data": {
            "title": "Invalid URL Test",
            "description": None,
            "url": "not-a-valid-url",
            "image_url": None,
        },
        "question_data": {"text": "Test?"},
    }
    response = auth_client.post("/api/projects/", json=payload)
    assert response.status_code == 422
    with SessionLocal() as db:
        assert db.query(Project).filter(Project.title == "Invalid URL Test").count() == 0
    
    cleanup_database()


def test_long_suggestion_rejected(auth_client):
    """Test that overly long suggestion is rejected and not persisted."""
    reset_rate_limits()
    cleanup_database()
    
    payload = {
        "project_data": {"title": "Long Suggestion", "description": None, "url": None, "image_url": None},
        "question_data": {"text": "Test?"},
    }
    create_resp = auth_client.post("/api/projects/", json=payload)
    project_id = create_resp.json()["project"]["id"]
    
    # 2001 chars - exceeds limit
    long_text = "x" * 2001
    response_payload = {
        "clarity": "very_clear",
        "would_use": "yes",
        "suggestion": long_text,
    }
    response = auth_client.post(f"/api/projects/{project_id}/responses", json=response_payload)
    assert response.status_code == 422
    with SessionLocal() as db:
        assert db.query(Response).count() == 0
    
    cleanup_database()


def test_long_title_rejected(auth_client):
    """Test that overly long title is rejected and not persisted."""
    reset_rate_limits()
    cleanup_database()
    
    long_title = "x" * 201  # 201 chars, limit is 200
    payload = {
        "project_data": {"title": long_title, "description": None, "url": None, "image_url": None},
        "question_data": {"text": "Test?"},
    }
    response = auth_client.post("/api/projects/", json=payload)
    assert response.status_code == 422
    with SessionLocal() as db:
        assert db.query(Project).count() == 0
    
    cleanup_database()
