"""Current-page markers in the HTML actually served by each main route."""
from html.parser import HTMLParser
import uuid

import pytest
from fastapi.testclient import TestClient
from app.database import SessionLocal
from app.main import app
from app.models import Project, User


class NavbarLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_header = False
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'header' and 'navbar' in attrs.get('class', '').split():
            self.in_header = True
        if self.in_header and tag == 'a':
            self.links.append(attrs)

    def handle_endtag(self, tag):
        if tag == 'header':
            self.in_header = False


@pytest.mark.parametrize('path,expected', [
    ('/', '/'), ('/discover', '/discover'), ('/my-projects', '/my-projects'),
    ('/project/{id}', None), ('/project/{id}/results', None),
])
def test_served_nav_marks_only_the_current_destination(path, expected):
    project_id = owner_id = None
    try:
        if '{id}' in path:
            with SessionLocal() as db:
                owner = User(username=f'nav-{uuid.uuid4().hex}')
                db.add(owner)
                db.flush()
                project = Project(title='Synthetic nav project', owner_id=owner.id)
                db.add(project)
                db.commit()
                project_id, owner_id = project.id, owner.id
            path = path.format(id=project_id)
        response = TestClient(app).get(path)
        assert response.status_code == 200
        navbar = NavbarLinks()
        navbar.feed(response.text)
        assert navbar.links, 'the rendered page must contain navigation links'
        current = [link['href'] for link in navbar.links if link.get('aria-current') == 'page']
        assert current == ([] if expected is None else [expected])
    finally:
        if project_id is not None:
            with SessionLocal() as db:
                db.query(Project).filter(Project.id == project_id).delete()
                db.query(User).filter(User.id == owner_id).delete()
                db.commit()
