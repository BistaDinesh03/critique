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
from app.models import Project, Question, Response, User
from app.auth import get_current_user

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
    assert shown, "project list must not be empty"
    assert set(project_ids) <= set(shown), "seeded projects must be listed"

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


def test_project_list_response_count_with_drifted_question_id():
    """A project whose question id differs from its project id reports the correct count in Discover."""
    init_db()
    db = SessionLocal()
    user = User(username="drift_user_" + uuid.uuid4().hex[:8])
    db.add(user)
    db.commit()

    p1 = Project(
        title="Drift Project 1",
        description="First project",
        owner_id=user.id,
        feedback_count=0,
    )
    db.add(p1)
    db.commit()
    q1 = Question(text="Q1 text", project_id=p1.id, is_active=True)
    db.add(q1)
    db.commit()

    # Advance Question sequence with an inactive question to guarantee drift
    q_dummy = Question(text="Retired question", project_id=p1.id, is_active=False)
    db.add(q_dummy)
    db.commit()

    p2 = Project(
        title="Drift Project 2",
        description="Project with drifted question id",
        owner_id=user.id,
        feedback_count=2,
    )
    db.add(p2)
    db.commit()
    q2 = Question(text="Q2 text", project_id=p2.id, is_active=True)
    db.add(q2)
    db.commit()

    assert p2.id != q2.id, f"test requires drifted ids, got project.id={p2.id} == question.id={q2.id}"

    r1 = Response(
        clarity="very_clear",
        would_use="yes",
        suggestion="Great",
        question_id=q2.id,
        user_id=user.id,
        ip_hash="hash1",
    )
    r2 = Response(
        clarity="mostly_clear",
        would_use="maybe",
        suggestion="Good",
        question_id=q2.id,
        user_id=user.id,
        ip_hash="hash2",
    )
    db.add_all([r1, r2])
    db.commit()

    try:
        response = client.get("/api/projects/?page=1&page_size=50")
        assert response.status_code == 200
        items = {item["id"]: item for item in response.json()["items"]}
        assert p2.id in items, "Project 2 should be in Discover items"
        assert items[p2.id]["response_count"] == 2

        # Verify self-heal does not overwrite feedback_count with 0
        db.refresh(p2)
        assert p2.feedback_count == 2
    finally:
        db.query(Response).filter(Response.question_id.in_([q1.id, q_dummy.id, q2.id])).delete(synchronize_session=False)
        db.query(Question).filter(Question.id.in_([q1.id, q_dummy.id, q2.id])).delete(synchronize_session=False)
        db.query(Project).filter(Project.id.in_([p1.id, p2.id])).delete(synchronize_session=False)
        db.query(User).filter(User.id == user.id).delete(synchronize_session=False)
        db.commit()
        db.close()


def test_my_projects_response_count_with_drifted_question_id():
    """A project whose question id differs from its project id reports the correct count in My Projects."""
    init_db()
    db = SessionLocal()
    user = User(username="drift_owner_" + uuid.uuid4().hex[:8])
    db.add(user)
    db.commit()

    p1 = Project(
        title="Owner Project 1",
        description="First project",
        owner_id=user.id,
        feedback_count=0,
    )
    db.add(p1)
    db.commit()
    q1 = Question(text="Q1 text", project_id=p1.id, is_active=True)
    db.add(q1)
    db.commit()

    q_dummy = Question(text="Retired question", project_id=p1.id, is_active=False)
    db.add(q_dummy)
    db.commit()

    p2 = Project(
        title="Owner Project 2",
        description="Project with drifted question id",
        owner_id=user.id,
        feedback_count=3,
    )
    db.add(p2)
    db.commit()
    q2 = Question(text="Q2 text", project_id=p2.id, is_active=True)
    db.add(q2)
    db.commit()

    assert p2.id != q2.id, f"test requires drifted ids, got project.id={p2.id} == question.id={q2.id}"

    responses = [
        Response(
            clarity="very_clear",
            would_use="yes",
            suggestion=f"Suggestion {i}",
            question_id=q2.id,
            user_id=user.id,
            ip_hash=f"owner_hash_{i}",
        )
        for i in range(3)
    ]
    db.add_all(responses)
    db.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        response = client.get("/api/projects/my/list")
        assert response.status_code == 200
        items = {item["id"]: item for item in response.json()}
        assert p2.id in items, "Project 2 should be in My Projects items"
        assert items[p2.id]["response_count"] == 3
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        db.query(Response).filter(Response.question_id.in_([q1.id, q_dummy.id, q2.id])).delete(synchronize_session=False)
        db.query(Question).filter(Question.id.in_([q1.id, q_dummy.id, q2.id])).delete(synchronize_session=False)
        db.query(Project).filter(Project.id.in_([p1.id, p2.id])).delete(synchronize_session=False)
        db.query(User).filter(User.id == user.id).delete(synchronize_session=False)
        db.commit()
        db.close()


def test_discover_ranking_is_deterministic_and_pages_are_disjoint(seed_projects):
    """Multiple identical queries return identical ordering, and consecutive pages are disjoint."""
    seed_projects(12)

    # First request
    resp1 = client.get("/api/projects/?page=1&page_size=6").json()
    ids_page1_run1 = [p["id"] for p in resp1["items"]]

    # Second identical request must produce the exact same sequence
    resp2 = client.get("/api/projects/?page=1&page_size=6").json()
    ids_page1_run2 = [p["id"] for p in resp2["items"]]

    assert ids_page1_run1 == ids_page1_run2, "identical queries produced different ordering"

    # Page 2 request
    resp_page2 = client.get("/api/projects/?page=2&page_size=6").json()
    ids_page2 = [p["id"] for p in resp_page2["items"]]

    # Consecutive pages must be disjoint
    overlap = set(ids_page1_run1) & set(ids_page2)
    assert not overlap, f"page 1 and page 2 overlap on project ids: {overlap}"

