"""Known HTML routes must distinguish absent projects from valid page shells."""
import uuid
from pathlib import Path

import pytest
from app.database import SessionLocal
from app.main import app
from app.models import Project, User
from fastapi.testclient import TestClient


@pytest.mark.parametrize('suffix', ['', '/results'])
@pytest.mark.parametrize('project_id', ['999999999', 'abc', str(2**100), str(-(2**100))])
def test_missing_or_invalid_project_page_returns_404(suffix, project_id):
    response = TestClient(app).get(f'/project/{project_id}{suffix}')
    assert response.status_code == 404


@pytest.mark.parametrize('path', [
    '/api/projects/{}', '/badge/{}.svg',
    '/api/projects/{}/responses', '/api/projects/{}/results',
])
@pytest.mark.parametrize('project_id', [
    '999999999', str(2**63 - 1), str(-(2**63)),
    str(2**63), str(2**100), str(-(2**63) - 1), str(-(2**100)),
])
def test_missing_or_out_of_range_project_api_and_badge_return_404(path, project_id):
    response = TestClient(app, raise_server_exceptions=False).get(path.format(project_id))
    assert response.status_code == 404
    assert response.json() == {'detail': 'Project not found'}


@pytest.mark.parametrize('suffix,filename', [('', 'project_detail.html'), ('/results', 'project_results.html')])
def test_existing_project_page_preserves_shell_and_cache_headers(suffix, filename):
    with SessionLocal() as db:
        owner = User(username=f'synthetic-page-{uuid.uuid4().hex[:12]}')
        db.add(owner)
        db.flush()
        project = Project(title='Synthetic project', owner_id=owner.id)
        db.add(project)
        db.commit()
        project_id = project.id
    response = TestClient(app).get(f'/project/{project_id}{suffix}')
    assert response.status_code == 200
    source = Path(__file__).resolve().parents[2] / 'frontend' / filename
    assert response.text == source.read_text(encoding='utf-8')
    assert response.headers['cache-control'] == 'private, no-store'
    assert response.headers['vary'] == 'Cookie'
    assert response.headers['content-type'].startswith('text/html')
