"""Feedback submission: which outcomes count as errors, and what comes next.

Production analytics showed 22 feedback submit attempts with 16 "errors" and
9 successes. The backend was reproduced locally: a signed-out visitor always
sends the CSRF token issued with the page, so the only status they can reach
is 401 -- the *designed* sign-in gate (``test_anonymous_submit_with_valid_csrf_gets_401_gate``).
The page used to report that gate as ``feedback_submit_error``, so the metric
counted every anonymous attempt as a failure and buried the real ones (403,
5xx, network).

These tests run the page's real JavaScript inside the Node rendering harness
and lock both sides of the fix:

* the 401 gate is *not* an error (it is already recorded as
  ``login_prompt_shown``, and the draft is kept for after login),
* genuine failures (CSRF, server error) still are,
* a successful submit stays on screen and offers the next real project
  instead of reloading the form away,
* reloading after a success shows the recorded state, never a form that the
  server would only reject with 409.

Requires ``node`` on PATH; the whole module is skipped when it is missing.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
HARNESS = Path(__file__).resolve().parent / "frontend_render_harness.js"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node is required to run the frontend rendering harness",
)

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

# Key order matters: the harness matches routes by first substring hit, and
# "/api/projects/1" would otherwise swallow ".../1/responses".
DETAIL_ROUTES = {
    "/api/projects/1/responses": {"status": 401, "body": {"detail": "Not authenticated"}},
    "/api/projects/1": {"status": 200, "body": PROJECT},
}

FILL_FORM = [
    {"checkInput": {"name": "clarity", "value": "very_clear"}},
    {"checkInput": {"name": "would_use", "value": "yes"}},
]


def run(tmp_path, page, calls, fetch=None, location="/", read=None):
    """Execute the page's scripts and return the harness result."""
    scenario = {
        "page": (FRONTEND_DIR / page).as_posix(),
        "calls": calls,
        "read": read or {"created": True},
        "fetch": fetch or {},
        "location": location,
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


def events(result, name):
    """Requests that tracked exactly `name` (not its longer relatives)."""
    marker = "event_name=" + name
    hits = []
    for r in result["requests"]:
        url = r["url"]
        i = url.find(marker)
        if i == -1:
            continue
        end = i + len(marker)
        if end == len(url) or url[end] == "&":
            hits.append(r)
    return hits


def submit(calls=()):
    return [*FILL_FORM, {"submitId": "response-form"}, *calls]


def help_links(result):
    """The 'Help another builder' link the page built, if any."""
    return [
        m
        for m in result["createdMeta"]
        if m.get("text") and "Help another builder" in str(m["text"])
    ]


# ---------------------------------------------------------------------------
# What is (and is not) a submit error
# ---------------------------------------------------------------------------


def test_anonymous_sign_in_gate_is_not_a_submit_error(tmp_path):
    """401 is the designed gate: login prompt, kept draft, no error event.

    Regression: counting this as feedback_submit_error inflated the error
    count with every anonymous attempt (the most common visitor).
    """
    result = run(
        tmp_path,
        "project_detail.html",
        submit(),
        fetch=DETAIL_ROUTES,
        location="/project/1",
    )

    assert len(events(result, "feedback_submit_attempt")) == 1
    assert len(events(result, "login_prompt_shown")) == 1
    assert events(result, "feedback_submit_error") == []

    # The gate itself: both methods, resume-aware return_to, kept draft.
    assert "Continue with GitHub" in " ".join(result["created"])
    assert "Continue with email" in " ".join(result["created"])
    login = [
        m
        for m in result["createdMeta"]
        if m.get("href") and str(m["href"]).startswith("/auth/login")
    ]
    assert login and "resume%3Dfeedback" in str(login[0]["href"])
    assert "critique_feedback_1" in result["storage"]["session"]


def test_csrf_failure_is_still_a_submit_error(tmp_path):
    """A broken session (403) is a real failure and must stay visible."""
    fetch = {
        "/api/projects/1/responses": {"status": 403, "body": {"detail": "CSRF failed"}},
        "/api/projects/1": {"status": 200, "body": PROJECT},
    }
    result = run(
        tmp_path,
        "project_detail.html",
        submit(),
        fetch=fetch,
        location="/project/1",
    )

    assert len(events(result, "feedback_submit_error")) == 1
    assert events(result, "feedback_submit") == []
    assert "Session expired. Please refresh." in result["ids"]["message"]


def test_server_error_is_still_a_submit_error(tmp_path):
    """A 5xx is a real failure and must stay visible."""
    fetch = {
        "/api/projects/1/responses": {"status": 500, "body": {"detail": "Boom on the server"}},
        "/api/projects/1": {"status": 200, "body": PROJECT},
    }
    result = run(
        tmp_path,
        "project_detail.html",
        submit(),
        fetch=fetch,
        location="/project/1",
    )

    assert len(events(result, "feedback_submit_error")) == 1
    assert events(result, "feedback_submit") == []
    assert "Boom on the server" in result["ids"]["message"]


# ---------------------------------------------------------------------------
# What comes after a successful submit (Phase 6)
# ---------------------------------------------------------------------------


def test_success_offers_the_next_real_project_and_keeps_the_confirmation(tmp_path):
    """After feedback: confirmation stays put and offers another real project."""
    fetch = {
        "/api/projects/1/responses": {"status": 201, "body": {}},
        "/api/projects/1": {"status": 200, "body": PROJECT},
        # The feed leads with the project just answered, then a real other one.
        "/api/projects/?": {
            "status": 200,
            "body": {
                "total": 2,
                "items": [
                    {"id": 1, "title": "Sentry bot"},
                    {"id": 2, "title": "Biohome"},
                ],
            },
        },
    }
    result = run(
        tmp_path,
        "project_detail.html",
        submit(),
        fetch=fetch,
        location="/project/1",
    )

    assert len(events(result, "feedback_submit")) == 1
    assert events(result, "feedback_submit_error") == []
    assert "Thank you! Your feedback has been submitted." in result["ids"]["message"]

    links = help_links(result)
    assert links, f"no next-step link built: {result['createdMeta']}"
    # Points at a *different* real project, never back at the answered one.
    assert links[0]["href"] == "/project/2"

    # The success state must not be wiped by a background reload.
    assert "critique_responded_1" in result["storage"]["session"]
    assert not any(r["url"] == "/api/projects/1" for r in result["requests"])


def test_next_step_falls_back_to_the_real_project_list(tmp_path):
    """If the feed does not answer, the action still lands on real projects."""
    fetch = {
        "/api/projects/1/responses": {"status": 201, "body": {}},
        "/api/projects/1": {"status": 200, "body": PROJECT},
        # /api/projects/? stays unmatched -> harness default 404.
    }
    result = run(
        tmp_path,
        "project_detail.html",
        submit(),
        fetch=fetch,
        location="/project/1",
    )

    assert len(events(result, "feedback_submit")) == 1
    links = help_links(result)
    assert links, f"no next-step link built: {result['createdMeta']}"
    assert links[0]["href"] == "/discover"


def test_reload_after_success_shows_recorded_state_not_the_form(tmp_path):
    """A same-session reload must not offer the form the server would 409."""
    fetch = {
        "/api/projects/1/responses": {"status": 401, "body": {"detail": "Not authenticated"}},
        "/api/projects/1": {"status": 200, "body": PROJECT},
        "/api/projects/?": {
            "status": 200,
            "body": {"total": 1, "items": [{"id": 2, "title": "Biohome"}]},
        },
    }
    result = run(
        tmp_path,
        "project_detail.html",
        [
            {"fn": "markFeedbackSubmitted", "args": []},
            {"fn": "renderProject", "args": [PROJECT, []]},
        ],
        fetch=fetch,
        location="/project/1",
    )

    thanks = result["ids"].get("feedback-thanks", "")
    assert "Thank you! Your feedback has been submitted." in thanks
    links = help_links(result)
    assert links, f"no next-step link built: {result['createdMeta']}"
    assert links[0]["href"] == "/project/2"
    # No submit was attempted on this render.
    assert events(result, "feedback_submit_attempt") == []
