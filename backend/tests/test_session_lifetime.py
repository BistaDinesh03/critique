import uuid

import pytest
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from starlette.requests import Request

from app.auth import (
    SESSION_COOKIE_NAME,
    create_session_token,
    session_cookie_is_valid,
)
from app.config import settings
from app.database import SessionLocal
from app.main import app
from app.models import User


@pytest.fixture
def signed_session(monkeypatch):
    clock = [1_700_000_000]
    monkeypatch.setattr(TimestampSigner, "get_timestamp", lambda self: clock[0])
    identifier = uuid.uuid4().hex
    with SessionLocal() as db:
        user = User(
            username=f"session_{identifier}",
            email=f"{identifier}@example.com",
        )
        db.add(user)
        db.commit()
        token = create_session_token(user.id)
    return token, clock


@pytest.mark.parametrize("lifetime", [60, 86400 * 7, 86400 * 14])
@pytest.mark.parametrize(
    "offset, expected_status, expected_valid",
    [(-1, 200, True), (0, 200, True), (1, 401, False)],
)
def test_api_and_page_use_configured_session_lifetime(
    monkeypatch, signed_session, lifetime, offset, expected_status, expected_valid
):
    monkeypatch.setattr(settings, "SESSION_COOKIE_MAX_AGE", lifetime)
    token, clock = signed_session
    clock[0] += lifetime + offset

    with TestClient(app) as client:
        client.cookies.set(SESSION_COOKIE_NAME, token)
        check = client.get("/auth/check")
        page = client.get("/")

    assert page.status_code == 200
    assert (check.status_code, 'data-auth="in"' in page.text) == (
        expected_status,
        expected_valid,
    )


@pytest.mark.parametrize(
    "max_age, age, expected_valid",
    [(0, 1, False), (10, 10, True), (10, 11, False), (None, 61, False)],
)
def test_session_probe_resolves_configured_and_explicit_lifetimes(
    monkeypatch, signed_session, max_age, age, expected_valid
):
    monkeypatch.setattr(settings, "SESSION_COOKIE_MAX_AGE", 60)
    token, clock = signed_session
    clock[0] += age
    request = Request({
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"cookie", f"{SESSION_COOKIE_NAME}={token}".encode())],
    })

    assert session_cookie_is_valid(request, max_age=max_age) is expected_valid
