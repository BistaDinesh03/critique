"""disableResponseForm must really disable the response form.

Regression for #238: the render harness used to fabricate any
getElementById target and return [] for querySelectorAll, so
`disableResponseForm()` was a silent no-op the suite could not observe.
These tests assert on the hydrated markup: every control in the form is
actually disabled after a settled submission.
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


def test_controls_really_exist_and_get_disabled_after_success(tmp_path):
    """The hydrated form has real input/textarea/button children."""
    fetch = {
        "/api/projects/1/responses": {"status": 201, "body": {}},
        "/api/projects/1": {"status": 200, "body": PROJECT},
    }
    calls = [
        *FILL_FORM,
        {"submitId": "response-form"},
        {
            "evaluate": (
                "document.getElementById('response-form')"
                ".querySelectorAll('input, textarea, button').length"
            ),
            "as": "controls_found",
        },
        {"evaluate": "document.getElementById('submit-btn').disabled", "as": "submit_disabled"},
        {
            "evaluate": (
                "document.getElementById('response-form')"
                ".querySelector('textarea').disabled"
            ),
            "as": "textarea_disabled",
        },
    ]
    result = run_harness(tmp_path, calls, fetch)

    assert result["values"]["controls_found"] >= 8, "hydration did not find the form controls"
    assert result["values"]["submit_disabled"] is True
    assert result["values"]["textarea_disabled"] is True


def test_controls_really_exist_and_get_disabled_after_409(tmp_path):
    """A duplicate answer still disables the form (the 409 path)."""
    fetch = {
        "/api/projects/1/responses": {"status": 409, "body": {"detail": "Already responded"}},
        "/api/projects/1": {"status": 200, "body": PROJECT},
    }
    calls = [
        *FILL_FORM,
        {"submitId": "response-form"},
        {"evaluate": "document.getElementById('submit-btn').disabled", "as": "submit_disabled"},
        {
            "evaluate": (
                "document.getElementById('response-form')"
                ".querySelector('textarea').disabled"
            ),
            "as": "textarea_disabled",
        },
    ]
    result = run_harness(tmp_path, calls, fetch)

    assert result["values"]["submit_disabled"] is True
    assert result["values"]["textarea_disabled"] is True
