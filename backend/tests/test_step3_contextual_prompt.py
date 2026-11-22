"""Frontend rendering tests for Step 3 contextual follow-up prompts (#838)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "frontend"
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
        "id": 7,
        "title": "Invoice Radar",
        "description": "Tracks overdue invoices.",
        "image_url": None,
        "url": None,
        "response_count": 2,
    },
    "question": {
        "id": 1,
        "text": "Is the pricing clear?",
        "is_active": True,
        "project_id": 7,
    },
}

CONFUSING_HINT = (
    "Which part was unclear — the description, the screenshot, the pricing, or what it does?"
)
WOULD_NOT_USE_HINT = (
    "For example: you already use something similar, the value is unclear, or it is not for you."
)

READ_STEP3_JS = (
    "(function() {"
    "  var headingText = document.getElementById('suggestion-heading-text');"
    "  var hint = document.getElementById('suggestion-followup-hint');"
    "  var suggestion = document.getElementById('suggestion');"
    "  var counter = document.getElementById('suggestion-char-count');"
    "  return {"
    "    heading: headingText ? headingText.textContent : null,"
    "    placeholder: suggestion ? suggestion.placeholder : null,"
    "    value: suggestion ? suggestion.value : null,"
    "    counter: counter ? counter.textContent : null,"
    "    hintText: hint ? hint.textContent : null,"
    "    hintHidden: hint ? !!hint.hidden : null,"
    "    hintAriaLive: hint ? hint.getAttribute('aria-live') : null,"
    "    textareaAriaLive: suggestion ? suggestion.getAttribute('aria-live') : null"
    "  };"
    "})()"
)


def _dispatch_radio_change(name, value):
    return [
        {"checkInput": {"name": name, "value": value}},
        {
            "evaluate": (
                "(function() {"
                "  var form = document.getElementById('response-form');"
                f"  var ev = {{ type: 'change', target: {{ name: {json.dumps(name)}, value: {json.dumps(value)} }} }};"
                "  form.handlers.filter(function(h) { return h.type === 'change'; }).forEach(function(h) { h.fn(ev); });"
                "})()"
            ),
            "as": f"change_{name}_{value}",
        },
    ]


def _run_detail(tmp_path, calls, local_storage=None, name="scenario.json"):
    scenario = {
        "page": (FRONTEND_DIR / "project_detail.html").as_posix(),
        "calls": calls,
        "read": {"byId": "content"},
        "fetch": {},
        "location": "/project/7",
    }
    if local_storage is not None:
        scenario["localStorage"] = local_storage

    scenario_file = tmp_path / name
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


def test_default_and_positive_ratings_keep_default_step3_prompt(tmp_path):
    result = _run_detail(
        tmp_path,
        [
            {"fn": "renderProject", "args": [PROJECT, []]},
            {"evaluate": READ_STEP3_JS, "as": "initial"},
            *_dispatch_radio_change("clarity", "very_clear"),
            *_dispatch_radio_change("would_use", "yes"),
            {"evaluate": READ_STEP3_JS, "as": "positive"},
            *_dispatch_radio_change("clarity", "mostly_clear"),
            *_dispatch_radio_change("would_use", "maybe"),
            {"evaluate": READ_STEP3_JS, "as": "still_positive"},
        ],
    )

    assert '<span style="font-weight:400;color:var(--text-muted);">(optional)</span>' in result["html"]
    for key in ("initial", "positive", "still_positive"):
        state = result["values"][key]
        assert state["heading"] == "3. What would you change?"
        assert state["placeholder"] == "Your honest feedback..."
        assert state["hintText"] == ""
        assert state["hintHidden"] is True
        assert state["hintAriaLive"] == "polite"
        assert state["textareaAriaLive"] is None


def test_confusing_only_updates_step3_prompt(tmp_path):
    result = _run_detail(
        tmp_path,
        [
            {"fn": "renderProject", "args": [PROJECT, []]},
            *_dispatch_radio_change("clarity", "confusing"),
            *_dispatch_radio_change("would_use", "yes"),
            {"evaluate": READ_STEP3_JS, "as": "state"},
        ],
    )

    state = result["values"]["state"]
    assert state["heading"] == "3. What was confusing?"
    assert state["placeholder"] == CONFUSING_HINT
    assert state["hintText"] == CONFUSING_HINT
    assert state["hintHidden"] is False
    assert state["hintAriaLive"] == "polite"
    assert state["textareaAriaLive"] is None


def test_would_not_use_only_updates_step3_prompt(tmp_path):
    result = _run_detail(
        tmp_path,
        [
            {"fn": "renderProject", "args": [PROJECT, []]},
            *_dispatch_radio_change("clarity", "very_clear"),
            *_dispatch_radio_change("would_use", "no"),
            {"evaluate": READ_STEP3_JS, "as": "state"},
        ],
    )

    state = result["values"]["state"]
    assert state["heading"] == "3. Why wouldn't you use it?"
    assert state["placeholder"] == WOULD_NOT_USE_HINT
    assert state["hintText"] == WOULD_NOT_USE_HINT
    assert state["hintHidden"] is False


def test_confusing_and_would_not_use_shows_combined_prompt_and_reverts(tmp_path):
    combined = f"{CONFUSING_HINT}\n{WOULD_NOT_USE_HINT}"
    result = _run_detail(
        tmp_path,
        [
            {"fn": "renderProject", "args": [PROJECT, []]},
            *_dispatch_radio_change("clarity", "confusing"),
            *_dispatch_radio_change("would_use", "no"),
            {"evaluate": READ_STEP3_JS, "as": "both"},
            *_dispatch_radio_change("clarity", "very_clear"),
            *_dispatch_radio_change("would_use", "yes"),
            {"evaluate": READ_STEP3_JS, "as": "reverted"},
        ],
    )

    both = result["values"]["both"]
    assert both["heading"] == "3. What was confusing, and why wouldn't you use it?"
    assert both["placeholder"] == combined
    assert both["hintText"] == combined
    assert both["hintHidden"] is False

    reverted = result["values"]["reverted"]
    assert reverted["heading"] == "3. What would you change?"
    assert reverted["placeholder"] == "Your honest feedback..."
    assert reverted["hintText"] == ""
    assert reverted["hintHidden"] is True


def test_switching_ratings_preserves_typed_text_and_typing_does_not_retrigger_live_region(tmp_path):
    track_live_writes = (
        "(function() {"
        "  var hint = document.getElementById('suggestion-followup-hint');"
        "  var desc = Object.getOwnPropertyDescriptor(hint, 'textContent');"
        "  window.__hintWrites = 0;"
        "  Object.defineProperty(hint, 'textContent', {"
        "    configurable: true,"
        "    enumerable: true,"
        "    get: function() { return desc.get.call(this); },"
        "    set: function(v) { window.__hintWrites += 1; desc.set.call(this, v); }"
        "  });"
        "})()"
    )
    type_into_suggestion = (
        "(function() {"
        "  var s = document.getElementById('suggestion');"
        "  var form = document.getElementById('response-form');"
        "  s.value = 'Pricing tiers are unclear';"
        "  s.handlers.filter(function(h) { return h.type === 'input'; }).forEach(function(h) { h.fn({ type: 'input', target: s }); });"
        "  form.handlers.filter(function(h) { return h.type === 'input'; }).forEach(function(h) { h.fn({ type: 'input', target: s }); });"
        "  form.handlers.filter(function(h) { return h.type === 'change'; }).forEach(function(h) { h.fn({ type: 'change', target: s }); });"
        "})()"
    )

    result = _run_detail(
        tmp_path,
        [
            {"fn": "renderProject", "args": [PROJECT, []]},
            {"evaluate": track_live_writes, "as": "tracked"},
            *_dispatch_radio_change("clarity", "confusing"),
            {"evaluate": "window.__hintWrites", "as": "writes_after_confusing"},
            {"evaluate": type_into_suggestion, "as": "typed"},
            {"evaluate": "window.__hintWrites", "as": "writes_after_typing"},
            *_dispatch_radio_change("would_use", "no"),
            {"evaluate": READ_STEP3_JS, "as": "after_both"},
            *_dispatch_radio_change("clarity", "mostly_clear"),
            *_dispatch_radio_change("would_use", "maybe"),
            {"evaluate": READ_STEP3_JS, "as": "after_positive"},
        ],
    )

    assert result["values"]["writes_after_confusing"] == 1
    assert result["values"]["writes_after_typing"] == 1

    after_both = result["values"]["after_both"]
    assert after_both["value"] == "Pricing tiers are unclear"
    assert after_both["counter"] == "25 / 2000"
    assert after_both["heading"] == "3. What was confusing, and why wouldn't you use it?"

    after_positive = result["values"]["after_positive"]
    assert after_positive["value"] == "Pricing tiers are unclear"
    assert after_positive["counter"] == "25 / 2000"
    assert after_positive["heading"] == "3. What would you change?"


@pytest.mark.parametrize(
    ("draft", "expected_heading", "expected_hint"),
    [
        (
            {"clarity": "confusing", "would_use": "yes", "suggestion": "Hero copy is vague"},
            "3. What was confusing?",
            CONFUSING_HINT,
        ),
        (
            {"clarity": "mostly_clear", "would_use": "no", "suggestion": "Already use Stripe"},
            "3. Why wouldn't you use it?",
            WOULD_NOT_USE_HINT,
        ),
        (
            {"clarity": "confusing", "would_use": "no", "suggestion": "Need clearer demo"},
            "3. What was confusing, and why wouldn't you use it?",
            f"{CONFUSING_HINT}\n{WOULD_NOT_USE_HINT}",
        ),
    ],
)
def test_draft_restore_updates_step3_prompt_copy(tmp_path, draft, expected_heading, expected_hint):
    seed = f"sessionStorage.setItem('critique_feedback_7', {json.dumps(json.dumps(draft))})"
    result = _run_detail(
        tmp_path,
        [
            {"evaluate": seed, "as": "seeded"},
            {"fn": "renderProject", "args": [PROJECT, []]},
            {"evaluate": READ_STEP3_JS, "as": "state"},
        ],
        name=f"draft_{draft['clarity']}_{draft['would_use']}.json",
    )

    state = result["values"]["state"]
    assert state["heading"] == expected_heading
    assert state["placeholder"] == expected_hint
    assert state["hintText"] == expected_hint
    assert state["hintHidden"] is False
    assert state["value"] == draft["suggestion"]
    assert state["counter"] == f"{len(draft['suggestion'])} / 2000"
