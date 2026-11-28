"""Frontend render tests for the pre-submission project preview.

The preview is part of the public project form, so these tests follow the same
rendering boundary as the rest of the frontend suite: the real page scripts run
inside ``frontend_render_harness.js`` and the assertions are made on the DOM the
page actually produces. No new test dependency is introduced.

Coverage includes the preview itself (open, close, live updates, expanded card,
URL safety, keyboard and dialog behaviour, small screens) and the regressions
that matter most for this PR: the preview must not undo the merged maker
activation work (#913).
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

pytestmark = [
    pytest.mark.frontend_render,
    pytest.mark.skipif(
        shutil.which("node") is None,
        reason="node is required to run the frontend rendering harness",
    ),
]

HOMEPAGE_URL = "/api/projects/?page=1&page_size=6"
SUBMIT_URL = "/api/projects/"
OK_HOME = {"status": 200, "body": {"total": 0, "items": []}}

FILLED = {
    "title": "Akiya Scout",
    "description": "Scans listings for abandoned houses",
    "url": "https://akiya-scout.example",
    "image_url": "https://akiya-scout.example/shot.png",
    "question": "Is the price shown up front?",
}

CREATED_PROJECT = {
    "project": {
        "id": 9,
        "title": FILLED["title"],
        "description": FILLED["description"],
        "url": FILLED["url"],
        "image_url": FILLED["image_url"],
        "owner_id": 1,
        "response_count": 0,
        "created_at": "2026-09-01T10:00:00",
    },
    "question": {
        "id": 9,
        "project_id": 9,
        "text": FILLED["question"],
        "is_active": True,
    },
}

WAIT_FOR_RENDER = {
    "evaluate": "new Promise(function(r) { setTimeout(function() { r('waited'); }, 10); })",
    "as": "waited",
}


def run(tmp_path, calls, fetch=None, location="/", session=None):
    """Execute index.html scripts through the shared harness."""
    scenario = {
        "page": (FRONTEND_DIR / "index.html").as_posix(),
        "calls": calls,
        "read": {"created": True},
        "fetch": fetch or {HOMEPAGE_URL: OK_HOME},
        "location": location,
        "sessionStorage": session or {},
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


def set_fields(**values):
    assignments = [
        "document.getElementById(%s).value = %s;"
        % (json.dumps(field), json.dumps(value))
        for field, value in values.items()
    ]
    assignments.append("'filled'")
    return "".join(assignments)


def input_event():
    return {"dispatchEventId": "project-form", "eventType": "input"}


def read(id_or_expression, as_name):
    expression = (
        f"document.getElementById({json.dumps(id_or_expression)}).textContent"
        if not id_or_expression.startswith("document.")
        and not id_or_expression.startswith("safe")
        else id_or_expression
    )
    return {"evaluate": expression, "as": as_name}


def evaluate(expression, as_name):
    return {"evaluate": expression, "as": as_name}


def open_small(tmp_path, values=None):
    return run(
        tmp_path,
        [{"evaluate": set_fields(**(values or {})), "as": "filled"}, {"clickId": "preview-btn"}],
    )


def open_full(tmp_path, values=None):
    return run(
        tmp_path,
        [
            {"evaluate": set_fields(**(values or {})), "as": "filled"},
            {"clickId": "preview-btn"},
            {"clickId": "preview"},
        ],
    )


def keydown_on_preview(key):
    return (
        "var e = {key: %s, preventDefault: function() { this.defaultPrevented = true; }};"
        "document.getElementById('preview').handlers"
        "  .filter(function(h) { return h.type === 'keydown'; })"
        "  .forEach(function(h) { h.fn(e); });"
        "e.defaultPrevented;" % json.dumps(key)
    )


def page_source():
    return (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")


def rule_body(source, selector):
    match = re.search(re.escape(selector) + r"\s*\{", source)
    assert match, f"no CSS rule for {selector!r}"
    depth = 1
    index = match.end()
    while index < len(source) and depth:
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
        index += 1
    return source[match.end():index - 1]


def mobile_blocks(source):
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
# Trigger, open/close, and live updates
# ---------------------------------------------------------------------------


def test_preview_trigger_exists_and_does_not_submit(tmp_path):
    result = run(tmp_path, [{"clickId": "preview-btn"}])

    assert result["flags"]["project-preview"]["hidden"] is False
    assert result["requests"] == []


def test_preview_button_is_a_non_submit_button(tmp_path):
    result = run(tmp_path, [
        evaluate("document.getElementById('preview-btn').type", "type"),
    ])

    assert result["values"]["type"] == "button"


def test_close_button_hides_the_small_preview_and_restores_focus(tmp_path):
    result = run(tmp_path, [{"clickId": "preview-btn"}, {"clickId": "close-preview"}])

    assert result["flags"]["project-preview"]["hidden"] is True
    assert result["focused"]["id"] == "preview-btn"


def test_live_title_description_and_question_updates(tmp_path):
    result = run(tmp_path, [
        {"clickId": "preview-btn"},
        {"evaluate": set_fields(**FILLED), "as": "filled"},
        input_event(),
        read("preview-title", "title"),
        read("preview-description", "description"),
        read("preview-question", "question"),
    ])

    assert result["values"]["title"] == FILLED["title"]
    assert result["values"]["description"] == FILLED["description"]
    assert result["values"]["question"] == "Question: " + FILLED["question"]
    assert result["requests"] == []


def test_each_field_updates_without_stale_state(tmp_path):
    result = run(tmp_path, [
        {"clickId": "preview-btn"},
        {"evaluate": set_fields(title="First", description="Old copy", question="Old?"), "as": "first"},
        input_event(),
        {"evaluate": set_fields(title="Second", description="New copy", question="New?"), "as": "second"},
        input_event(),
        read("preview-title", "title"),
        read("preview-description", "description"),
        read("preview-question", "question"),
    ])

    assert result["values"]["title"] == "Second"
    assert result["values"]["description"] == "New copy"
    assert result["values"]["question"] == "Question: New?"


# ---------------------------------------------------------------------------
# Image handling and URL safety
# ---------------------------------------------------------------------------


def test_valid_https_image_appears_then_disappears_when_cleared(tmp_path):
    result = run(tmp_path, [
        {"clickId": "preview-btn"},
        {"evaluate": set_fields(image_url=FILLED["image_url"]), "as": "filled"},
        input_event(),
        evaluate("document.getElementById('preview-image').src", "src"),
        evaluate("document.getElementById('preview-image').hidden", "hidden_with"),
        {"evaluate": set_fields(image_url=""), "as": "cleared"},
        input_event(),
        evaluate("document.getElementById('preview-image').getAttribute('src')", "cleared_src"),
        evaluate("document.getElementById('preview-image').hidden", "hidden_without"),
    ])

    assert result["values"]["src"] == FILLED["image_url"]
    assert result["values"]["hidden_with"] is False
    assert result["values"]["cleared_src"] is None
    assert result["values"]["hidden_without"] is True


@pytest.mark.parametrize("bad_url", [
    "javascript:alert(1)",
    "data:image/png;base64,AAAA",
    "http://example.com/insecure.png",
    "ftp://example.com/file.png",
    "not a url",
])
def test_unsafe_or_invalid_image_urls_are_never_assigned(tmp_path, bad_url):
    small = run(tmp_path, [
        {"clickId": "preview-btn"},
        {"evaluate": set_fields(image_url=bad_url), "as": "filled"},
        input_event(),
        evaluate("document.getElementById('preview-image').getAttribute('src')", "src"),
        evaluate("document.getElementById('preview-image').hidden", "hidden"),
    ])
    full = open_full(tmp_path, {**FILLED, "image_url": bad_url})

    assert small["values"]["src"] is None
    assert small["values"]["hidden"] is True
    assert 'src="' + bad_url + '"' not in full["ids"]["full-preview-content"]
    assert "preview-full-image" not in full["ids"]["full-preview-content"]


@pytest.mark.parametrize("bad_url", [
    "javascript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "vbscript:msgbox(1)",
    "file:///etc/passwd",
    "ftp://example.com",
    "example.com",
])
def test_unsafe_or_invalid_project_urls_are_not_clickable(tmp_path, bad_url):
    result = open_full(tmp_path, {**FILLED, "url": bad_url})
    html = result["ids"]["full-preview-content"]

    assert "Visit project" not in html
    assert 'href="' + bad_url + '"' not in html
    assert "javascript:" not in html
    assert "vbscript:" not in html
    assert "file:" not in html


@pytest.mark.parametrize("good_url", ["http://example.com", "https://example.com/a?b=1&c=2"])
def test_safe_project_urls_render_as_external_links(tmp_path, good_url):
    result = open_full(tmp_path, {**FILLED, "url": good_url})
    html = result["ids"]["full-preview-content"]

    assert "Visit project" in html
    assert 'rel="noopener noreferrer"' in html
    assert 'href="' in html


# ---------------------------------------------------------------------------
# Expanded preview, dialog semantics, and keyboard behaviour
# ---------------------------------------------------------------------------


def test_small_card_opens_the_expanded_preview(tmp_path):
    result = open_full(tmp_path, FILLED)
    html = result["ids"]["full-preview-content"]

    assert result["flags"]["full-preview"]["hidden"] is False
    assert FILLED["title"] in html
    assert FILLED["description"] in html
    assert FILLED["question"] in html
    assert FILLED["url"] in html
    assert FILLED["image_url"] in html


def test_expanded_preview_has_dialog_semantics_and_a_label(tmp_path):
    result = open_full(tmp_path, FILLED)
    expressions = [
        evaluate("document.getElementById('full-preview').getAttribute('role')", "role"),
        evaluate("document.getElementById('full-preview').getAttribute('aria-modal')", "modal"),
        evaluate("document.getElementById('full-preview').getAttribute('aria-label')", "label"),
        evaluate("document.getElementById('close-full-preview').getAttribute('aria-label')", "close_label"),
    ]
    checked = run(tmp_path, [
        {"evaluate": set_fields(**FILLED), "as": "filled"},
        {"clickId": "preview-btn"},
        {"clickId": "preview"},
    ] + expressions)

    assert checked["values"]["role"] == "dialog"
    assert checked["values"]["modal"] == "true"
    assert checked["values"]["label"] == "Project preview"
    assert checked["values"]["close_label"] == "Close project preview"
    assert result["flags"]["full-preview"]["hidden"] is False


def test_opening_the_dialog_moves_focus_to_the_close_button(tmp_path):
    result = open_full(tmp_path, FILLED)

    assert result["focused"]["id"] == "close-full-preview"


def test_escape_closes_the_dialog_and_restores_focus(tmp_path):
    result = run(tmp_path, [
        {"clickId": "preview-btn"},
        {"clickId": "preview"},
        {"dispatchKeydown": "Escape"},
    ])

    assert result["flags"]["full-preview"]["hidden"] is True
    assert result["focused"]["id"] == "preview"


def test_close_button_hides_the_dialog_and_restores_focus(tmp_path):
    result = run(tmp_path, [
        {"clickId": "preview-btn"},
        {"clickId": "preview"},
        {"clickId": "close-full-preview"},
    ])

    assert result["flags"]["full-preview"]["hidden"] is True
    assert result["focused"]["id"] == "preview"


def test_enter_and_space_open_the_dialog_and_prevent_default(tmp_path):
    for key in ("Enter", " "):
        result = run(tmp_path, [
            {"clickId": "preview-btn"},
            {"evaluate": keydown_on_preview(key), "as": "handled"},
        ])
        assert result["values"]["handled"] is True
        assert result["flags"]["full-preview"]["hidden"] is False


def test_full_preview_uses_the_published_question_label(tmp_path):
    result = open_full(tmp_path, FILLED)
    html = result["ids"]["full-preview-content"]

    assert "The Maker&#39;s Question" in html
    assert "The Makers Question" not in html
    assert 'class="project-title"' in html
    assert 'class="question-block"' in html


# ---------------------------------------------------------------------------
# Text safety, placeholders, long content, and small screens
# ---------------------------------------------------------------------------


def test_user_text_is_escaped_in_both_previews(tmp_path):
    payload = '<img src=x onerror="window.__preview_xss=1">'
    values = {"title": payload, "description": payload, "question": payload}

    small = run(tmp_path, [
        {"clickId": "preview-btn"},
        {"evaluate": set_fields(**values), "as": "filled"},
        input_event(),
        read("preview-title", "title"),
        read("preview-description", "description"),
        read("preview-question", "question"),
    ])
    full = open_full(tmp_path, values)
    html = full["ids"]["full-preview-content"]

    assert small["values"]["title"] == payload
    assert small["values"]["description"] == payload
    assert small["values"]["question"] == "Question: " + payload
    assert "<img src=x" not in html
    assert "&lt;img" in html
    assert "onerror=&quot;window.__preview_xss=1&quot;" in html


def test_empty_fields_show_graceful_placeholders(tmp_path):
    small = run(tmp_path, [
        {"clickId": "preview-btn"},
        read("preview-title", "title"),
        read("preview-description", "description"),
        read("preview-question", "question"),
    ])
    full = open_full(tmp_path, {})

    assert small["values"]["title"] == "Your project title"
    assert small["values"]["description"] == "Description to be provided"
    assert small["values"]["question"] == "Question: No question provided"
    assert small["flags"]["preview-image"]["hidden"] is True
    assert "Project title required" in full["ids"]["full-preview-content"]
    assert "No question provided" in full["ids"]["full-preview-content"]


def test_long_content_is_carried_into_the_preview_and_can_wrap(tmp_path):
    values = {"title": "T" * 200, "description": "D" * 5000, "question": "Q" * 500}
    result = open_full(tmp_path, values)
    html = result["ids"]["full-preview-content"]

    assert values["title"] in html
    assert values["description"] in html
    assert values["question"] in html

    source = page_source()
    for selector in (
        "#full-preview-content .project-title",
        "#full-preview-content .project-summary",
        "#full-preview-content .question-text",
    ):
        assert "overflow-wrap" in rule_body(source, selector)


def test_preview_controls_have_phone_width_rules():
    mobile = " ".join(mobile_blocks(page_source()))

    assert ".buttons-form" in mobile
    assert "flex-direction: column" in mobile
    assert ".project-preview-overlay" in mobile
    assert ".project-preview-content" in mobile


# ---------------------------------------------------------------------------
# Submission and merged-main regressions
# ---------------------------------------------------------------------------


def submit_calls():
    return [
        {"evaluate": set_fields(**FILLED), "as": "filled"},
        {"clickId": "preview-btn"},
        {"clickId": "close-preview"},
        {"clickId": "preview-btn"},
        {"clickId": "preview"},
        {"clickId": "close-full-preview"},
        {"submitId": "project-form"},
    ]


def posts(result):
    return [
        request for request in result["requests"]
        if request["method"] == "POST" and request["url"] == SUBMIT_URL
    ]


def test_preview_interactions_do_not_change_the_submission_payload(tmp_path):
    result = run(tmp_path, submit_calls(), fetch={
        HOMEPAGE_URL: OK_HOME,
        SUBMIT_URL: {"status": 201, "body": CREATED_PROJECT},
    })

    assert len(posts(result)) == 1
    payload = json.loads(posts(result)[0]["body"])
    assert payload["project_data"] == {
        "title": FILLED["title"],
        "description": FILLED["description"],
        "url": FILLED["url"],
        "image_url": FILLED["image_url"],
    }
    assert payload["question_data"] == {"text": FILLED["question"]}


def test_typing_still_saves_the_draft_without_waiting_for_sign_in(tmp_path):
    result = run(tmp_path, [
        {"evaluate": set_fields(title="Akiya Scout", question="Is the price clear?"), "as": "filled"},
        input_event(),
    ])

    draft = json.loads(result["storage"]["session"]["critique_project_draft"])
    assert draft["title"] == "Akiya Scout"
    assert draft["question"] == "Is the price clear?"


def test_existing_draft_is_restored_on_a_normal_load(tmp_path):
    draft = json.dumps({"title": "Akiya Scout", "question": "Is the price clear?"})
    result = run(
        tmp_path,
        [
            evaluate("document.getElementById('title').value", "title"),
            evaluate("document.getElementById('question').value", "question"),
        ],
        session={"critique_project_draft": draft},
    )

    assert result["values"]["title"] == "Akiya Scout"
    assert result["values"]["question"] == "Is the price clear?"


def test_question_guidance_and_sign_in_expectation_are_preserved():
    match = re.search(
        r"<form\s+id=\"project-form\".*?</form>", page_source(), re.DOTALL
    )
    assert match, "project form not found"
    form_html = match.group(0)

    assert "One specific question gets a useful answer." in form_html
    assert "Name the part you want reviewed, not the whole project." in form_html
    assert "You'll sign in when you submit." in form_html


def test_field_specific_validation_error_is_preserved(tmp_path):
    result = run(tmp_path, [
        {"evaluate": set_fields(**FILLED), "as": "filled"},
        {"submitId": "project-form"},
    ], fetch={
        HOMEPAGE_URL: OK_HOME,
        SUBMIT_URL: {
            "status": 422,
            "body": {"detail": [{"loc": ["body", "project_data", "title"], "msg": "Field required"}]},
        },
    })

    assert result["ids"]["message"] == (
        "Add a project title, then try again. Your answers are still here."
    )
    assert "value_error" not in result["ids"]["message"]


def test_rate_limit_retry_after_message_is_preserved(tmp_path):
    result = run(tmp_path, [
        {"evaluate": set_fields(**FILLED), "as": "filled"},
        {"submitId": "project-form"},
    ], fetch={
        HOMEPAGE_URL: OK_HOME,
        SUBMIT_URL: {
            "status": 429,
            "body": {"detail": "Too many requests. Please slow down."},
            "headers": {"Retry-After": "42"},
        },
    })

    assert result["ids"]["message"] == (
        "Too many submissions. Try again in 42 seconds. Your answers are still here."
    )
    draft = json.loads(result["storage"]["session"]["critique_project_draft"])
    assert draft["title"] == FILLED["title"]


def test_network_error_reassurance_is_preserved(tmp_path):
    result = run(tmp_path, [
        {"evaluate": set_fields(**FILLED), "as": "filled"},
        {"submitId": "project-form"},
    ], fetch={
        HOMEPAGE_URL: OK_HOME,
        SUBMIT_URL: {"networkError": True, "message": "Failed to fetch", "body": {}},
    })

    assert result["ids"]["message"] == "Network error. Your answers are still here."
    draft = json.loads(result["storage"]["session"]["critique_project_draft"])
    assert draft["question"] == FILLED["question"]


def test_share_post_still_includes_the_makers_question(tmp_path):
    result = run(tmp_path, [
        {"evaluate": set_fields(**FILLED), "as": "filled"},
        {"submitId": "project-form"},
        WAIT_FOR_RENDER,
    ], fetch={
        HOMEPAGE_URL: OK_HOME,
        SUBMIT_URL: {"status": 201, "body": CREATED_PROJECT},
    })

    posts_text = [meta.get("value") or "" for meta in result["createdMeta"]]
    assert any(FILLED["question"] in text for text in posts_text)
    assert any(FILLED["title"] in text for text in posts_text)


def test_analytics_scripts_keep_their_required_order():
    source = page_source()
    events = source.index("/static/analytics_events.js")
    analytics = source.index("/static/analytics.js")
    share = source.index("/static/share.js")

    assert events < analytics < share


def test_theme_color_metadata_is_present():
    tags = re.findall(r"<meta\s+name=\"theme-color\"[^>]*>", page_source())

    assert len(tags) == 2
    assert any("prefers-color-scheme: light" in tag and "#ffffff" in tag for tag in tags)
    assert any("prefers-color-scheme: dark" in tag and "#1e293b" in tag for tag in tags)


def test_file_uses_lf_line_endings():
    assert b"\r\n" not in (FRONTEND_DIR / "index.html").read_bytes()
