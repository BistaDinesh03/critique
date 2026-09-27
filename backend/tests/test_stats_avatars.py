"""Real, privacy-safe social proof for the homepage trust section.

`/api/stats` is the only source of the builder count and the builder avatars
shown on the homepage, so it must:

* report the real number of accounts (never a curated subset),
* include builders who signed up with email even though they have no avatar,
* never hand the page an avatar URL that is not plain https.

Unit tests cover the URL guard directly; the API tests check the wire contract.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal, init_db
from app.main import app
from app.models import User
from app.routes_stats import _safe_avatar_url

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

    from sqlalchemy import func

    real_total = db.query(func.count(User.id)).scalar()
    assert body["total_builders"] == real_total
    assert isinstance(body["total_projects"], int)


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
