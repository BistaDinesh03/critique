"""The two forms: what the visitor sees, and what the APIs receive.

Phases 4, 5 and 11 of the UX pass. The project form had grown flat -- every
field in one column with the question, the only reason to submit, lost among
them -- and the feedback page read like an open-ended questionnaire. The
project form now reads project -> about it -> your question -> optional (the
question carrying the only accent), and the feedback page reads as a brief
task with an end: what am I reviewing, three numbered questions, submit. One
form, one page -- no wizard, no dialog.

Nothing about the submissions changed: same field names, same limits as the
schemas in ``backend/app/schemas.py``, same CSRF header, same draft-then-gate
behaviour on 401. Structure is asserted against the source; behaviour runs
through the Node rendering harness.

Requires ``node`` on PATH; the whole module is skipped when it is missing.
"""

import json
import re
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

HOMEPAGE_URL = "/api/projects/?page=1&page_size=6"
SUBMIT_URL = "/api/projects/"

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

# Values are set the way a visitor types them: the harness reads element
# values directly, and the submit handler builds its payload from them.
FILL_PROJECT = [
    {
        "evaluate": (
            "document.getElementById('title').value = 'Akiya Scout'; "
            "document.getElementById('description').value = 'Scans listings for abandoned houses'; "
            "document.getElementById('url').value = 'https://akiya-scout.example'; "
            "document.getElementById('image_url').value = ''; "
            "document.getElementById('question').value = 'Is the price shown up front?'; "
            "'filled'"
        ),
        "as": "filled",
    },
    {"submitId": "project-form"},
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
    return [
        r
        for r in result["requests"]
        if (i := r["url"].find(marker)) != -1
        and (i + len(marker) == len(r["url"]) or r["url"][i + len(marker)] == "&")
    ]


def posts(result):
    """The project submissions themselves (analytics also posts, elsewhere)."""
    return [
        r for r in result["requests"]
        if r["method"] == "POST" and r["url"] == SUBMIT_URL
    ]


def page_source(page):
    return (FRONTEND_DIR / page).read_text(encoding="utf-8")


def project_form(source):
    """The markup between the form's tags, nothing else on the page."""
    start = source.index('<form id="project-form">')
    return source[start:source.index("</form>", start)]


def tag_with_id(html, field_id):
    """The opening tag of `field_id`, whatever order its attributes are in."""
    match = re.search(r'<[a-z]+[^>]*\bid="' + re.escape(field_id) + r'"[^>]*>', html)
    assert match, f"no element with id={field_id!r}"
    return match.group(0)


def first_rule_body(source, selector):
    """The declarations of the first `selector { ... }` in the stylesheet."""
    match = re.search(re.escape(selector) + r"\s*\{", source)
    assert match, selector
    return source[match.end():source.index("}", match.end())]


def mobile_blocks(source):
    """Bodies of every phone-width media query in the stylesheet."""
    blocks = []
    for match in re.finditer(r"@media[^{]*max-width:\s*600px[^{]*\{", source):
        depth = 1
        index = match.end()
        while index < len(source) and depth:
            if source[index] == "{":
                depth += 1
            elif source[index] == "}":
                depth -= 1
            index += 1
        blocks.append(source[match.end():index - 1])
    return blocks


# ---------------------------------------------------------------------------
# The project form's hierarchy and validation (Phase 5 / Phase 11)
# ---------------------------------------------------------------------------


def test_project_form_walks_project_then_about_then_question_then_optional():
    """Reading order is the layout: the eye never has to guess what's next."""
    form = project_form(page_source("index.html"))

    marks = [
        "Share your project",
        ">Project</h3>",
        ">About it</h3>",
        ">Your question</h3>",
        ">Optional</h3>",
        "Submit for feedback",
    ]
    positions = [form.index(mark) for mark in marks]
    assert positions == sorted(positions), marks


def test_project_form_keeps_every_field_the_api_needs():
    """Names and limits as the schemas enforce them (schemas.py: 200/5000/500/500/500)."""
    form = project_form(page_source("index.html"))

    title = tag_with_id(form, "title")
    assert 'name="title"' in title and "required" in title
    assert 'type="text"' in title and 'maxlength="200"' in title

    url = tag_with_id(form, "url")
    assert 'name="url"' in url and 'type="url"' in url and 'maxlength="500"' in url

    description = tag_with_id(form, "description")
    assert 'name="description"' in description and 'maxlength="5000"' in description

    question = tag_with_id(form, "question")
    assert 'name="question"' in question and "required" in question
    assert 'maxlength="500"' in question

    image_url = tag_with_id(form, "image_url")
    assert 'name="image_url"' in image_url and 'maxlength="500"' in image_url
    # The screenshot stays optional: an unanswered field never blocks a submit.
    assert "required" not in image_url

    assert "(required)" in form
    assert "form-optional-tag" in form


def test_project_form_gives_the_question_the_only_accent():
    """One accent in the whole form, and it belongs to the question."""
    form = project_form(page_source("index.html"))

    assert form.count("section-heading-accent") == 1
    assert '<h3 class="section-heading section-heading-accent">Your question</h3>' in form
    assert 'class="form-section form-question-section"' in form
    assert '<h3 class="section-heading">Optional</h3>' in form
    assert 'class="form-section form-optional"' in form


def test_the_project_post_carries_the_csrf_header():
    """The API rejects these posts without it (test_csrf.py), so the page sends it."""
    assert "'X-CSRF-Token': csrfToken" in page_source("index.html")
    assert "'X-CSRF-Token': csrfToken" in page_source("project_detail.html")


# ---------------------------------------------------------------------------
# Submitting it (Phase 11: project submission validation)
# ---------------------------------------------------------------------------


def test_project_form_submits_the_payload_the_api_expects(tmp_path):
    result = run(
        tmp_path,
        "index.html",
        FILL_PROJECT,
        fetch={
            HOMEPAGE_URL: {"status": 200, "body": {"total": 0, "items": []}},
            SUBMIT_URL: {
                "status": 201,
                "body": {
                    "project": {
                        "id": 9,
                        "title": "Akiya Scout",
                        "description": "Scans listings for abandoned houses",
                        "url": "https://akiya-scout.example",
                        "image_url": None,
                        "response_count": 0,
                    },
                    "question": {
                        "id": 9,
                        "project_id": 9,
                        "text": "Is the price shown up front?",
                        "is_active": True,
                    },
                },
            },
        },
    )

    assert result["values"]["filled"] == "filled"
    sent = posts(result)
    assert len(sent) == 1, result["requests"]

    payload = json.loads(sent[0]["body"])
    assert payload["project_data"] == {
        "title": "Akiya Scout",
        "description": "Scans listings for abandoned houses",
        "url": "https://akiya-scout.example",
        "image_url": None,
    }
    assert payload["question_data"] == {"text": "Is the price shown up front?"}
    # The success is recorded, reported as the live-project state (the share
    # section lives inside it), and leaves no draft behind.
    assert len(events(result, "project_submit")) == 1
    seen = [m["text"] for m in result["createdMeta"] if m.get("text")]
    assert "Your project is live!" in seen
    assert "critique_project_draft" not in result["storage"]["session"]


def test_an_anonymous_project_submission_keeps_the_draft_and_offers_sign_in(tmp_path):
    """401 is the designed gate, for this form too: kept draft, no dead end."""
    result = run(
        tmp_path,
        "index.html",
        FILL_PROJECT,
        fetch={
            HOMEPAGE_URL: {"status": 200, "body": {"total": 0, "items": []}},
            SUBMIT_URL: {"status": 401, "body": {"detail": "Not authenticated"}},
        },
    )

    assert len(posts(result)) == 1, result["requests"]

    draft = json.loads(result["storage"]["session"]["critique_project_draft"])
    assert draft["title"] == "Akiya Scout"
    assert draft["question"] == "Is the price shown up front?"

    html = " ".join(result["created"])
    assert "Almost there" in html
    assert "Your project is ready to submit." in html
    assert "Continue with GitHub" in html and "Continue with email" in html
    # Inline in the form, never an overlay.
    assert "modal-backdrop" not in html
    assert len(events(result, "login_prompt_shown")) == 1
    # Nothing failed: the gate is not a submit error.
    assert "alert-error" not in result["flags"]["message"]["className"]


# ---------------------------------------------------------------------------
# The feedback page's hierarchy (Phase 4)
# ---------------------------------------------------------------------------


def test_feedback_form_reads_as_a_brief_task_not_a_wizard(tmp_path):
    result = run(
        tmp_path,
        "project_detail.html",
        [{"fn": "renderProject", "args": [PROJECT, []]}],
        location="/project/1",
    )
    html = result["ids"]["content"]

    # What am I reviewing, in order, before anything is asked of the visitor.
    marks = [
        "Sentry bot",
        "Watches your logs",
        "The Maker's Question",
        "Is the alerting clear enough?",
        "Your feedback",
        "1. How clear is it?",
        "2. Would you use it?",
        "3. What would you change?",
        "Submit feedback",
    ]
    positions = [html.index(mark) for mark in marks]
    assert positions == sorted(positions), marks

    # One form, three numbered questions, one page: no wizard, no dialog.
    assert html.count("<form") == 1
    assert html.count("1. ") == 1
    assert "modal-backdrop" not in " ".join(result["created"])


# ---------------------------------------------------------------------------
# Light on a phone (Phase 11: mobile form behavior)
# ---------------------------------------------------------------------------


def test_project_form_is_lightweight_on_mobile():
    source = page_source("index.html")
    mobile = " ".join(mobile_blocks(source))

    # The reduction lives in the phone breakpoint: the same rules, tightened...
    assert ".form-section" in mobile
    assert "margin-bottom: var(--space-4)" in mobile
    assert ".form-question-section" in mobile
    assert "padding: var(--space-4)" in mobile
    # ...while the desktop rule above the breakpoint keeps its room.
    assert "margin-bottom: var(--space-5)" in first_rule_body(source, ".form-section")


def test_feedback_form_is_lightweight_on_mobile():
    source = page_source("project_detail.html")
    mobile = " ".join(mobile_blocks(source))

    assert ".response-form-card" in mobile
    assert "padding: var(--space-4)" in mobile
    assert ".form-section" in mobile
    assert ".question-block" in mobile
    # Same reduction against the roomier desktop rules.
    assert "padding: var(--space-6)" in first_rule_body(source, ".response-form-card")
    assert "padding: var(--space-5)" in first_rule_body(source, ".question-block")
