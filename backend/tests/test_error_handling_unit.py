"""Error handling regressions (no DOM / Node needed).

Covers backend surfaces that must never expose internal details or raw
exception text to production visitors.
"""

import asyncio
import json


def test_project_detail_never_renders_raw_exception_text():
    """No DOM write may concatenate an error's message into the page."""
    page = (
        __import__("pathlib").Path(__file__).resolve().parent.parent.parent
        / "frontend"
        / "project_detail.html"
    )
    source = page.read_text(encoding="utf-8")
    assert "'Network error' + e.message" not in source
    assert "textContent = 'Network error: ' + e.message" not in source


def test_unhandled_exception_handler_returns_generic_500():
    """The catch-all handler must not leak exception details."""
    from starlette.requests import Request

    from app import main

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/boom",
            "headers": [],
            "query_string": b"",
            "client": ("127.0.0.1", 1234),
            "server": ("test", 80),
            "root_path": "",
        }
    )
    exc = RuntimeError("secret: database credentials hunter2")
    response = asyncio.run(main.unhandled_exception_handler(request, exc))

    assert response.status_code == 500
    body = response.body.decode("utf-8")
    assert "hunter2" not in body
    assert json.loads(body) == {"detail": "Internal server error"}
