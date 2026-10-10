"""Regression tests for the feedback results page rendering.

The results page renders every state through its own inline JavaScript, so
these tests exercise the real code path: the Node harness executes the page
and the assertions run against the exact HTML assigned to innerHTML.

Requires `node` on PATH; the whole module is skipped when it is missing.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent
FRONTEND_DIR = REPO_DIR / "frontend"
HARNESS = Path(__file__).resolve().parent / "frontend_render_harness.js"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node is required to run the frontend rendering harness",
)


def run(tmp_path, page, calls, read=None, fetch=None, location="/"):
    """Run the page's real JS in Node and return the full harness result."""
    scenario = {
        "page": (FRONTEND_DIR / page).as_posix(),
        "calls": calls,
        "read": read or {"byId": "content"},
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


def render_results(tmp_path, data, location="/project/1/results"):
    """Render the results page for `data` the way the page's loader does."""
    result = run(
        tmp_path,
        "project_results.html",
        [
            {"fn": "countResponses", "args": [data]},
            {"fn": "renderPage", "args": [data]},
        ],
        read={"byId": "content"},
        location=location,
    )
    html = result["html"]
    assert html.strip(), "page rendered no HTML"
    return html


def results_data(
    total,
    clarity,
    would_use,
    owner=False,
    responses=None,
    title="Sample Project",
    question="Would you understand this in 10 seconds?",
):
    """Build the payload GET /api/projects/{id}/results returns.

    `clarity` and `would_use` are the percentage dicts the backend sends
    (rounded to one decimal), exactly as calculated by calculate_stats().
    """
    return {
        "project_title": title,
        "question_text": question,
        "is_owner": owner,
        "responses": responses or [],
        "stats": {"total": total, "clarity": clarity, "would_use": would_use},
    }


def mixed_stats():
    """A 3-response distribution: 2 very clear/confusing + 1 confusing/no."""
    return (
        {"very_clear": 66.7, "mostly_clear": 0, "confusing": 33.3},
        {"yes": 66.7, "maybe": 0, "no": 33.3},
    )


# ---------------------------------------------------------------------------
# Header, summary cards, and bars
# ---------------------------------------------------------------------------


def test_mixed_results_show_header_question_counts_and_bars(tmp_path):
    clarity, would_use = mixed_stats()
    data = results_data(
        3,
        clarity,
        would_use,
        owner=True,
        responses=[
            {"id": 1, "clarity": "very_clear", "would_use": "yes",
             "suggestion": "Clear and useful."},
            {"id": 2, "clarity": "very_clear", "would_use": "yes",
             "suggestion": "Nice work."},
            {"id": 3, "clarity": "confusing", "would_use": "no",
             "suggestion": None},
        ],
    )
    html = render_results(tmp_path, data)

    # Compact header: section title, project name, question, exact total.
    assert "<h2>Feedback results</h2>" in html
    assert "3 total responses" in html
    assert "Sample Project" in html
    assert "Would you understand this in 10 seconds?" in html

    # Every category shows its percentage and its exact count of the total.
    assert "66.7% · 2 of 3" in html
    assert "33.3% · 1 of 3" in html
    assert "0% · 0 of 3" in html

    # The most common answer is called out in each summary card header.
    assert "Most common: </span>Very clear" in html
    assert "Most common: </span>Yes" in html

    # Sample-size note is present and flags the small sample.
    assert 'class="sample-note"' in html
    assert "Small sample" in html

    # Both actions are present and point at the right places.
    assert 'href="/project/1" class="btn btn-primary">Get more feedback' in html
    assert 'href="/discover" class="btn btn-secondary">Discover projects' in html


def test_each_percentage_appears_exactly_once(tmp_path):
    """The old page repeated every percentage in a signal card and a bar.

    Distinct percentages per category make each visible mention countable:
    every number must appear once (in its bar) and nowhere else. The only
    other occurrence of a percentage is the bar fill's width, which is a
    style attribute, not rendered text.
    """
    data = results_data(
        3,
        {"very_clear": 66.7, "mostly_clear": 0, "confusing": 33.3},
        {"yes": 100, "maybe": 0, "no": 0},
    )
    html = render_results(tmp_path, data)

    assert html.count("66.7% · 2 of 3") == 1
    assert html.count("33.3% · 1 of 3") == 1
    assert html.count("100% · 3 of 3") == 1
    assert html.count("66.7%") == 2  # visible meta + fill width, nothing more
    assert html.count("3 total responses") == 1


def test_summary_cards_and_bars_are_semantic(tmp_path):
    clarity, would_use = mixed_stats()
    html = render_results(tmp_path, results_data(3, clarity, would_use))

    # Two labelled summary cards, bar lists as real lists, decorative track
    # hidden from assistive technology (the visible text carries the numbers).
    assert '<section class="summary-card" aria-labelledby="clarity-summary-title">' in html
    assert '<section class="summary-card" aria-labelledby="would-use-summary-title">' in html
    assert html.count('<ul class="bar-list">') == 2
    assert html.count('<div class="bar-track" aria-hidden="true">') == 6
    assert '<h3 id="clarity-summary-title">How clear is it?</h3>' in html
    assert '<h3 id="would-use-summary-title">Would you use it?</h3>' in html

    # No inline event handlers may ever be rendered (XSS invariant).
    assert " onclick=" not in html
    assert " onerror=" not in html


def test_rendered_output_escapes_user_controlled_content(tmp_path):
    """Quotes and angle brackets in title/question/suggestion stay literal."""
    data = results_data(
        1,
        {"very_clear": 100, "mostly_clear": 0, "confusing": 0},
        {"yes": 100, "maybe": 0, "no": 0},
        owner=True,
        title='t" onmouseover="alert(2)',
        question="Ampersand & <angle> check",
        responses=[
            {"id": 1, "clarity": "very_clear", "would_use": "yes",
             "suggestion": 'nice work" onmouseover="alert(9)'},
        ],
    )
    html = render_results(tmp_path, data)

    assert "onmouseover" in html  # the text round-trips...
    assert ' onmouseover="' not in html  # ...but never as a real attribute
    assert "&quot;" in html  # attribute-context escaping happened


# ---------------------------------------------------------------------------
# Zero, one, and larger response counts
# ---------------------------------------------------------------------------


def test_zero_responses_renders_empty_state_with_both_actions(tmp_path):
    html = render_results(
        tmp_path,
        results_data(
            0,
            {"very_clear": 0, "mostly_clear": 0, "confusing": 0},
            {"yes": 0, "maybe": 0, "no": 0},
        ),
    )

    assert "No feedback yet" in html
    assert "0 total responses" in html
    # The question is preserved even with no answers yet.
    assert "Would you understand this in 10 seconds?" in html
    # Both standard actions, no bars, no broken arithmetic.
    assert "Get more feedback" in html
    assert "Discover projects" in html
    assert "bar-track" not in html
    assert "sample-note" not in html
    for artifact in ("NaN", "Infinity", "undefined"):
        assert artifact not in html


def test_single_response_is_exact_and_humble(tmp_path):
    data = results_data(
        1,
        {"very_clear": 100, "mostly_clear": 0, "confusing": 0},
        {"yes": 100, "maybe": 0, "no": 0},
        owner=True,
        responses=[
            {"id": 1, "clarity": "very_clear", "would_use": "yes",
             "suggestion": "So clear."},
        ],
    )
    html = render_results(tmp_path, data)

    assert "100% · 1 of 1" in html
    assert "1 total response" in html
    assert "1 total responses" not in html
    assert "Based on 1 response" in html
    assert "not a pattern" in html
    assert "So clear." in html
    for artifact in ("NaN", "Infinity", "undefined"):
        assert artifact not in html


def test_larger_sample_uses_neutral_wording_and_exact_counts(tmp_path):
    """Counts recovered from rounded percentages must sum to the total."""
    html = render_results(
        tmp_path,
        results_data(
            12,
            {"very_clear": 50, "mostly_clear": 41.7, "confusing": 8.3},
            {"yes": 50, "maybe": 41.7, "no": 8.3},
        ),
    )

    assert "12 total responses" in html
    assert "50% · 6 of 12" in html
    assert "41.7% · 5 of 12" in html
    assert "8.3% · 1 of 12" in html

    # Wording stays honest: shares of the sample, never significance.
    assert "Based on 12 responses" in html
    assert "not statistical measures" in html
    assert "Small sample" not in html
    for phrase in ("statistically significant", "guaranteed", "proven"):
        assert phrase not in html


def test_public_view_shows_stats_without_written_feedback(tmp_path):
    clarity, would_use = mixed_stats()
    html = render_results(
        tmp_path,
        results_data(2, clarity, would_use, owner=False, responses=[]),
    )

    assert "2 total responses" in html
    assert "66.7% · ?" not in html  # counts are derived, never unknown
    assert "Written feedback" not in html


# ---------------------------------------------------------------------------
# Written feedback prominence
# ---------------------------------------------------------------------------


def test_written_feedback_comment_leads_choices_follow(tmp_path):
    data = results_data(
        2,
        {"very_clear": 100, "mostly_clear": 0, "confusing": 0},
        {"yes": 100, "maybe": 0, "no": 0},
        owner=True,
        responses=[
            {"id": 1, "clarity": "very_clear", "would_use": "yes",
             "suggestion": "Please add pricing."},
            {"id": 2, "clarity": "very_clear", "would_use": "yes",
             "suggestion": None},
        ],
    )
    html = render_results(tmp_path, data)

    assert "Written feedback" in html
    # Only the response with a suggestion is listed.
    assert "Please add pricing." in html

    # The comment is the primary content; choices are secondary metadata
    # rendered after it.
    comment_pos = html.index("Please add pricing.")
    meta_pos = html.index("Clarity: ")
    assert comment_pos < meta_pos, "comment must render before its metadata"
    assert html.index('class="feedback-text"') < html.index('class="feedback-meta"')
    assert "Would use: Yes" in html


# ---------------------------------------------------------------------------
# Count derivation math (percentages -> exact counts)
# ---------------------------------------------------------------------------


DERIVE_CASES = [
    # (percentages, total, expected [very_clear, mostly_clear, confusing])
    ({"very_clear": 33.3, "mostly_clear": 33.3, "confusing": 33.3}, 3, [1, 1, 1]),
    ({"very_clear": 66.7, "mostly_clear": 0, "confusing": 33.3}, 3, [2, 0, 1]),
    ({"very_clear": 100, "mostly_clear": 0, "confusing": 0}, 1, [1, 0, 0]),
    ({"very_clear": 0, "mostly_clear": 0, "confusing": 100}, 1, [0, 0, 1]),
    ({"very_clear": 50, "mostly_clear": 41.7, "confusing": 8.3}, 12, [6, 5, 1]),
    ({"very_clear": 42.9, "mostly_clear": 57.1, "confusing": 0}, 7, [3, 4, 0]),
    # Percentages that do not sum to 100 because of per-key rounding.
    ({"very_clear": 33.4, "mostly_clear": 33.3, "confusing": 33.3}, 1000, [334, 333, 333]),
]


@pytest.mark.parametrize("pcts,total,expected", DERIVE_CASES)
def test_derive_counts_match_expectations_and_sum_to_total(tmp_path, pcts, total, expected):
    result = run(
        tmp_path,
        "project_results.html",
        [{"evaluate": "deriveCounts(" + json.dumps(pcts) + ", " + str(total) + ")",
          "as": "counts"}],
        location="/project/1/results",
    )
    counts = result["values"]["counts"]
    values = [counts["very_clear"], counts["mostly_clear"], counts["confusing"]]
    assert values == expected, f"got {values}, want {expected}"
    assert sum(values) == total


def test_derive_counts_survives_zero_total(tmp_path):
    """No division by zero: every count is 0 when there is nothing to count."""
    result = run(
        tmp_path,
        "project_results.html",
        [{"evaluate": "deriveCounts({very_clear: 50, mostly_clear: 50, confusing: 0}, 0)",
          "as": "counts"}],
        location="/project/1/results",
    )
    counts = result["values"]["counts"]
    assert counts == {"very_clear": 0, "mostly_clear": 0, "confusing": 0}


def test_format_pct_strips_float_noise(tmp_path):
    result = run(
        tmp_path,
        "project_results.html",
        [
            {"evaluate": "formatPct(66.70000000000001)", "as": "a"},
            {"evaluate": "formatPct(100)", "as": "b"},
            {"evaluate": "formatPct(0)", "as": "c"},
            {"evaluate": "formatPct(NaN)", "as": "d"},
        ],
        location="/project/1/results",
    )
    values = result["values"]
    assert values["a"] == "66.7"
    assert values["b"] == "100"
    assert values["c"] == "0"
    assert values["d"] == "0"


# ---------------------------------------------------------------------------
# Runtime back link and API failure state
# ---------------------------------------------------------------------------


def test_back_link_is_filled_from_the_path_at_runtime(tmp_path):
    """The static markup ships href="/" and the script points it at the
    project -- the pre-redesign markup shipped a literal broken href."""
    source = (FRONTEND_DIR / "project_results.html").read_text(encoding="utf-8")
    assert '<a id="back-link" href="/"' in source
    assert ">Back to project</a>" in source
    assert "' + projectId + '" not in source, "no unexpanded template text"
    # The results fetch encodes the path segment like the back link does.
    assert "encodeURIComponent(String(projectId))" in source

    result = run(
        tmp_path,
        "project_results.html",
        [
            {"evaluate": "document.getElementById('back-link').getAttribute('href')",
             "as": "back_href"},
        ],
        location="/project/42/results",
    )
    assert result["values"]["back_href"] == "/project/42"


def test_api_failure_renders_the_friendly_error_state(tmp_path):
    """A failed results fetch lands on the friendly error state, never on a
    half-rendered page or raw error text."""
    # No route mocked: the harness answers /api/... with 404.
    result = run(
        tmp_path,
        "project_results.html",
        [{"fn": "loadResults", "args": []}],
        location="/project/7/results",
    )
    html = result["html"]
    assert 'class="error-state"' in html
    assert "Something went wrong. Please try again." in html
    assert "bar-track" not in html
    for artifact in ("NaN", "Infinity", "undefined", "[object Object]"):
        assert artifact not in html
