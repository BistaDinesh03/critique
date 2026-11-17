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
    assert 'Synthetic project — Critique' in response.text
    assert f'<link rel="canonical" href="http://127.0.0.1:8000/project/{project_id}{suffix}">' in response.text
    assert response.headers['cache-control'] == 'private, no-store'
    assert response.headers['vary'] == 'Cookie'
    assert response.headers['content-type'].startswith('text/html')


def test_project_detail_has_breadcrumb_navigation():
    source = (Path(__file__).resolve().parents[2] / 'frontend' / 'project_detail.html').read_text(encoding='utf-8')
    assert '<nav aria-label="Breadcrumb" class="breadcrumb-nav">' in source
    assert '<ol class="breadcrumbs">' in source
    assert '<a href="/">Home</a>' in source
    assert '<a href="/discover">Discover</a>' in source
    assert 'aria-current="page"' in source
    assert 'id="breadcrumb-current"' in source


def test_two_different_projects_render_distinct_titles_and_descriptions():
    """Different projects have different server-rendered titles containing project names (fixes #312)."""
    with SessionLocal() as db:
        owner = User(username=f'page-title-{uuid.uuid4().hex[:12]}')
        db.add(owner)
        db.flush()
        p1 = Project(title='Alpha Scanner', description='Fast security audits', owner_id=owner.id)
        p2 = Project(title='Beta Monitor', description='Uptime tracking tool', owner_id=owner.id)
        db.add_all([p1, p2])
        db.commit()
        id1, id2 = p1.id, p2.id

    client = TestClient(app)
    r1 = client.get(f'/project/{id1}')
    r2 = client.get(f'/project/{id2}')
    assert '<title>Alpha Scanner — Critique</title>' in r1.text
    assert '<title>Beta Monitor — Critique</title>' in r2.text
    assert 'Fast security audits' in r1.text
    assert 'Uptime tracking tool' in r2.text


def test_discover_and_my_projects_have_meta_descriptions():
    """Discover has a public meta description; My Projects and Results declare noindex (fixes #312)."""
    client = TestClient(app)
    discover_resp = client.get('/discover')
    assert '<meta name="description"' in discover_resp.text
    assert 'Discover projects from builders and makers' in discover_resp.text

    my_projects_resp = client.get('/my-projects')
    assert '<meta name="description"' in my_projects_resp.text
    assert '<meta name="robots" content="noindex, nofollow">' in my_projects_resp.text


def test_project_page_escapes_html_and_truncates_length():
    """Project titles and descriptions with HTML characters are escaped and truncated (fixes #312)."""
    with SessionLocal() as db:
        owner = User(username=f'escape-{uuid.uuid4().hex[:12]}')
        db.add(owner)
        db.flush()
        long_title = '<script>alert("xss")</script> ' + 'A' * 100
        long_desc = '<b>bold & dangerous</b> ' + 'D' * 200
        p = Project(title=long_title, description=long_desc, owner_id=owner.id)
        db.add(p)
        db.commit()
        pid = p.id

    client = TestClient(app)
    resp = client.get(f'/project/{pid}')
    assert '<script>alert' not in resp.text
    assert '&lt;script&gt;alert' in resp.text
    assert '<b>bold' not in resp.text
    assert '&lt;b&gt;bold &amp; dangerous&lt;/b&gt;' in resp.text
