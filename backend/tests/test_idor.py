from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import Project, Question, Response, User
from app.auth import get_current_user, get_current_user_optional
from app.rate_limit import reset_rate_limits


def cleanup_database():
    db = SessionLocal()
    try:
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
    client.cookies.set("critique_csrf", "idor_test_token")
    client.headers["X-CSRF-Token"] = "idor_test_token"
    return client, user


def create_project(client, title):
    payload = {
        "project_data": {"title": title, "description": "Test", "url": None, "image_url": None},
        "question_data": {"text": "Test question?"},
    }
    return client.post("/api/projects/", json=payload)


def submit_response(client, project_id):
    payload = {
        "clarity": "very_clear",
        "would_use": "yes",
        "suggestion": "PRIVATE_FEEDBACK",
    }
    return client.post(f"/api/projects/{project_id}/responses", json=payload)


def test_idor_results_user_a_cannot_access_user_b():
    reset_rate_limits()
    cleanup_database()

    client_a, user_a = create_user_and_client(111111, "idor_user_a")
    create_resp_a = create_project(client_a, "Project A")
    project_id_a = create_resp_a.json()["project"]["id"]

    app.dependency_overrides.clear()
    client_b, user_b = create_user_and_client(222222, "idor_user_b")
    create_resp_b = create_project(client_b, "Project B")
    project_id_b = create_resp_b.json()["project"]["id"]

    submit_response(client_b, project_id_a)

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: user_a
    app.dependency_overrides[get_current_user_optional] = lambda: user_a

    response = client_a.get(f"/api/projects/{project_id_b}/results")
    data = response.json()

    assert data["is_owner"] == False
    assert data["responses"] == []

    app.dependency_overrides.clear()
    cleanup_database()


def test_idor_results_owner_can_access_own():
    reset_rate_limits()
    cleanup_database()

    client_a, user_a = create_user_and_client(333333, "idor_owner_test")
    create_resp = create_project(client_a, "Owner Project")
    project_id = create_resp.json()["project"]["id"]
    submit_response(client_a, project_id)

    response = client_a.get(f"/api/projects/{project_id}/results")
    data = response.json()

    assert data["is_owner"] == True
    assert len(data["responses"]) == 1
    assert data["responses"][0]["suggestion"] == "PRIVATE_FEEDBACK"

    app.dependency_overrides.clear()
    cleanup_database()


def test_idor_responses_non_owner_sees_no_suggestion():
    reset_rate_limits()
    cleanup_database()

    # User A creates project
    client_a, user_a = create_user_and_client(444444, "idor_resp_a")
    create_resp_a = create_project(client_a, "A Project")
    project_id_a = create_resp_a.json()["project"]["id"]

    # User B submits feedback to A's project with private suggestion
    app.dependency_overrides.clear()
    client_b, user_b = create_user_and_client(555555, "idor_resp_b")
    submit_response(client_b, project_id_a)

    # User B (non-owner) views responses to A's project
    # B is authenticated but not the owner
    response = client_b.get(f"/api/projects/{project_id_a}/responses")
    data = response.json()

    # B should see public response data but NOT the suggestion
    assert len(data) == 1
    assert "suggestion" not in data[0]
    assert data[0]["clarity"] == "very_clear"

    app.dependency_overrides.clear()
    cleanup_database()


def test_idor_x_owner_header_cannot_bypass():
    reset_rate_limits()
    cleanup_database()

    client_a, user_a = create_user_and_client(666666, "idor_header_a")
    create_resp = create_project(client_a, "Header Test")
    project_id = create_resp.json()["project"]["id"]
    submit_response(client_a, project_id)

    app.dependency_overrides.clear()
    client_b, user_b = create_user_and_client(777777, "idor_header_b")

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: user_b
    app.dependency_overrides[get_current_user_optional] = lambda: user_b

    response = client_b.get(
        f"/api/projects/{project_id}/results",
        headers={"X-Owner-ID": str(user_a.id)},
    )
    data = response.json()

    assert data["is_owner"] == False
    assert data["responses"] == []

    app.dependency_overrides.clear()
    cleanup_database()


def test_idor_unauthenticated_gets_public_only():
    reset_rate_limits()
    cleanup_database()

    client_a, user_a = create_user_and_client(888888, "idor_unauth_test")
    create_resp = create_project(client_a, "Public Test")
    project_id = create_resp.json()["project"]["id"]
    submit_response(client_a, project_id)

    app.dependency_overrides.clear()
    public_client = TestClient(app)

    response = public_client.get(f"/api/projects/{project_id}/results")
    data = response.json()

    assert data["is_owner"] == False
    assert data["responses"] == []
    assert data["stats"]["total"] == 1

    cleanup_database()
