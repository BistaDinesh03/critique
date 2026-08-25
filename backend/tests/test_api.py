from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, SessionLocal
from app.models import Project, Question, Response, User

client = TestClient(app)


def setup_function():
    """Initialize database before each test."""
    init_db()


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


def create_test_project(title="Akiya Scout", question_text="Can you understand what this website does within 10 seconds?"):
    """Helper to create a test project via API."""
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


def test_create_project_with_question():
    """Test creating a project with a question via API."""
    cleanup_database()

    response = create_test_project()

    assert response.status_code == 201
    data = response.json()
    assert data["project"]["title"] == "Akiya Scout"
    assert data["question"]["text"] == "Can you understand what this website does within 10 seconds?"
    assert data["question"]["is_active"] == True

    cleanup_database()


def test_list_projects_with_pagination():
    """Test listing projects with pagination."""
    cleanup_database()

    # Create 3 test projects
    create_test_project(title="Project One")
    create_test_project(title="Project Two")
    create_test_project(title="Project Three")

    # List with page_size=2
    response = client.get("/api/projects/?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] == 2
    assert len(data["items"]) == 2
    # Items should have question_text and response_count
    assert data["items"][0]["question_text"] is not None
    assert data["items"][0]["response_count"] == 0

    # Get page 2
    response = client.get("/api/projects/?page=2&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1

    cleanup_database()


def test_get_project_with_question():
    """Test getting a project with its active question via API."""
    cleanup_database()

    create_response = create_test_project()
    project_id = create_response.json()["project"]["id"]

    response = client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["project"]["id"] == project_id
    assert data["project"]["title"] == "Akiya Scout"
    assert data["question"]["text"] == "Can you understand what this website does within 10 seconds?"

    cleanup_database()


def test_validation_rejects_empty_title():
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

    response = client.post("/api/projects/", json=payload)
    assert response.status_code == 422

    cleanup_database()


def test_pagination_rejects_invalid_page():
    """Test that page=0 is rejected."""
    cleanup_database()

    response = client.get("/api/projects/?page=0")
    assert response.status_code == 422

    cleanup_database()
