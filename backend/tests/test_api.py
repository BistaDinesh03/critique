from app.database import init_db, SessionLocal
from app.models import Project, Question, Response, User


def cleanup_database():
    """Remove test data from database."""
    db = SessionLocal()
    try:
        db.query(Response).delete()
        db.query(Question).delete()
        db.query(Project).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


def create_test_project(client, title="Akiya Scout", question_text="Can you understand what this website does within 10 seconds?"):
    """Helper to create a test project via authenticated client."""
    payload = {
        "project_data": {
            "title": title,
            "description": "Find abandoned houses in Japan",
            "url": "https://akiya-scout.example.com",
            "image_url": None,
        },
        "question_data": {
            "text": question_text,
        },
    }
    return client.post("/api/projects/", json=payload)


def test_create_project_with_question(auth_client):
    """Test creating a project with a question via API."""
    cleanup_database()
    response = create_test_project(auth_client)
    assert response.status_code == 201
    data = response.json()
    assert data["project"]["title"] == "Akiya Scout"
    assert data["question"]["text"] == "Can you understand what this website does within 10 seconds?"
    assert data["question"]["is_active"] == True
    cleanup_database()


def test_list_projects_with_pagination(auth_client):
    """Test visible projects and metadata across multiple pages."""
    from app.auth import get_current_user_optional

    cleanup_database()
    current_user = __import__("app.main", fromlist=["app"]).app.dependency_overrides[
        get_current_user_optional
    ]()
    db = SessionLocal()
    project_ids = []
    try:
        owners = []
        for index in range(5):
            owner = User(username=f"pagination_owner_{index}")
            db.add(owner)
            db.commit()
            db.refresh(owner)
            if owner.id != current_user.id:
                owners.append(owner)
        for index, owner in enumerate(owners[:4]):
            project = Project(
                title=f"Pagination Project {index + 1}",
                description="Visible project for pagination coverage",
                url=f"https://example.com/{index + 1}",
                owner_id=owner.id,
                feedback_count=0,
                discover_impressions=0,
            )
            db.add(project)
            db.commit()
            db.refresh(project)
            project_ids.append(project.id)
            db.add(Question(text=f"Question {index + 1}?", project_id=project.id, is_active=True))
            db.commit()

        first = auth_client.get("/api/projects/?page=1&page_size=2")
        second = auth_client.get("/api/projects/?page=2&page_size=2")
        assert first.status_code == second.status_code == 200
        first_data, second_data = first.json(), second.json()
        first_titles = {item["title"] for item in first_data["items"]}
        second_titles = {item["title"] for item in second_data["items"]}
        expected_titles = {f"Pagination Project {index}" for index in range(1, 5)}
        assert len(first_titles) == len(second_titles) == 2
        assert first_titles | second_titles == expected_titles
        assert first_data["total"] == len(first_data["items"]) == 2
        assert second_data["total"] == len(second_data["items"]) == 2
        assert first_data["page"] == 1 and second_data["page"] == 2
        assert first_data["page_size"] == second_data["page_size"] == 2
        assert first_data["total_pages"] == second_data["total_pages"] == 2
        assert set(item["id"] for item in first_data["items"]).isdisjoint(
            item["id"] for item in second_data["items"]
        )
    finally:
        db.close()
        cleanup_database()


def test_get_project_with_question(auth_client):
    """Test getting a project with its active question via API."""
    cleanup_database()
    create_response = create_test_project(auth_client)
    project_id = create_response.json()["project"]["id"]

    response = auth_client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["project"]["id"] == project_id
    assert data["project"]["title"] == "Akiya Scout"
    assert data["question"]["text"] == "Can you understand what this website does within 10 seconds?"
    cleanup_database()


def test_validation_rejects_empty_title(auth_client):
    """Test that empty title is rejected."""
    cleanup_database()
    payload = {
        "project_data": {
            "title": "",
            "description": "Test",
            "url": "https://example.com",
            "image_url": None,
        },
        "question_data": {
            "text": "Test question?",
        },
    }
    response = auth_client.post("/api/projects/", json=payload)
    assert response.status_code == 422
    cleanup_database()


def test_pagination_rejects_invalid_page(auth_client):
    """Test that page=0 is rejected."""
    cleanup_database()
    response = auth_client.get("/api/projects/?page=0")
    assert response.status_code == 422
    cleanup_database()


def test_unauthenticated_create_project():
    """Test that unauthenticated project creation is rejected."""
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    payload = {
        "project_data": {
            "title": "Unauthorized",
            "description": "Should fail",
            "url": None,
            "image_url": None,
        },
        "question_data": {
            "text": "Should this fail?",
        },
    }
    response = client.post("/api/projects/", json=payload)
    assert response.status_code == 401
