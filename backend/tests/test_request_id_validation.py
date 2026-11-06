import re

from fastapi.testclient import TestClient

from app.main import app, _REQUEST_ID_RE

client = TestClient(app)


def test_valid_request_id_propagated():
    rid = "abc-123-XYZ"
    r = client.get("/health", headers={"X-Request-ID": rid})
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID") == rid


def test_missing_request_id_generated():
    r = client.get("/health")
    assert r.status_code == 200
    rid = r.headers.get("X-Request-ID")
    assert rid and _REQUEST_ID_RE.fullmatch(rid)


def test_empty_request_id_generated():
    r = client.get("/health", headers={"X-Request-ID": ""})
    rid = r.headers.get("X-Request-ID")
    assert rid and _REQUEST_ID_RE.fullmatch(rid)
    assert rid != ""


def test_oversized_request_id_generated():
    r = client.get("/health", headers={"X-Request-ID": "a" * 65})
    rid = r.headers.get("X-Request-ID")
    assert rid and _REQUEST_ID_RE.fullmatch(rid)
    assert len(rid) == 32


def test_newline_request_id_generated():
    r = client.get("/health", headers={"X-Request-ID": "abc\ndef"})
    rid = r.headers.get("X-Request-ID")
    assert rid and _REQUEST_ID_RE.fullmatch(rid)


def test_invalid_chars_request_id_generated():
    r = client.get("/health", headers={"X-Request-ID": "abc def!@#"})
    rid = r.headers.get("X-Request-ID")
    assert rid and _REQUEST_ID_RE.fullmatch(rid)


def test_generated_ids_are_32_hex():
    r = client.get("/health")
    rid = r.headers.get("X-Request-ID")
    assert re.fullmatch(r"[0-9a-f]{32}", rid)
