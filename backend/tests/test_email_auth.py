"""Tests for passwordless email authentication.

Covers /auth/email/start and /auth/email/verify.

Design notes:
- No real Resend calls. _build_client is monkeypatched at the service seam.
- No real API key. settings.RESEND_API_KEY is temporarily set to a dummy value.
- Uses follow_redirects=False so cookies and Location headers are inspectable.
"""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db, SessionLocal
from app.models import User, EmailLoginToken
from app.config import settings
from app.csrf import generate_csrf_token, CSRF_COOKIE_NAME
from app import auth as auth_module


def _unique_email():
    return f"email_test_{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture
def client():
    """Plain test client with a CSRF cookie set."""
    init_db()
    c = TestClient(app, follow_redirects=False)
    token = generate_csrf_token()
    c.cookies.set(CSRF_COOKIE_NAME, token)
    c.headers["X-CSRF-Token"] = token
    return c


@pytest.fixture
def fake_email(monkeypatch):
    """Monkeypatch the Resend seam and set config values for the test."""
    sent = []
    class FakeEmails:
        @staticmethod
        def send(payload):
            sent.append(payload)
    monkeypatch.setattr("app.email._build_client", lambda: FakeEmails)
    monkeypatch.setattr(settings, "RESEND_API_KEY", "test_key_not_real")
    monkeypatch.setattr(settings, "EMAIL_FROM", "Critique <login@example.com>")
    return sent


@pytest.fixture(autouse=True)
def reset_cooldown():
    """Clear the per-email cooldown between tests."""
    auth_module._EMAIL_COOLDOWN.clear()
    yield
    auth_module._EMAIL_COOLDOWN.clear()


def _cleanup_user_by_email(email):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == email).first()
        if u:
            db.delete(u)
            db.commit()
    finally:
        db.close()


def _cleanup_tokens_by_email(email):
    db = SessionLocal()
    try:
        for row in db.query(EmailLoginToken).filter(EmailLoginToken.email == email).all():
            db.delete(row)
        db.commit()
    finally:
        db.close()


# ---------------- /auth/email/start ----------------

def test_start_valid_email_returns_ok_and_creates_token(client, fake_email):
    email = _unique_email()
    try:
        r = client.post("/auth/email/start", json={"email": email, "return_to": "/project/1?resume=feedback"})
        assert r.status_code == 200
        assert r.json() == {"ok": True}
        assert len(fake_email) == 1
        assert fake_email[0]["to"] == [email]

        db = SessionLocal()
        try:
            row = db.query(EmailLoginToken).filter(EmailLoginToken.email == email).first()
            assert row is not None
            assert len(row.token_hash) == 64
            assert row.used_at is None
            assert row.return_to == "/project/1?resume=feedback"
        finally:
            db.close()
    finally:
        _cleanup_tokens_by_email(email)


def test_start_malformed_email_returns_ok_but_no_token(client, fake_email):
    email = "not an email"
    try:
        r = client.post("/auth/email/start", json={"email": email})
        assert r.status_code == 200
        assert r.json() == {"ok": True}
        assert len(fake_email) == 0

        db = SessionLocal()
        try:
            row = db.query(EmailLoginToken).filter(EmailLoginToken.email == email.strip().lower()).first()
            assert row is None
        finally:
            db.close()
    finally:
        _cleanup_tokens_by_email(email.strip().lower())


def test_start_requires_csrf(fake_email):
    init_db()
    c = TestClient(app, follow_redirects=False)
    # No CSRF cookie, no CSRF header.
    r = c.post("/auth/email/start", json={"email": _unique_email()})
    assert r.status_code == 403


def test_start_unsafe_return_to_is_dropped(client, fake_email):
    email = _unique_email()
    try:
        r = client.post("/auth/email/start", json={"email": email, "return_to": "https://evil.com"})
        assert r.status_code == 200
        assert r.json() == {"ok": True}

        db = SessionLocal()
        try:
            row = db.query(EmailLoginToken).filter(EmailLoginToken.email == email).first()
            assert row is not None
            assert row.return_to is None
        finally:
            db.close()
    finally:
        _cleanup_tokens_by_email(email)


def test_start_anti_enumeration_existing_vs_new(client, fake_email):
    """Two calls â€” one for an email that has a user, one for an email that doesn't â€” return identical responses."""
    init_db()
    existing_email = _unique_email()
    new_email = _unique_email()

    db = SessionLocal()
    try:
        u = User(email=existing_email, username="email_" + uuid.uuid4().hex[:16])
        db.add(u)
        db.commit()
    finally:
        db.close()

    try:
        r1 = client.post("/auth/email/start", json={"email": existing_email})
        r2 = client.post("/auth/email/start", json={"email": new_email})
        assert r1.status_code == r2.status_code == 200
        assert r1.json() == r2.json() == {"ok": True}
    finally:
        _cleanup_tokens_by_email(existing_email)
        _cleanup_tokens_by_email(new_email)
        _cleanup_user_by_email(existing_email)


def test_start_raw_token_never_stored(client, fake_email):
    """Every token_hash in the DB is 64 hex chars, and none of them equal any raw token shape."""
    email = _unique_email()
    try:
        r = client.post("/auth/email/start", json={"email": email})
        assert r.status_code == 200

        db = SessionLocal()
        try:
            row = db.query(EmailLoginToken).filter(EmailLoginToken.email == email).first()
            assert row is not None
            # Hash length is fixed at 64 (sha256 hex digest)
            assert len(row.token_hash) == 64
            # Every char is hex
            int(row.token_hash, 16)
        finally:
            db.close()
    finally:
        _cleanup_tokens_by_email(email)


def test_start_cooldown_blocks_second_request_within_window(client, fake_email):
    email = _unique_email()
    try:
        r1 = client.post("/auth/email/start", json={"email": email})
        assert r1.status_code == 200
        assert len(fake_email) == 1

        r2 = client.post("/auth/email/start", json={"email": email})
        assert r2.status_code == 200
        assert r2.json() == {"ok": True}
        # Second request returned ok but did not send.
        assert len(fake_email) == 1

        db = SessionLocal()
        try:
            count = db.query(EmailLoginToken).filter(EmailLoginToken.email == email).count()
            # Only one token was created
            assert count == 1
        finally:
            db.close()
    finally:
        _cleanup_tokens_by_email(email)


def test_start_survives_email_send_failure(client, monkeypatch):
    """If the send helper raises, /start still returns ok."""
    email = _unique_email()

    def boom(*args, **kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr("app.auth.send_login_link", boom)
    monkeypatch.setattr(settings, "RESEND_API_KEY", "test_key_not_real")
    monkeypatch.setattr(settings, "EMAIL_FROM", "Critique <login@example.com>")

    try:
        r = client.post("/auth/email/start", json={"email": email})
        assert r.status_code == 200
        assert r.json() == {"ok": True}
    finally:
        _cleanup_tokens_by_email(email)


def test_start_no_token_in_response(client, fake_email):
    email = _unique_email()
    try:
        r = client.post("/auth/email/start", json={"email": email})
        assert r.status_code == 200
        body = r.text
        # The response must not contain a token_urlsafe-ish string
        assert "token" not in body.lower()
        assert len(body) < 100  # "{\"ok\":true}"
    finally:
        _cleanup_tokens_by_email(email)


# ---------------- /auth/email/verify ----------------

def _insert_token(email, minutes_valid=15, return_to=None, used=False):
    raw = "raw_" + uuid.uuid4().hex
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        row = EmailLoginToken(
            email=email,
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            created_at=now,
            expires_at=now + timedelta(minutes=minutes_valid),
            used_at=now if used else None,
            requester_ip_hash="0" * 64,
            return_to=return_to,
        )
        db.add(row)
        db.commit()
    finally:
        db.close()
    return raw


def test_verify_valid_token_creates_user_and_session(client):
    email = _unique_email()
    raw = _insert_token(email)
    try:
        r = client.get(f"/auth/email/verify?token={raw}")
        assert r.status_code in (302, 303, 307)
        # Session cookie set
        assert any(c.startswith("critique_session") or "critique_session" in c for c in r.headers.get_list("set-cookie"))
        # CSRF cookie set
        set_cookie = "; ".join(r.headers.get_list("set-cookie"))
        assert "critique_session" in set_cookie
        assert "critique_csrf" in set_cookie

        # User exists with synthetic username
        db = SessionLocal()
        try:
            u = db.query(User).filter(User.email == email).first()
            assert u is not None
            assert u.username.startswith("email_")
            assert len(u.username) == 22  # "email_" (6) + 16 hex
        finally:
            db.close()
    finally:
        _cleanup_tokens_by_email(email)
        _cleanup_user_by_email(email)


def test_verify_token_is_single_use(client):
    email = _unique_email()
    raw = _insert_token(email)
    try:
        r1 = client.get(f"/auth/email/verify?token={raw}")
        assert r1.status_code in (302, 303, 307)

        r2 = client.get(f"/auth/email/verify?token={raw}")
        # Second use redirects to the error path, not the resume path
        assert r2.status_code in (302, 303, 307)
        assert "error=email_link" in r2.headers["location"]
    finally:
        _cleanup_tokens_by_email(email)
        _cleanup_user_by_email(email)


def test_verify_expired_token_rejected(client):
    email = _unique_email()
    raw = _insert_token(email, minutes_valid=-5)  # expired 5 minutes ago
    try:
        r = client.get(f"/auth/email/verify?token={raw}")
        assert r.status_code in (302, 303, 307)
        assert "error=email_link" in r.headers["location"]

        db = SessionLocal()
        try:
            u = db.query(User).filter(User.email == email).first()
            assert u is None
        finally:
            db.close()
    finally:
        _cleanup_tokens_by_email(email)


def test_verify_invalid_token_rejected(client):
    r = client.get("/auth/email/verify?token=this_is_not_a_valid_token")
    assert r.status_code in (302, 303, 307)
    assert "error=email_link" in r.headers["location"]


def test_verify_same_email_returns_same_user(client):
    email = _unique_email()
    raw1 = _insert_token(email)
    try:
        r1 = client.get(f"/auth/email/verify?token={raw1}")
        assert r1.status_code in (302, 303, 307)

        db = SessionLocal()
        try:
            u1 = db.query(User).filter(User.email == email).first()
            assert u1 is not None
            uid = u1.id
        finally:
            db.close()

        # Second verification with a different raw token for the same email
        raw2 = _insert_token(email)
        c2 = TestClient(app, follow_redirects=False)
        r2 = c2.get(f"/auth/email/verify?token={raw2}")
        assert r2.status_code in (302, 303, 307)

        db = SessionLocal()
        try:
            u2 = db.query(User).filter(User.email == email).first()
            assert u2 is not None
            assert u2.id == uid  # same user
            # Only one user with this email
            count = db.query(User).filter(User.email == email).count()
            assert count == 1
        finally:
            db.close()
    finally:
        _cleanup_tokens_by_email(email)
        _cleanup_user_by_email(email)


def test_verify_respects_safe_return_to(client):
    email = _unique_email()
    raw = _insert_token(email, return_to="/project/42?resume=feedback")
    try:
        r = client.get(f"/auth/email/verify?token={raw}")
        assert r.status_code in (302, 303, 307)
        assert r.headers["location"] == "/project/42?resume=feedback"
    finally:
        _cleanup_tokens_by_email(email)
        _cleanup_user_by_email(email)


def test_verify_drops_unsafe_return_to_at_insert(client):
    """If the stored return_to is somehow unsafe, verify falls back to '/'."""
    email = _unique_email()
    raw = _insert_token(email, return_to="https://evil.com")
    try:
        r = client.get(f"/auth/email/verify?token={raw}")
        assert r.status_code in (302, 303, 307)
        assert r.headers["location"] == "/"
    finally:
        _cleanup_tokens_by_email(email)
        _cleanup_user_by_email(email)