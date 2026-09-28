"""Query behaviour of the public project list -- the homepage's slowest call.

Wall-clock timing is unusable in CI (and would only measure SQLite), so the
optimisation target is asserted as *request behaviour*: how many round trips
the endpoint takes and what it writes. These bounds come from measuring
production (critique.page on Render free + Neon free), where the same reads
cost ~1200ms with nothing written, ~1436ms with one row written and ~2534ms
with six -- roughly 220ms per row written per read.

What must hold for every anonymous page load:

* one SELECT for the whole page: no ``count(*)`` pagination query and no
  per-project query;
* impressions for the projects actually shown are still recorded, in a single
  statement rather than one round trip per row;
* the response contract the frontend depends on is unchanged.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from app.database import SessionLocal, engine, init_db
from app.main import app
from app.models import Project, Question, User

client = TestClient(app)

LIST_URL = "/api/projects/?page=1&page_size=6"


@pytest.fixture
def sql():
    """Every statement issued while the body runs."""
    captured = []

    def _record(conn, cursor, statement, parameters, context, executemany):
        captured.append(
            {
                "sql": " ".join(statement.split()),
                "parameters": parameters,
                "executemany": executemany,
            }
        )

    event.listen(engine, "before_cursor_execute", _record)
    try:
        yield captured
    finally:
        event.remove(engine, "before_cursor_execute", _record)


@pytest.fixture
def seed_projects():
    """Create `count` projects with one active question each; remove them after."""
    init_db()
    db = SessionLocal()
    user_ids = []
    project_ids = []

    def _seed(count):
        user = User(username="list_budget_" + uuid.uuid4().hex[:8])
        db.add(user)
        db.commit()
        user_ids.append(user.id)
        for i in range(count):
            project = Project(
                title=f"List budget project {i}",
                description="A project used to measure query behaviour.",
                url="https://example.com/budget",
                owner_id=user.id,
                feedback_count=0,
                discover_impressions=0,
            )
            db.add(project)
            db.commit()
            project_ids.append(project.id)
            db.add(
                Question(
                    text=f"Is requirement {i} clear?",
                    project_id=project.id,
                    is_active=True,
                )
            )
            db.commit()
        return project_ids[:]

    try:
        yield _seed
    finally:
        db.query(Question).filter(
            Question.project_id.in_(project_ids)
        ).delete(synchronize_session=False)
        db.query(Project).filter(Project.id.in_(project_ids)).delete(
            synchronize_session=False
        )
        db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        db.commit()
        db.close()


def selects(statements):
    return [s["sql"] for s in statements if s["sql"].upper().startswith("SELECT")]


def impression_writes(statements):
    return [
        s
        for s in statements
        if s["sql"].upper().startswith("UPDATE") and "discover_impressions" in s["sql"]
    ]


def test_project_list_reads_the_database_once(sql, seed_projects):
    """One page, one read: no count(*) query and no per-project query."""
    seed_projects(5)
    sql.clear()

    response = client.get(LIST_URL)
    assert response.status_code == 200

    reads = selects(sql)
    assert len(reads) == 1, f"expected a single SELECT, got {len(reads)}: {reads}"


def test_project_list_read_count_does_not_grow_with_results(sql, seed_projects):
    """A bigger page must not cost more reads (no N+1)."""
    seed_projects(4)
    sql.clear()
    client.get("/api/projects/?page=1&page_size=6")
    few = len(selects(sql))

    seed_projects(20)
    sql.clear()
    client.get("/api/projects/?page=1&page_size=6")
    many = len(selects(sql))

    assert few == many == 1, f"read count scaled with rows: {few} vs {many}"


def test_impressions_are_recorded_in_a_single_statement(sql, seed_projects):
    """The write must be one statement, not one round trip per shown project."""
    project_ids = seed_projects(6)
    sql.clear()

    response = client.get("/api/projects/?page=1&page_size=50")
    assert response.status_code == 200
    shown = [item["id"] for item in response.json()["items"]]
    assert set(project_ids) <= set(shown), "seeded projects must be listed"

    writes = impression_writes(sql)
    assert len(writes) == 1, f"impressions took {len(writes)} statements: {writes}"
    assert not writes[0]["executemany"], (
        "impressions were written as a batch of individual row updates; "
        "incrementing in one statement avoids a round trip per project"
    )


def test_impressions_still_count_every_shown_project(seed_projects):
    """The optimisation must not lose the metric it was meant to preserve."""
    project_ids = seed_projects(3)

    def impressions():
        session = SessionLocal()
        try:
            return {
                project_id: session.query(Project)
                .filter(Project.id == project_id)
                .first()
                .discover_impressions
                for project_id in project_ids
            }
        finally:
            session.close()

    before = impressions()

    first = client.get("/api/projects/?page=1&page_size=50").json()
    shown = [item["id"] for item in first["items"]]

    after_first = impressions()
    for project_id in project_ids:
        if project_id in shown:
            assert after_first[project_id] == (before[project_id] or 0) + 1, (
                f"impression not counted for {project_id}"
            )

    client.get("/api/projects/?page=1&page_size=50")
    after_second = impressions()
    for project_id in project_ids:
        if project_id in shown:
            assert after_second[project_id] == (before[project_id] or 0) + 2, (
                f"second impression lost for {project_id}"
            )


def test_project_list_response_contract_is_unchanged(seed_projects):
    """The homepage, discover page and their tests read these exact keys."""
    seed_projects(2)
    body = client.get(LIST_URL).json()

    assert set(body) == {"items", "total", "page", "page_size", "total_pages"}
    assert body["page"] == 1
    assert body["page_size"] == 6
    assert isinstance(body["total_pages"], int) and body["total_pages"] >= 1
    assert body["total"] == len(body["items"])
    for item in body["items"]:
        assert {
            "id",
            "title",
            "description",
            "question_text",
            "response_count",
        } <= set(item)
