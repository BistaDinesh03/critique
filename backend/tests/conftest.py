import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, SessionLocal
from app.models import User
from app.auth import get_current_user
from app.csrf import generate_csrf_token, CSRF_COOKIE_NAME


@pytest.fixture
def auth_client():
    """Create a test client with authentication and CSRF bypassed."""
    init_db()
    db = SessionLocal()
    unique_suffix = uuid.uuid4().hex[:8]
    user = User(github_id=hash(unique_suffix) % 100000000, username=f"testuser_{unique_suffix}")
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()

    def mock_get_current_user():
        return user

    app.dependency_overrides[get_current_user] = mock_get_current_user
    client = TestClient(app)
    
    # Set CSRF cookie and capture token for header
    csrf_token = generate_csrf_token()
    client.cookies.set(CSRF_COOKIE_NAME, csrf_token)
    client.headers["X-CSRF-Token"] = csrf_token
    
    yield client
    app.dependency_overrides.clear()
