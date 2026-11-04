"""Breadcrumb navigation tests for project detail view."""
from pathlib import Path
import uuid
from app.database import SessionLocal
from app.main import app
from app.models import Project, User
from fastapi.testclient import TestClient


def test_project_detail_html_contains_breadcrumb_navigation():
    html_path = Path(__file__).resolve().parents[2] / 'frontend' / 'project_detail.html'
    html = html_path.read_text(encoding='utf-8')
    assert 'aria-label="Breadcrumb"' in html
    assert 'class="breadcrumb-nav"' in html
    assert 'href="/" class="breadcrumb-link">Home</a>' in html
    assert 'href="/discover" class="breadcrumb-link">Discover</a>' in html
    assert 'id="breadcrumb-title"' in html
    assert 'aria-current="page"' in html


def test_project_detail_route_serves_breadcrumb_navigation():
    with SessionLocal() as db:
        owner = User(username=f'breadcrumb-test-{uuid.uuid4().hex[:8]}')
        db.add(owner)
        db.flush()
        project = Project(title='Breadcrumb Test Project', owner_id=owner.id)
        db.add(project)
        db.commit()
        project_id = project.id

    client = TestClient(app)
    response = client.get(f'/project/{project_id}')
    assert response.status_code == 200
    assert 'aria-label="Breadcrumb"' in response.text
    assert 'id="breadcrumb-title"' in response.text
