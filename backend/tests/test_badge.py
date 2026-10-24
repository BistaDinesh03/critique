"""Pin the contract of the badge SVG endpoint.

The badge is rendered inside other people's READMEs, so a regression in the
status code, the content type, the markup or the cache header would only show
up as a broken image on someone else's page. These tests follow the fixtures
and style of ``test_project_pages.py``.
"""
import uuid

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Project, Question, Response, User
from app.routes_badge import format_count


def _build_project(response_count=0, question_active=True):
    """Create a project with one question and ``response_count`` responses.

    Returns ``(project_id, question_id, user_id)`` so the caller can clean up
    exactly the rows this helper inserted.
    """
    unique = uuid.uuid4().hex[:12]
    with SessionLocal() as db:
        owner = User(github_id=int(uuid.uuid4().int % 100000000),
                     username=f"badge-owner-{unique}")
        db.add(owner)
        db.flush()

        project = Project(title=f"Badge project {unique}", owner_id=owner.id)
        db.add(project)
        db.flush()

        question = Question(text="Is this clear?",
                            project_id=project.id,
                            is_active=question_active)
        db.add(question)
        db.flush()

        db.bulk_save_objects([
            Response(clarity="very_clear",
                     would_use="yes",
                     question_id=question.id,
                     user_id=owner.id,
                     ip_hash=f"badge-{uuid.uuid4().hex}")
            for _ in range(response_count)
        ])
        db.commit()
        return project.id, question.id, owner.id


def _delete_project(project_id, question_id, user_id):
    with SessionLocal() as db:
        db.query(Response).filter(Response.question_id == question_id).delete()
        db.query(Question).filter(Question.id == question_id).delete()
        db.query(Project).filter(Project.id == project_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()


class _ProjectFixture:
    """Context manager wrapping ``_build_project`` / ``_delete_project``."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.project_id = None

    def __enter__(self):
        self.project_id, self.question_id, self.user_id = _build_project(**self.kwargs)
        return self.project_id

    def __exit__(self, *exc_info):
        _delete_project(self.project_id, self.question_id, self.user_id)
        return False


def badge_for_existing_project(**kwargs):
    return _ProjectFixture(**kwargs)


def get_badge(project_id):
    return TestClient(app).get(f"/badge/{project_id}.svg")


def test_existing_project_returns_svg():
    """GET /badge/{id}.svg must be a 200 with an SVG content type."""
    with badge_for_existing_project() as project_id:
        response = get_badge(project_id)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert "<svg" in response.text
    assert response.text.rstrip().endswith("</svg>")


def test_missing_project_returns_404():
    response = get_badge(999999999)

    assert response.status_code == 404


def test_badge_sends_no_cache_header():
    """Embedders must not get a cached copy; see issue #34 for any future change."""
    with badge_for_existing_project() as project_id:
        response = get_badge(project_id)

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-cache"


def test_badge_counts_responses_of_the_active_question():
    with badge_for_existing_project(response_count=3) as project_id:
        response = get_badge(project_id)

    assert response.status_code == 200
    assert ">3</text>" in response.text
    assert "reviews</text>" in response.text


def test_single_response_uses_the_singular_label():
    with badge_for_existing_project(response_count=1) as project_id:
        response = get_badge(project_id)

    assert response.status_code == 200
    assert ">1</text>" in response.text
    assert "review</text>" in response.text
    assert "reviews</text>" not in response.text


def test_inactive_question_reports_zero():
    """Only the newest *active* question is counted."""
    with badge_for_existing_project(response_count=2, question_active=False) as project_id:
        response = get_badge(project_id)

    assert response.status_code == 200
    assert ">0</text>" in response.text
    assert "reviews</text>" in response.text


def test_project_without_a_question_reports_zero():
    """A project with no question at all still renders a badge."""
    unique = uuid.uuid4().hex[:12]
    with SessionLocal() as db:
        owner = User(github_id=int(uuid.uuid4().int % 100000000),
                     username=f"badge-noq-{unique}")
        db.add(owner)
        db.flush()
        project = Project(title=f"No question {unique}", owner_id=owner.id)
        db.add(project)
        db.commit()
        project_id, user_id = project.id, owner.id

    try:
        response = get_badge(project_id)
    finally:
        with SessionLocal() as db:
            db.query(Project).filter(Project.id == project_id).delete()
            db.query(User).filter(User.id == user_id).delete()
            db.commit()

    assert response.status_code == 200
    assert ">0</text>" in response.text


def test_format_count_abbreviates_large_numbers():
    """1000 and above render as 1k+ so the badge keeps a fixed width."""
    assert format_count(0) == "0"
    assert format_count(1) == "1"
    assert format_count(999) == "999"
    assert format_count(1000) == "1k+"
    assert format_count(5000) == "1k+"
