from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import Project, Question, Response, User
from app.rate_limit import reset_rate_limits
from app.auth import get_current_user, get_current_user_optional


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

def create_user_and_client(github_id, username):
    db = SessionLocal()
    user = User(github_id=github_id, username=username)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()

    db2 = SessionLocal()
    user = db2.query(User).filter(User.id == user.id).first()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_user_optional] = lambda: user
    client = TestClient(app)
    client.cookies.set("critique_csrf", "response_test_token")
    client.headers["X-CSRF-Token"] = "response_test_token"
    return client, user


def test_owner_sees_suggestion_public_does_not(auth_client):
    """Test that owner sees suggestion but public response has no suggestion field."""
    reset_rate_limits()
    cleanup_database()

    # Create project using auth_client
    payload = {
        "project_data": {"title": "Privacy Test", "description": None, "url": None, "image_url": None},
        "question_data": {"text": "Test?"},
    }
    create_resp = auth_client.post("/api/projects/", json=payload)
    project_id = create_resp.json()["project"]["id"]

    # Submit response with suggestion
    response_payload = {
        "clarity": "very_clear",
        "would_use": "yes",
        "suggestion": "Owner should see this.",
    }

    saved = {
        get_current_user: app.dependency_overrides.pop(get_current_user, None),
        get_current_user_optional: app.dependency_overrides.pop(get_current_user_optional, None),
    }

    reviewer, user = create_user_and_client(222222, "reviewer")

    submit_resp = reviewer.post(f"/api/projects/{project_id}/responses", json=response_payload)
    assert submit_resp.status_code == 201

    for dep, mock in saved.items():
        if mock is None:
            app.dependency_overrides.pop(dep, None)
        else:
            app.dependency_overrides[dep] = mock

    # Owner gets responses (auth_client has get_current_user mocked as owner)
    response = auth_client.get(f"/api/projects/{project_id}/responses")
    data = response.json()
    assert len(data) == 1
    assert data[0]["suggestion"] == "Owner should see this."

    # Public (no auth) — no suggestion
    app.dependency_overrides.clear()
    public_client = TestClient(app)
    public_response = public_client.get(f"/api/projects/{project_id}/responses")
    public_data = public_response.json()
    assert len(public_data) == 1
    assert "suggestion" not in public_data[0]
    assert public_data[0]["clarity"] == "very_clear"

    cleanup_database()


def test_results_privacy(auth_client):
    """Test that results endpoint respects privacy."""
    reset_rate_limits()
    cleanup_database()

    # Create project
    payload = {
        "project_data": {"title": "Results Privacy", "description": None, "url": None, "image_url": None},
        "question_data": {"text": "Test?"},
    }
    create_resp = auth_client.post("/api/projects/", json=payload)
    project_id = create_resp.json()["project"]["id"]

    # Submit response with suggestion
    response_payload = {
        "clarity": "very_clear",
        "would_use": "yes",
        "suggestion": "Private written feedback.",
    }

    saved = {
        get_current_user: app.dependency_overrides.pop(get_current_user, None),
        get_current_user_optional: app.dependency_overrides.pop(get_current_user_optional, None),
    }

    reviewer, user = create_user_and_client(222222, "reviewer")
    reviewer.post(f"/api/projects/{project_id}/responses", json=response_payload)

    for dep, mock in saved.items():
        if mock is None:
            app.dependency_overrides.pop(dep, None)
        else:
            app.dependency_overrides[dep] = mock


    # Owner gets full results (auth_client is the owner)
    response = auth_client.get(f"/api/projects/{project_id}/results")
    data = response.json()
    assert data["is_owner"] == True
    assert len(data["responses"]) == 1
    assert data["responses"][0]["suggestion"] == "Private written feedback."

    # Public gets stats only
    app.dependency_overrides.clear()
    public_client = TestClient(app)
    public_response = public_client.get(f"/api/projects/{project_id}/results")
    public_data = public_response.json()
    assert public_data["is_owner"] == False
    assert public_data["responses"] == []
    assert public_data["stats"]["total"] == 1

    cleanup_database()
