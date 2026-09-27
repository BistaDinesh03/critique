"""Schema-level tests for email authentication additions.

These tests exercise the User.email column and the EmailLoginToken model
without touching routes, sessions, or the auth flow.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.database import init_db, SessionLocal
from app.models import User, EmailLoginToken


@pytest.fixture
def db():
    """Provide a fresh session against the test database."""
    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _unique_username(prefix: str = "schema_test_") -> str:
    import uuid
    return prefix + uuid.uuid4().hex[:12]


def _unique_email() -> str:
    import uuid
    return f"schema_test_{uuid.uuid4().hex[:12]}@example.com"


# ---------- User.email column ----------

def test_user_has_email_column():
    """User model exposes an email attribute."""
    assert hasattr(User, "email")
    assert User.email is not None


def test_user_without_email_still_works(db):
    """GitHub-style users (no email) can still be created."""
    user = User(github_id=hash("gh") % 10**9, username=_unique_username("gh_"))
    db.add(user)
    db.commit()
    db.refresh(user)
    try:
        assert user.id is not None
        assert user.email is None
    finally:
        db.delete(user)
        db.commit()


def test_user_with_email_can_be_created(db):
    """An email-only user can be created with email populated."""
    email = _unique_email()
    user = User(email=email, username=_unique_username("em_"))
    db.add(user)
    db.commit()
    db.refresh(user)
    try:
        assert user.id is not None
        assert user.email == email
        assert user.github_id is None
    finally:
        db.delete(user)
        db.commit()


def test_email_uniqueness_enforced(db):
    """Inserting two users with the same email fails at the DB level."""
    email = _unique_email()
    u1 = User(email=email, username=_unique_username("u1_"))
    db.add(u1)
    db.commit()
    try:
        u2 = User(email=email, username=_unique_username("u2_"))
        db.add(u2)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.delete(u1)
        db.commit()


def test_multiple_users_with_null_email_allowed(db):
    """Multiple users with NULL email coexist (unique allows multiple NULLs in SQLite)."""
    u1 = User(github_id=1_111_111, username=_unique_username("n1_"))
    u2 = User(github_id=2_222_222, username=_unique_username("n2_"))
    db.add(u1)
    db.add(u2)
    db.commit()
    try:
        assert u1.email is None
        assert u2.email is None
    finally:
        db.delete(u1)
        db.delete(u2)
        db.commit()


# ---------- EmailLoginToken model ----------

def test_email_login_token_can_be_created(db):
    """A token row can be inserted with all required fields."""
    token = EmailLoginToken(
        email=_unique_email(),
        token_hash="a" * 64,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        requester_ip_hash="b" * 64,
        return_to="/project/1?resume=feedback",
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    try:
        assert token.id is not None
        assert token.used_at is None
        assert token.return_to == "/project/1?resume=feedback"
        assert token.created_at is not None
        assert token.expires_at is not None
    finally:
        db.delete(token)
        db.commit()


def test_token_hash_uniqueness_enforced(db):
    """Two tokens cannot share the same hash."""
    shared_hash = "c" * 64
    t1 = EmailLoginToken(
        email=_unique_email(),
        token_hash=shared_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        requester_ip_hash="d" * 64,
    )
    db.add(t1)
    db.commit()
    try:
        t2 = EmailLoginToken(
            email=_unique_email(),
            token_hash=shared_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            requester_ip_hash="e" * 64,
        )
        db.add(t2)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.delete(t1)
        db.commit()


def test_return_to_is_optional(db):
    """return_to can be NULL."""
    token = EmailLoginToken(
        email=_unique_email(),
        token_hash="f" * 64,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        requester_ip_hash="g" * 64,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    try:
        assert token.return_to is None
    finally:
        db.delete(token)
        db.commit()


def test_used_at_can_be_set(db):
    """used_at can be populated and reflects the value written."""
    now = datetime.now(timezone.utc)
    token = EmailLoginToken(
        email=_unique_email(),
        token_hash="1" * 64,
        expires_at=now + timedelta(minutes=15),
        requester_ip_hash="2" * 64,
        used_at=now,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    try:
        assert token.used_at is not None
    finally:
        db.delete(token)
        db.commit()


def test_multiple_tokens_per_email_allowed(db):
    """The same email can request multiple tokens (e.g. after expiry)."""
    email = _unique_email()
    t1 = EmailLoginToken(
        email=email,
        token_hash="3" * 64,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        requester_ip_hash="4" * 64,
    )
    t2 = EmailLoginToken(
        email=email,
        token_hash="5" * 64,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        requester_ip_hash="4" * 64,
    )
    db.add(t1)
    db.add(t2)
    db.commit()
    try:
        count = (
            db.query(EmailLoginToken)
            .filter(EmailLoginToken.email == email)
            .count()
        )
        assert count == 2
    finally:
        db.delete(t1)
        db.delete(t2)
        db.commit()