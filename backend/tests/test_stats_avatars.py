"""Real, privacy-safe social proof for the homepage trust section.

`/api/stats` is the only source of the builder count, the recent-builder
avatars and the named public members shown on the homepage, so it must:

* report the real number of accounts (never a curated subset),
* include builders who signed up with email even though they have no avatar,
* never hand the page an avatar URL that is not plain https,
* expose a named "public_members" list containing only real, displayable
  profiles (a public username, a public avatar, and at least one project).

Unit tests cover the URL guard directly; the API tests check the wire contract.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func

from app.database import SessionLocal, init_db
from app.main import app
from app.models import Project, User
from app.routes_stats import PUBLIC_MEMBER_LIMIT, _safe_avatar_url

client = TestClient(app)


@pytest.fixture
def db():
    """Fresh session against the shared test database."""
    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _unique_username(prefix):
    return prefix + uuid.uuid4().hex[:12]


def _unique_github_id():
    return uuid.uuid4().int % 1_000_000_000 + 100_000_000


# ---------------------------------------------------------------------------
# Avatar URL guard
# ---------------------------------------------------------------------------


def test_safe_avatar_url_returns_plain_https_unchanged():
    url = "https://avatars.githubusercontent.com/u/123?v=4"
    assert _safe_avatar_url(url) == url


@pytest.mark.parametrize(
    "unsafe",
    [
        "javascript:alert(1)",
        "JaVaScRiPt:alert(1)",
        "http://evil.example/a.png",
        "//evil.example/a.png",
        "data:image/svg+xml,<svg onload=alert(1)>",
        "https://user:pass@evil.example/a.png",
        "https://evil.example/a.png\nonerror=alert(1)",
        "",
        "x" * 501,
        None,
        123,
        {"url": "https://example.com"},
    ],
)
def test_safe_avatar_url_rejects_anything_that_is_not_plain_https(unsafe):
    assert _safe_avatar_url(unsafe) is None


# ---------------------------------------------------------------------------
# Wire contract
# ---------------------------------------------------------------------------


def test_stats_reports_the_real_builder_count(db):
    response = client.get("/api/stats")
    assert response.status_code == 200
    body = response.json()

    real_total = db.query(func.count(User.id)).scalar()
    assert body["total_builders"] == real_total
    assert isinstance(body["total_projects"], int)
    assert isinstance(body["total_questions"], int)
    assert isinstance(body["total_responses"], int)


def test_stats_includes_a_builder_who_has_no_avatar(db):
    """Email sign-ins have avatar_url NULL but are still real builders."""
    email_user = User(username=_unique_username("email_stats_"))
    gh_user = User(
        github_id=_unique_github_id(),
        username=_unique_username("gh_stats_"),
        avatar_url="https://avatars.githubusercontent.com/u/99?v=4",
    )
    db.add_all([email_user, gh_user])
    db.commit()
    try:
        response = client.get("/api/stats")
        builders = response.json()["builders"]
        by_name = {b["username"]: b for b in builders}

        assert email_user.username in by_name, "avatar-less builder was dropped"
        assert by_name[email_user.username]["avatar_url"] is None
        assert by_name[gh_user.username][
            "avatar_url"
        ] == "https://avatars.githubusercontent.com/u/99?v=4"
    finally:
        db.delete(email_user)
        db.delete(gh_user)
        db.commit()


def test_stats_never_returns_an_unsafe_stored_avatar(db):
    unsafe_user = User(
        username=_unique_username("unsafe_stats_"),
        avatar_url="javascript:alert(1)",
    )
    db.add(unsafe_user)
    db.commit()
    try:
        response = client.get("/api/stats")
        for builder in response.json()["builders"]:
            if builder["username"] == unsafe_user.username:
                assert builder["avatar_url"] is None
                break
        else:
            # The builder must still be present (only the URL is withheld).
            pytest.fail("builder with an unsafe avatar_url disappeared from /api/stats")
    finally:
        db.delete(unsafe_user)
        db.commit()


def test_stats_avatar_list_never_claims_more_users_than_exist(db):
    """The avatar row may show a subset of builders, never a larger claim."""
    users = [User(username=_unique_username("row_stats_")) for _ in range(6)]
    db.add_all(users)
    db.commit()
    try:
        response = client.get("/api/stats")
        body = response.json()

        real_total = db.query(func.count(User.id)).scalar()
        assert body["total_builders"] == real_total
        assert 0 < len(body["builders"]) <= body["total_builders"]
        # The recent-builders list stays small; the homepage never renders a
        # headcount, it renders named members from `public_members`.
        assert len(body["builders"]) <= 4
        assert "@" not in response.text, "an email address reached /api/stats"
        for builder in body["builders"]:
            assert set(builder) == {"username", "avatar_url"}, builder
    finally:
        for user in users:
            db.delete(user)
        db.commit()


# ---------------------------------------------------------------------------
# Named public members (the homepage community row)
# ---------------------------------------------------------------------------


def test_public_members_are_real_profile_photos_of_project_owners(db):
    owner = User(
        username=_unique_username("member_"),
        avatar_url="https://avatars.githubusercontent.com/u/77?v=4",
    )
    without_project = User(
        username=_unique_username("noshow_"),
        avatar_url="https://avatars.githubusercontent.com/u/78?v=4",
    )
    email_only = User(username=_unique_username("email_member_"), avatar_url=None)
    db.add_all([owner, without_project, email_only])
    db.commit()
    project = Project(title="Member row fixture", owner_id=owner.id)
    db.add(project)
    db.commit()
    try:
        members = client.get("/api/stats").json()["public_members"]
        by_name = {m["username"]: m for m in members}

        assert by_name[owner.username]["avatar_url"] == (
            "https://avatars.githubusercontent.com/u/77?v=4"
        )
        assert without_project.username not in by_name, "a non-owner was shown"
        assert email_only.username not in by_name, "an email signup was shown"
        for member in members:
            assert set(member) == {"username", "avatar_url"}, member
            assert member["username"].startswith("email_") is False
    finally:
        db.delete(project)
        db.delete(owner)
        db.delete(without_project)
        db.delete(email_only)
        db.commit()


def test_public_members_never_include_an_unsafe_avatar(db):
    owner = User(
        username=_unique_username("unsafe_member_"),
        avatar_url="javascript:alert(1)",
    )
    db.add(owner)
    db.commit()
    project = Project(title="Unsafe avatar fixture", owner_id=owner.id)
    db.add(project)
    db.commit()
    try:
        members = client.get("/api/stats").json()["public_members"]
        assert owner.username not in {m["username"] for m in members}
    finally:
        db.delete(project)
        db.delete(owner)
        db.commit()


def test_public_members_are_capped(db):
    owners = [
        User(
            username=_unique_username("cap_"),
            avatar_url=f"https://avatars.githubusercontent.com/u/{i}?v=4",
        )
        for i in range(PUBLIC_MEMBER_LIMIT + 3)
    ]
    db.add_all(owners)
    db.commit()
    projects = [Project(title="Cap fixture", owner_id=u.id) for u in owners]
    db.add_all(projects)
    db.commit()
    try:
        members = client.get("/api/stats").json()["public_members"]
        assert 0 < len(members) <= PUBLIC_MEMBER_LIMIT
    finally:
        for project in projects:
            db.delete(project)
        for user in owners:
            db.delete(user)
        db.commit()
