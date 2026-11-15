"""Error handling regressions (frontend harness).

Covers the #296-class bug: raw browser exception text must never be
rendered into the DOM, and the draft must survive a network failure.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
HARNESS = Path(__file__).resolve().parent / "frontend_render_harness.js"
PAGE = FRONTEND_DIR / "project_detail.html"

pytestmark = [
    pytest.mark.frontend_render,
    pytest.mark.skipif(
        shutil.which("node") is None,
        reason="node is required to run the frontend rendering harness",
    ),
]

PROJECT = {
    "project": {
        "id": 1,
        "title": "Sentry bot",
        "description": "Watches your logs",
        "image_url": None,
        "url": None,
        "response_count": 3,
    },
    "question": {
        "id": 1,
        "text": "Is the alerting clear enough?",
        "is_active": True,
        "project_id": 1,
    },
}

FILL_FORM = [
    {"checkInput": {"name": "clarity", "value": "very_clear"}},
    {"checkInput": {"name": "would_use", "value": "yes"}},
]


def run_harness(tmp_path, calls, fetch):
    scenario = {
        "page": PAGE.as_posix(),
        "calls": calls,
        "read": {"created": True},
        "fetch": fetch,
        "location": "/project/1",
    }
    scenario_file = tmp_path / "scenario.json"
    scenario_file.write_text(json.dumps(scenario), encoding="utf-8")
    proc = subprocess.run(
        ["node", str(HARNESS), str(scenario_file)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert proc.returncode == 0, f"harness crashed:\n{proc.stderr}"
    result = json.loads(proc.stdout)
    assert result["errors"] == [], f"page script errors: {result['errors']}"
    return result


def test_network_failure_uses_stable_copy_and_saves_draft(tmp_path):
    """A refused fetch shows the friendly message, never e.message."""
    fetch = {
        "/api/projects/1/responses": {
            "status": 0,
            "networkError": True,
            "message": "Failed to fetch",
            "body": {},
        },
        "/api/projects/1": {"status": 200, "body": PROJECT},
    }
    calls = [*FILL_FORM, {"submitId": "response-form"}]
    result = run_harness(tmp_path, calls, fetch)

    message = result["ids"]["message"]
    assert "Network error." in message
    assert "Failed to fetch" not in message
    # The draft survives a network failure: the page restores it on the next
    # visit (issue #296).
    assert "critique_feedback_1" in result["storage"]["session"]
