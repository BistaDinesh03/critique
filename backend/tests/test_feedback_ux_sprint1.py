"""Frontend rendering tests for the Feedback UX Sprint 1 changes (#900-#903)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "frontend"
HARNESS = Path(__file__).resolve().parent / "frontend_render_harness.js"
DETAIL_SOURCE = FRONTEND_DIR / "project_detail.html"

pytestmark = [
    pytest.mark.frontend_render,
    pytest.mark.skipif(
        shutil.which("node") is None,
        reason="node is required to run the frontend rendering harness",
    ),
]

PROJECT = {
    "project": {
        "id": 7,
        "title": "Invoice Radar",
        "description": "Tracks overdue invoices.",
        "image_url": "/static/og-image.png",
        "url": "https://example.com/invoice-radar",
        "response_count": 2,
    },
    "question": {
        "id": 1,
        "text": "Is the pricing clear?",
        "is_active": True,
        "project_id": 7,
    },
}

READ_PROGRESS = (
    "(function() {"
    "  var indicator = document.querySelector('.feedback-progress-indicator');"
    "  var fill = document.getElementById('progress-fill');"
    "  var label = document.getElementById('progress-label');"
    "  return {"
    "    now: indicator ? indicator.getAttribute('aria-valuenow') : null,"
    "    max: indicator ? indicator.getAttribute('aria-valuemax') : null,"
    "    valueText: indicator ? indicator.getAttribute('aria-valuetext') : null,"
    "    describedBy: indicator ? indicator.getAttribute('aria-describedby') : null,"
    "    label: label ? label.textContent : null,"
    "    width: fill ? fill.style.width : null"
    "  };"
    "})()"
)

READ_PRIVACY = (
    "(function() {"
    "  var note = document.getElementById('suggestion-privacy-note');"
    "  var hint = document.getElementById('suggestion-followup-hint');"
    "  var input = document.getElementById('suggestion');"
    "  var counter = document.getElementById('suggestion-char-count');"
    "  return {"
    "    noteHidden: note ? !!note.hidden : null,"
    "    hintHidden: hint ? !!hint.hidden : null,"
    "    describedBy: input ? input.getAttribute('aria-describedby') : null,"
    "    counter: counter ? counter.textContent : null"
    "  };"
    "})()"
)

TYPE_OPTIONAL_SUGGESTION = (
    "(function() {"
    "  var input = document.getElementById('suggestion');"
    "  input.value = 'Pricing tiers are still unclear.';"
    "  return input.value;"
    "})()"
)


def _run_detail(tmp_path, calls, project=PROJECT):
    scenario = {
        "page": (FRONTEND_DIR / "project_detail.html").as_posix(),
        "calls": calls,
        "read": {"byId": "content"},
        "fetch": {},
        "location": "/project/7",
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


def test_project_context_precedes_question_and_form(tmp_path):
    """#900: reviewers see the full project image before being asked to judge it."""
    result = _run_detail(tmp_path, [{"fn": "renderProject", "args": [PROJECT, []]}])
    html = result["html"]

    context_pos = html.index('class="eyebrow">About this project')
    image_pos = html.index('class="project-screenshot"')
    link_pos = html.index("View full image")
    question_pos = html.index("The Maker")
    form_pos = html.index('id="response-form"')
    assert context_pos < image_pos < link_pos < question_pos < form_pos
    assert 'target="_blank" rel="noopener noreferrer">View full image' in html
    assert 'alt="Screenshot of Invoice Radar"' in html


def test_project_without_image_shows_fallback_before_form(tmp_path):
    project = json.loads(json.dumps(PROJECT))
    project["project"]["image_url"] = None
    result = _run_detail(tmp_path, [{"fn": "renderProject", "args": [project, []]}])
    html = result["html"]

    assert "No screenshot was provided by the maker." in html
    assert html.index("No screenshot was provided by the maker.") < html.index('id="response-form"')
    assert 'class="project-screenshot"' not in html


def test_feedback_progress_counts_only_required_questions(tmp_path):
    """#901: the optional suggestion never changes required-question progress."""
    result = _run_detail(
        tmp_path,
        [
            {"fn": "renderProject", "args": [PROJECT, []]},
            {"evaluate": READ_PROGRESS, "as": "initial"},
            {"checkInput": {"name": "clarity", "value": "very_clear"}},
            {"evaluate": "updateFeedbackProgress()"},
            {"evaluate": READ_PROGRESS, "as": "one_answer"},
            {"checkInput": {"name": "would_use", "value": "yes"}},
            {"evaluate": "updateFeedbackProgress()"},
            {"evaluate": READ_PROGRESS, "as": "both_answers"},
            {"evaluate": TYPE_OPTIONAL_SUGGESTION},
            {"evaluate": "updateFeedbackProgress()"},
            {"evaluate": READ_PROGRESS, "as": "with_optional"},
        ],
    )
    values = result["values"]

    assert values["initial"]["now"] == "0"
    assert values["initial"]["max"] == "2"
    assert values["initial"]["label"] == "0 of 2 required questions answered"
    assert values["initial"]["describedBy"] == "progress-label"
    assert values["one_answer"]["now"] == "1"
    assert values["one_answer"]["width"] == "50%"
    assert values["both_answers"]["now"] == "2"
    assert values["both_answers"]["max"] == "2"
    assert values["both_answers"]["width"] == "100%"
    assert values["both_answers"]["label"] == "2 of 2 required questions answered"
    assert values["both_answers"]["valueText"] == "2 of 2 required questions answered"
    assert values["with_optional"] == values["both_answers"]


def test_feedback_privacy_note_is_visible_and_described(tmp_path):
    """#903: the note is present before typing and attached to the textarea."""
    result = _run_detail(
        tmp_path,
        [
            {"fn": "renderProject", "args": [PROJECT, []]},
            {"evaluate": READ_PRIVACY, "as": "form"},
        ],
    )
    state = result["values"]["form"]

    assert state["noteHidden"] is False
    # The render harness does not hydrate static text nodes into textContent;
    # assert the visible copy in the rendered markup instead.
    assert "shared privately with the maker" in result["html"]
    assert "Other visitors see your ratings only" in result["html"]
    assert state["describedBy"] == "suggestion-privacy-note suggestion-followup-hint"
    assert state["hintHidden"] is True
    assert state["counter"] == "0 / 2000"


def test_project_screenshot_style_does_not_crop():
    """The detail screenshot stays fully visible instead of a cropped strip."""
    source = DETAIL_SOURCE.read_text(encoding="utf-8")
    rule = source.split(".project-screenshot {", 1)[1].split("}", 1)[0]

    assert "object-fit: contain" in rule
    assert "height: auto" in rule
    assert "max-width: 100%" in rule
    assert "object-fit: cover" not in rule
