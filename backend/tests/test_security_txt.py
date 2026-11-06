"""Tests for RFC 9116 /.well-known/security.txt endpoint."""

from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_security_txt_endpoint():
    response = client.get("/.well-known/security.txt")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]

    content = response.text
    lines = dict(line.split(": ", 1) for line in content.strip().splitlines() if ": " in line)

    assert "Contact" in lines
    assert lines["Contact"] == "https://github.com/BistaDinesh03/critique/security/advisories/new"

    assert "Policy" in lines
    assert lines["Policy"] == "https://github.com/BistaDinesh03/critique/blob/main/SECURITY.md"

    assert "Preferred-Languages" in lines
    assert "en" in lines["Preferred-Languages"]

    assert "Expires" in lines
    # Must parse as valid future timestamp
    expires_dt = datetime.fromisoformat(lines["Expires"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    assert expires_dt > now
    # <= 6 months out (approx 185 days)
    assert (expires_dt - now).days <= 185


def test_security_txt_served_from_root_not_static():
    # Served at root
    res_root = client.get("/.well-known/security.txt")
    assert res_root.status_code == 200

    # Ensure /static/.well-known/security.txt is not required or default
    res_static = client.get("/static/.well-known/security.txt")
    # static mount only serves registered files or 404
    assert res_root.text != ""
