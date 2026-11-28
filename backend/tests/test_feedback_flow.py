"""Feedback submission: which outcomes count as errors, and what comes next.

Production analytics showed 109 submit attempts, 46 successes, 13
already-responded results, and 33 recorded errors. The endpoint currently
accepts guest feedback (``get_current_user_optional``), so a signed-out visitor
can reach ``201`` and a ``401`` is not reachable in practice; it is kept as a
defensive branch in case a sign-in gate returns. The failure classes that are
real today are ``403`` (CSRF or owner), ``404`` (project/question gone), ``422``
(validation), ``429`` (rate limit), ``5xx``, and network errors.

The page used to count the (then reachable) 401 gate as
``feedback_submit_error``, which inflated the error count and buried real
failures. These tests run the page's real JavaScript inside the Node rendering
harness and lock both sides of the fix:

* a 401 gate is *not* an error (it is recorded as ``login_prompt_shown`` and the
  draft is kept for after login),
* genuine failures (CSRF, server error, validation, rate limit, network) still
  are, and they show actionable copy instead of backend internals,
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
        if m.get("id") == "help-another-builder"
    ]


# ---------------------------------------------------------------------------
# What is (and is not) a submit error
# ---------------------------------------------------------------------------


def test_sign_in_gate_401_is_not_a_submit_error(tmp_path):
    """A 401 gate shows login, keeps the draft, and is not an error event.

    Defensive: the API currently accepts guest feedback, so this status is not
    reachable today. If a sign-in gate is ever re-introduced, it must not be
    counted as a failed submission.
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
    assert "Session expired." in result["ids"]["message"]
    # Refreshing is the only fix for a stale CSRF/session pair, so the answers
    # must already be in the draft before the visitor is told to refresh.
    draft = json.loads(result["storage"]["session"]["critique_feedback_1"])
    assert draft["clarity"] == "very_clear"
    assert draft["would_use"] == "yes"


def test_server_error_is_still_a_submit_error(tmp_path):
    """A 5xx is a real failure, but the visitor sees copy they can act on."""
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
    # The raw server detail is an internal and is never rendered.
    assert "Boom on the server" not in result["ids"]["message"]
    assert "Something went wrong on our side" in result["ids"]["message"]
    # The answers survive so a retry does not start from scratch.
    draft = json.loads(result["storage"]["session"]["critique_feedback_1"])
    assert draft["clarity"] == "very_clear"
    assert draft["would_use"] == "yes"


def test_rate_limit_shows_wait_and_keeps_draft(tmp_path):
    """429 is throttling: say when to retry, keep the answers, one error event."""
    fetch = {
        "/api/projects/1/responses": {
            "status": 429,
            "body": {"detail": "Too many requests. Please slow down."},
            "headers": {"Retry-After": "42"},
        },
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
    message = result["ids"]["message"]
    assert "submitted several responses recently" in message
    assert "42 seconds" in message
    # The raw backend wording is not shown.
    assert "Too many requests" not in message
    draft = json.loads(result["storage"]["session"]["critique_feedback_1"])
    assert draft["clarity"] == "very_clear"


def test_closed_project_404_closes_the_form_without_raw_detail(tmp_path):
    """A project/question that disappeared is a calm closed state, not internals."""
    fetch = {
        "/api/projects/1/responses": {
            "status": 404,
            "body": {"detail": "No active question for this project"},
        },
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
    assert "no longer accepting feedback" in result["ids"]["message"]
    assert "No active question" not in " ".join(result["created"])
    # The form is closed, so the same dead submission cannot be retried.
    assert result["flags"]["submit-btn"]["display"] == "none"
    assert result["flags"]["submit-btn"]["disabled"] is True


def test_validation_422_never_renders_the_detail_object(tmp_path):
    """FastAPI's 422 detail is a list; it must not reach the visitor as text."""
    fetch = {
        "/api/projects/1/responses": {
            "status": 422,
            "body": {"detail": [{"loc": ["body", "clarity"], "msg": "invalid"}]},
        },
        "/api/projects/1": {"status": 200, "body": PROJECT},
    }
    result = run(
        tmp_path,
        "project_detail.html",
        submit(),
        fetch=fetch,
        location="/project/1",
    )

    message = result["ids"]["message"]
    assert "Please check your answers" in message
    assert "[object Object]" not in message
    assert len(events(result, "feedback_submit_error")) == 1
    draft = json.loads(result["storage"]["session"]["critique_feedback_1"])
    assert draft["clarity"] == "very_clear"


def test_csrf_403_is_retried_once_with_a_fresh_token(tmp_path):
    """A stale CSRF token recovers without retyping or a duplicate answer."""
    # The harness consumes a route array in call order, and the page loads the
    # existing responses (GET .../responses) before the submit. The first entry
    # is that load; the POST then gets 403 and its one retry gets 201.
    fetch = {
        "/api/projects/1/responses": [
            {"status": 200, "body": []},
            {"status": 403, "body": {"detail": "Invalid or missing CSRF token"}},
            {"status": 201, "body": {}},
        ],
        "/auth/csrf-token": {"status": 200, "body": {"csrf_token": "fresh-token"}},
        "/api/projects/1": {"status": 200, "body": PROJECT},
    }
    result = run(
        tmp_path,
        "project_detail.html",
        submit(),
        fetch=fetch,
        location="/project/1",
    )

    posts = [r for r in result["requests"] if r["method"] == "POST" and r["url"].endswith("/responses")]
    token_gets = [r for r in result["requests"] if r["url"].endswith("/auth/csrf-token")]
    assert len(posts) == 2, "the rejected send should be retried exactly once"
    assert len(token_gets) == 1
    # The retry is part of the same attempt: one attempt, one success, no error.
    assert len(events(result, "feedback_submit_attempt")) == 1
    assert len(events(result, "feedback_submit")) == 1
    assert events(result, "feedback_submit_error") == []
    assert "Feedback submitted successfully!" in result["ids"]["message"]


def test_double_submit_while_in_flight_sends_only_one_request(tmp_path):
    """A second submit before the first resolves must not POST twice."""
    fetch = {
        "/api/projects/1/responses": {"pending": True},
        "/api/projects/1": {"status": 200, "body": PROJECT},
    }
    result = run(
        tmp_path,
        "project_detail.html",
        [*FILL_FORM, {"submitId": "response-form"}, {"submitId": "response-form"}],
        fetch=fetch,
        location="/project/1",
    )

    posts = [r for r in result["requests"] if r["method"] == "POST" and r["url"].endswith("/responses")]
    assert len(posts) == 1
    assert len(events(result, "feedback_submit_attempt")) == 1


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
    assert "Feedback submitted successfully!" in result["ids"]["message"]

    links = help_links(result)
    assert links, f"no next-step link built: {result['createdMeta']}"
    # Points at a *different* real project, never back at the answered one.
    assert links[0]["href"] == "/project/2"
    # When a project title is available, the link text shows it.
    assert links[0]["text"] == "Help Biohome \u2192"

    # Confirms live README badge link is offered for viral project promotion
    badge_links = [m for m in result["createdMeta"] if m.get("id") == "project-badge-link"]
    assert badge_links, f"no project badge link found in {result['createdMeta']}"
    assert badge_links[0]["href"] == "/badge/1.svg"

    # Confirmation panel features: discover link and accessible dismiss button (fixes #331)
    assert any("Discover more projects" in (m.get("text") or "") for m in result["createdMeta"])
    assert any(m.get("ariaLabel") == "Dismiss confirmation" for m in result["createdMeta"])

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
    assert "Feedback submitted successfully!" in thanks
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


def test_draft_restore_updates_suggestion_char_count(tmp_path):
    """The counter must reflect a restored draft, not only typed input.

    ``restoreFeedbackDraft()`` assigns ``textarea.value`` directly, which does
    not fire an ``input`` event. Without a refresh after the restore paths a
    visitor returning to a saved answer still sees "0 / 2000".
    """
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
            {"evaluate": "document.getElementById('suggestion').value", "as": "suggestion"},
            {
                "evaluate": "document.getElementById('suggestion-char-count').textContent",
                "as": "counter",
            },
        ],
        fetch=DETAIL_ROUTES,
        location="/project/1",
    )

    assert result["values"]["suggestion"] == "spell out the pricing"
    assert result["values"]["counter"] == "21 / 2000"


def test_suggestion_char_count_starts_at_zero_without_a_draft(tmp_path):
    """A fresh form starts at 0 / 2000, so the counter never shows a stale value."""
    result = run(
        tmp_path,
        "project_detail.html",
        [
            {"fn": "renderProject", "args": [PROJECT, []]},
            {
                "evaluate": "document.getElementById('suggestion-char-count').textContent",
                "as": "counter",
            },
        ],
        fetch=DETAIL_ROUTES,
        location="/project/1",
    )

    assert result["values"]["counter"] == "0 / 2000"


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
    assert "Feedback submitted successfully!" in result["ids"]["message"]
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
    assert "Feedback submitted successfully!" in result["ids"]["message"]


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
    # A 409 emits feedback_already_responded, not feedback_submit_error (#270).
    assert len(events(result, "feedback_already_responded")) == 1
    assert events(result, "feedback_submit_error") == []
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


def test_feedback_draft_and_responded_keys_are_namespaced_per_account(tmp_path):
    """Different accounts in the same tab get independent draft and responded state (fixes #315)."""
    fetch = {
        "/api/projects/1": {"status": 200, "body": PROJECT},
    }
    result = run(
        tmp_path,
        "project_detail.html",
        [
            {"fn": "renderProject", "args": [PROJECT, []]},
            # User A
            {"fn": "setCurrentUserId", "args": ["user_123"]},
            {"evaluate": "feedbackStorageKey()", "as": "userA_storageKey"},
            {"evaluate": "feedbackSubmittedKey()", "as": "userA_submittedKey"},
            # User B
            {"fn": "setCurrentUserId", "args": ["user_456"]},
            {"evaluate": "feedbackStorageKey()", "as": "userB_storageKey"},
            {"evaluate": "feedbackSubmittedKey()", "as": "userB_submittedKey"},
            # Anonymous
            {"fn": "setCurrentUserId", "args": [None]},
            {"evaluate": "feedbackStorageKey()", "as": "anon_storageKey"},
            {"evaluate": "feedbackSubmittedKey()", "as": "anon_submittedKey"},
        ],
        fetch=fetch,
        location="/project/1",
    )
    assert result["values"]["userA_storageKey"] == "critique_feedback_user_123_1"
    assert result["values"]["userA_submittedKey"] == "critique_responded_user_123_1"
    assert result["values"]["userB_storageKey"] == "critique_feedback_user_456_1"
    assert result["values"]["userB_submittedKey"] == "critique_responded_user_456_1"
    assert result["values"]["anon_storageKey"] == "critique_feedback_1"
    assert result["values"]["anon_submittedKey"] == "critique_responded_1"


# ---------------------------------------------------------------------------
# Client-side validation before submission
# ---------------------------------------------------------------------------


def test_missing_required_selection_shows_validation_message(tmp_path):
    """Submitting without both ratings never leaves the page or fires an attempt."""
    fetch = {
        "/api/projects/1/responses": {"status": 201, "body": {}},
        "/api/projects/1": {"status": 200, "body": PROJECT},
    }
    result = run(
        tmp_path,
        "project_detail.html",
        [{"submitId": "response-form"}, {"evaluate": "document.getElementById('submit-btn').disabled", "as": "btn_disabled"}],
        fetch=fetch,
        location="/project/1",
    )

    assert "Please answer both required questions before submitting." in result["ids"]["message"]
    # No attempt event and no request were produced.
    assert events(result, "feedback_submit_attempt") == []
    posts = [r for r in result["requests"] if r["method"] == "POST" and r["url"].endswith("/responses")]
    assert posts == []
    # Button stays enabled so the visitor can fix and retry.
    assert result["values"]["btn_disabled"] is False


def test_feedback_form_has_progress_indicator(tmp_path):
    """The feedback form displays an accessible progress indicator (fixes #329)."""
    fetch = {
        "/api/projects/1": {"status": 200, "body": PROJECT},
    }
    result = run(
        tmp_path,
        "project_detail.html",
        [{"fn": "renderProject", "args": [PROJECT, []]}],
        fetch=fetch,
        location="/project/1",
        read={"byId": "content"},
    )
    assert 'role="progressbar"' in result["html"]
    assert 'aria-label="Feedback progress"' in result["html"]
    assert 'aria-valuenow="0"' in result["html"]
    assert 'aria-valuemax="2"' in result["html"]
    assert 'aria-valuetext="0 of 2 required questions answered"' in result["html"]
    assert "0 of 2 required questions answered" in result["html"]


def test_project_detail_shows_response_count_to_owner(tmp_path):
    """Owner sees response count badge in project header; non-owners do not (fixes #327)."""
    owner_data = {
        "project": {
            "id": 1,
            "title": "Owner's App",
            "description": "App description",
            "response_count": 4,
            "image_url": None,
            "url": None,
        },
        "question": {
            "id": 1,
            "text": "What do you think?",
            "is_active": True,
            "project_id": 1,
        },
        "is_owner": True,
    }
    non_owner_data = {
        "project": {
            "id": 2,
            "title": "Visitor's App",
            "description": "App description",
            "response_count": 4,
            "image_url": None,
            "url": None,
        },
        "question": {
            "id": 2,
            "text": "What do you think?",
            "is_active": True,
            "project_id": 2,
        },
        "is_owner": False,
    }

    owner_res = run(tmp_path, "project_detail.html", [{"fn": "renderProject", "args": [owner_data, []]}], read={"byId": "content"})
    assert "owner-response-count" in owner_res["html"]
    assert "4 responses" in owner_res["html"]

    non_owner_res = run(tmp_path, "project_detail.html", [{"fn": "renderProject", "args": [non_owner_data, []]}], read={"byId": "content"})
    assert "owner-response-count" not in non_owner_res["html"]


def test_owner_view_replaces_feedback_form_with_owner_banner(tmp_path):
    """An owner never gets the feedback section: no "Your feedback" label,
    no form controls — instead a PROJECT OWNER note that links to the
    results page (fixes #814). A non-owner still sees the form."""
    owner_data = {
        "project": {
            "id": 1,
            "title": "Owner's App",
            "description": "App description",
            "response_count": 1,
            "image_url": None,
            "url": None,
        },
        "question": {
            "id": 1,
            "text": "What do you think?",
            "is_active": True,
            "project_id": 1,
        },
        "is_owner": True,
    }
    owner_html = run(
        tmp_path, "project_detail.html",
        [{"fn": "renderProject", "args": [owner_data, []]}],
        read={"byId": "content"},
    )["html"]

    # The banner replaces the whole feedback section.
    assert '<div class="eyebrow">Project owner</div>' in owner_html
    assert "This is your project" in owner_html
    assert 'href="/project/1/results"' in owner_html
    assert 'class="response-form-card"' in owner_html

    # Nothing of the form leaks through: no label, no container, no controls.
    assert '<div class="eyebrow">Your feedback</div>' not in owner_html
    assert 'id="response-form"' not in owner_html
    assert 'name="clarity"' not in owner_html
    assert "Submit feedback" not in owner_html


    non_owner_html = run(
        tmp_path, "project_detail.html",
        [{"fn": "renderProject", "args": [PROJECT, []]}],
        read={"byId": "content"},
    )["html"]

    # A visitor (no is_owner flag) still gets the label and the full form.
    assert '<div class="eyebrow">Your feedback</div>' in non_owner_html
    assert 'id="response-form"' in non_owner_html
    assert 'id="owner-note"' not in non_owner_html


def test_feedback_form_suggestion_textarea_has_maxlength(tmp_path):
    """The suggestion textarea caps input at 2000 characters to match the API schema (fixes #279)."""
    result = run(
        tmp_path,
        "project_detail.html",
        [{"fn": "renderProject", "args": [PROJECT, []]}],
        read={"byId": "content"},
    )
    assert '<textarea class="form-textarea" id="suggestion" maxlength="2000"' in result["html"]
