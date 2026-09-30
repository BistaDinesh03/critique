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

The feedback pass then tightened the flow around that gate: the gate reads as
the next step of the submission (not a wall in front of one), the draft comes
back field for field, a visitor who signs in has their finished answer sent
without pressing the same button twice, a duplicate answer is a calm
completed state instead of a red error, and the sign-in events fire only when
the page really was returned by an authentication.

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


# ---------------------------------------------------------------------------
# The gate reads as the middle of the submission, not a wall in front of it
# ---------------------------------------------------------------------------


def test_sign_in_gate_reads_as_the_next_step(tmp_path):
    """Phase 2: ready -> one sign-in step -> your feedback is saved.

    Regression: the gate sat under a live "Submit feedback" button that could
    only ever answer 401, so visitors pressed it repeatedly while their
    answer was already written out below.
    """
    result = run(
        tmp_path,
        "project_detail.html",
        submit(
            [
                {
                    "evaluate": "document.getElementById('submit-btn').disabled",
                    "as": "submit_disabled",
                }
            ]
        ),
        fetch=DETAIL_ROUTES,
        location="/project/1",
    )
    html = " ".join(result["created"])

    assert "Your feedback is ready." in html
    assert "One quick step: sign in so we can send it to the builder." in html
    assert "Your feedback is saved." in html
    assert "Continue with GitHub" in html
    assert "Continue with email" in html
    # Inline inside the form: a narrow screen never has to scroll a dialog up.
    assert "modal-backdrop" not in html
    # The button that can only answer 401 stops pretending otherwise.
    assert result["values"]["submit_disabled"] is True
    # And the answers themselves are kept for after the sign-in.
    assert "critique_feedback_1" in result["storage"]["session"]


def test_draft_is_restored_into_the_form_field_for_field(tmp_path):
    """Phase 11 (draft preserved): nothing is retyped after a reload."""
    seed = (
        "sessionStorage.setItem('critique_feedback_1', JSON.stringify("
        "{clarity: 'confusing', would_use: 'no', suggestion: 'spell out the pricing'}))"
    )
    result = run(
        tmp_path,
        "project_detail.html",
        [
            {"evaluate": seed, "as": "seeded"},
            {"fn": "renderProject", "args": [PROJECT, []]},
            {
                "evaluate": "document.querySelector('input[name=\"clarity\"]:checked').value",
                "as": "clarity",
            },
            {
                "evaluate": "document.querySelector('input[name=\"would_use\"]:checked').value",
                "as": "would_use",
            },
            {"evaluate": "document.getElementById('suggestion').value", "as": "suggestion"},
        ],
        fetch=DETAIL_ROUTES,
        location="/project/1",
    )

    assert result["values"]["clarity"] == "confusing"
    assert result["values"]["would_use"] == "no"
    assert result["values"]["suggestion"] == "spell out the pricing"
    # Restoring a draft is not evidence that anyone signed in.
    assert events(result, "login_success") == []
    assert events(result, "email_verification_success") == []


# ---------------------------------------------------------------------------
# Returning from sign-in continues the submission (Phase 2 / Phase 11)
# ---------------------------------------------------------------------------


def _feed_route():
    return (
        "/api/projects/?",
        {
            "status": 200,
            "body": {
                "total": 2,
                "items": [{"id": 1, "title": "Sentry bot"}, {"id": 2, "title": "Biohome"}],
            },
        },
    )


def _posts(result):
    return [
        r for r in result["requests"] if r["method"] == "POST" and r["url"].endswith("/responses")
    ]


def test_returning_from_github_continues_the_submission(tmp_path):
    """The sign-in detour must not cost the visitor a second submit click."""
    feed_url, feed_body = _feed_route()
    fetch = {
        "/api/projects/1/responses": {"status": 201, "body": {}},
        "/api/projects/1": {"status": 200, "body": PROJECT},
        feed_url: feed_body,
    }
    result = run(
        tmp_path,
        "project_detail.html",
        [*FILL_FORM, {"fn": "saveFeedbackDraft", "args": []}, {"fn": "renderProject", "args": [PROJECT, []]}],
        fetch=fetch,
        location="/project/1?resume=feedback",
    )

    posts = _posts(result)
    assert len(posts) == 1, result["requests"]
    assert json.loads(posts[0]["body"]) == {
        "clarity": "very_clear",
        "would_use": "yes",
        "suggestion": None,
    }
    assert len(events(result, "feedback_submit_attempt")) == 1
    assert len(events(result, "feedback_submit")) == 1
    assert events(result, "feedback_submit_error") == []
    assert len(events(result, "feedback_resume")) == 1
    assert len(events(result, "login_success")) == 1
    assert "Thank you! Your feedback has been submitted." in result["ids"]["message"]
    assert "critique_responded_1" in result["storage"]["session"]


def test_returning_from_the_email_link_continues_the_submission(tmp_path):
    """Same continuation on the new-tab email path (localStorage fallback)."""
    feed_url, feed_body = _feed_route()
    fetch = {
        "/api/projects/1/responses": {"status": 201, "body": {}},
        "/api/projects/1": {"status": 200, "body": PROJECT},
        feed_url: feed_body,
    }
    result = run(
        tmp_path,
        "project_detail.html",
        [
            *FILL_FORM,
            {"fn": "saveEmailFallbackDraft", "args": []},
            {"fn": "renderProject", "args": [PROJECT, []]},
        ],
        fetch=fetch,
        location="/project/1?resume=feedback",
    )

    posts = _posts(result)
    assert len(posts) == 1, result["requests"]
    assert len(events(result, "email_verification_success")) == 1
    assert len(events(result, "feedback_resume")) == 1
    assert len(events(result, "feedback_submit")) == 1
    assert events(result, "feedback_submit_error") == []
    assert "Thank you! Your feedback has been submitted." in result["ids"]["message"]


def test_an_incomplete_draft_is_not_sent_automatically(tmp_path):
    """Continuation is for finished answers only; a partial one stays a draft."""
    fetch = {
        "/api/projects/1/responses": {"status": 201, "body": {}},
        "/api/projects/1": {"status": 200, "body": PROJECT},
    }
    result = run(
        tmp_path,
        "project_detail.html",
        [
            {"checkInput": {"name": "clarity", "value": "confusing"}},
            {"fn": "saveFeedbackDraft", "args": []},
            {"fn": "renderProject", "args": [PROJECT, []]},
        ],
        fetch=fetch,
        location="/project/1?resume=feedback",
    )

    assert _posts(result) == [], result["requests"]
    assert events(result, "feedback_submit_attempt") == []
    # The half-finished answer is still there for its author to finish.
    assert "critique_feedback_1" in result["storage"]["session"]
    assert "Submit feedback" in result["ids"]["content"]
    assert "Continue with GitHub" not in " ".join(result["created"])


# ---------------------------------------------------------------------------
# Already responded (Phase 3 / Phase 11)
# ---------------------------------------------------------------------------


def test_duplicate_response_is_a_completed_state_not_a_red_error(tmp_path):
    """Phase 3: the server already has it, so the screen says so calmly."""
    fetch = {
        "/api/projects/1/responses": {
            "status": 409,
            "body": {"detail": "You have already responded to this question"},
        },
        "/api/projects/1": {"status": 200, "body": PROJECT},
        _feed_route()[0]: _feed_route()[1],
    }
    result = run(
        tmp_path,
        "project_detail.html",
        submit(),
        fetch=fetch,
        location="/project/1",
    )

    lines = {
        m["className"]: m["text"]
        for m in result["createdMeta"]
        if m.get("className") and m.get("text")
    }
    assert lines.get("response-done-title", "").endswith(
        "You already gave feedback on this project."
    )
    assert lines.get("response-done-note", "") == "Thanks for helping this builder."
    # The server's wording for the duplicate is never shown to the visitor.
    assert "You have already responded" not in " ".join(result["created"])
    # Finished-state styling, never the red error treatment.
    assert result["flags"]["message"]["className"] == "response-done"
    assert "alert-error" not in result["flags"]["message"]["className"]
    # No live submit button is left on a form the server would refuse again.
    assert result["flags"]["submit-btn"]["display"] == "none"
    assert "critique_responded_1" in result["storage"]["session"]

    explore = [
        m
        for m in result["createdMeta"]
        if m.get("text") and "Explore another project" in str(m["text"])
    ]
    assert explore, f"no onward link built: {result['createdMeta']}"
    assert explore[0]["href"] == "/project/2"
    # The attempt created nothing, so it stays counted as a rejected submit.
    assert len(events(result, "feedback_submit_error")) == 1
    assert events(result, "feedback_submit") == []


# ---------------------------------------------------------------------------
# Which loads may claim a sign-in (Phase 9)
# ---------------------------------------------------------------------------


def test_sign_in_events_fire_only_on_a_real_return(tmp_path):
    """A reload with a draft is not a login; the resume flag is."""
    fetch = {
        "/api/projects/1/responses": {"status": 401, "body": {"detail": "Not authenticated"}},
        "/api/projects/1": {"status": 200, "body": PROJECT},
    }
    seed = [*FILL_FORM, {"fn": "saveFeedbackDraft", "args": []}, {"fn": "renderProject", "args": [PROJECT, []]}]

    reloaded = run(tmp_path, "project_detail.html", seed, fetch=fetch, location="/project/1")
    assert events(reloaded, "login_success") == []
    assert events(reloaded, "email_verification_success") == []

    returned = run(
        tmp_path,
        "project_detail.html",
        seed,
        fetch=fetch,
        location="/project/1?resume=feedback",
    )
    assert len(events(returned, "login_success")) == 1
    # Coming back from the gate also means the draft goes out -- and, because
    # the session is still anonymous, it lands on the gate again as designed.
    assert len(events(returned, "feedback_submit_attempt")) == 1
    assert events(returned, "feedback_submit_error") == []
