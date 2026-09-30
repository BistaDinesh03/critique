"""Freshness and card hierarchy: every label comes from the API's own data.

Phases 6-8 of the UX pass asked the lists to say *when* a project was shared
and *how much help* it already has, without inventing a single number. The
timestamps were already in the list response (``created_at``), so this is
pure frontend work: one small formatter per page (no date library), a meta
line built from the response count plus that timestamp, and header copy that
describes what the backend really returns instead of claiming "trending" or
"active now" -- activity this product does not track.

These tests run the page's real JavaScript inside the Node rendering harness
(formatting is unit-tested through ``formatAge`` directly) and read the card
markup the pages actually render.

Requires ``node`` on PATH; the whole module is skipped when it is missing.
"""

import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
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
# Both lists render projects, so both pages carry the same formatter.
PAGES_WITH_FORMATTER = ["index.html", "discover.html"]


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


def ages(tmp_path, page, stamps):
    """``formatAge``'s label for each timestamp, read back from the page."""
    calls = [
        {"evaluate": "formatAge(" + json.dumps(stamp) + ")", "as": f"age{i}"}
        for i, stamp in enumerate(stamps)
    ]
    result = run(tmp_path, page, calls)
    return [result["values"][f"age{i}"] for i in range(len(stamps))]


def served(value):
    """A timestamp the way the API serves it: naive UTC, microsecond precision."""
    return value.strftime("%Y-%m-%dT%H:%M:%S.%f")


def short_date(value):
    """The formatter's fallback: 'Aug 21' (+ ', YYYY' in another year)."""
    label = value.strftime("%b ") + str(value.day)
    if value.year != datetime.now(timezone.utc).year:
        label += ", " + str(value.year)
    return label


# ---------------------------------------------------------------------------
# The formatter itself (Phase 6)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("page", PAGES_WITH_FORMATTER)
def test_format_age_reports_fresh_projects_in_plain_language(tmp_path, page):
    now = datetime.now(timezone.utc)

    def ago(**kwargs):
        return (now - timedelta(**kwargs)).strftime("%Y-%m-%dT%H:%M:%S")

    labels = ages(
        tmp_path,
        page,
        [
            ago(seconds=10),
            ago(minutes=45),
            ago(hours=2, minutes=5),
            ago(hours=5, minutes=5),
            ago(hours=26),
            ago(days=3, hours=2),
        ],
    )

    assert labels == ["Just now", "45m ago", "2h ago", "5h ago", "Yesterday", "3 days ago"]


@pytest.mark.parametrize("page", PAGES_WITH_FORMATTER)
def test_format_age_falls_back_to_a_short_date(tmp_path, page):
    old = datetime.now(timezone.utc) - timedelta(days=40)

    # Three shapes of the same moment -- plain, with the microseconds production
    # serves, and with an explicit offset -- must all read the same.
    labels = ages(
        tmp_path,
        page,
        [
            old.strftime("%Y-%m-%dT%H:%M:%S"),
            served(old),
            old.strftime("%Y-%m-%dT%H:%M:%SZ"),
        ],
    )

    assert labels == [short_date(old)] * 3


@pytest.mark.parametrize("page", PAGES_WITH_FORMATTER)
def test_format_age_pins_offsetless_timestamps_to_the_utc_date(tmp_path, page):
    """Both edges of a UTC day keep that date in every visitor timezone.

    The API serves UTC without an offset, so reading it as local time would
    date the same project differently for a visitor six hours away.
    """
    stamps = [
        "2026-01-05T02:00:00",
        "2026-01-05T23:00:00",
        "2026-01-05T02:00:00Z",
        "2026-01-05T23:00:00Z",
        "2026-01-05T23:00:00.392996",
    ]

    assert ages(tmp_path, page, stamps) == [short_date(datetime(2026, 1, 5))] * 5


@pytest.mark.parametrize("page", PAGES_WITH_FORMATTER)
def test_format_age_never_invents_an_age(tmp_path, page):
    ahead = datetime.now(timezone.utc) + timedelta(hours=2)

    labels = ages(tmp_path, page, [None, "", "not-a-date", served(ahead)])

    # Missing or unparsable data shows nothing at all...
    assert labels[:3] == ["", "", ""]
    # ...and a clock ahead of the server never reads as an age.
    assert labels[3] == "Just now"


# ---------------------------------------------------------------------------
# The cards (Phase 7)
# ---------------------------------------------------------------------------


def test_discover_card_shows_question_count_age_and_action(tmp_path):
    created = datetime.now(timezone.utc) - timedelta(hours=5, minutes=5)
    item = {
        "id": 7,
        "title": "Ship the thing",
        "description": "A short description",
        "question_text": "Is the pricing clear?",
        "response_count": 3,
        "image_url": None,
        "created_at": created.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    result = run(tmp_path, "discover.html", [{"fn": "showProjects", "args": [[item]]}])
    html = " ".join(result["created"])

    # Hierarchy: what it is, what it does, then the question being asked.
    assert html.index("Ship the thing") < html.index("A short description")
    assert html.index("A short description") < html.index("Is the pricing clear?")
    # Then how much help it already has, and how recently it was shared.
    assert "3 responses" in html
    assert "5h ago" in html
    assert '<time datetime="' + item["created_at"] + '">' in html
    # The action, named for assistive technology and pointing at the project.
    assert "Give feedback" in html
    assert '<a href="/project/7"' in html
    assert 'aria-label="Give feedback on Ship the thing"' in html


def test_discover_card_invents_nothing_when_the_api_omits_data(tmp_path):
    item = {
        "id": 8,
        "title": "Bare project",
        "description": None,
        "question_text": None,
        "response_count": 0,
        "image_url": None,
    }

    result = run(tmp_path, "discover.html", [{"fn": "showProjects", "args": [[item]]}])
    html = " ".join(result["created"])

    assert "Needs feedback" in html
    assert "No description provided." in html
    assert "No question" in html
    # No timestamp, no age -- and never a separator left hanging on its own.
    assert "<time" not in html
    assert "·" not in html
    assert "Just now" not in html


def test_homepage_preview_shows_description_question_count_and_age(tmp_path):
    created = datetime.now(timezone.utc) - timedelta(days=3, hours=2)
    item = {
        "id": 7,
        "title": "Ship the thing",
        "description": "A short description",
        "question_text": "Is the pricing clear?",
        "response_count": 2,
        "image_url": None,
        "created_at": created.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    result = run(
        tmp_path,
        "index.html",
        [{"fn": "loadHomepageProjects", "args": []}],
        fetch={
            HOMEPAGE_URL: {"status": 200, "body": {"total": 1, "items": [item]}},
        },
    )
    html = result["ids"]["homepage-projects"]

    assert html.index("Ship the thing") < html.index("A short description")
    assert html.index("A short description") < html.index("Is the pricing clear?")
    assert "Question: Is the pricing clear?" in html
    assert "2 responses" in html
    assert "3 days ago" in html
    assert '<time datetime="' + item["created_at"] + '">' in html
    assert "Give feedback" in html


# ---------------------------------------------------------------------------
# What the lists claim to be (Phase 8)
# ---------------------------------------------------------------------------


def test_discover_header_describes_what_the_backend_actually_returns():
    source = (FRONTEND_DIR / "discover.html").read_text(encoding="utf-8")

    # The page states the real thing on offer: projects a builder shared,
    # each with one question waiting.
    assert "Real projects looking for feedback." in source
    assert "a single question waiting for an honest answer" in source
    # Freshness is shown as data (the age on every card) -- never as a claim
    # about live or trending activity this product does not track.
    lowered = source.lower()
    for claim in ("trending", "active now", "live now", "just posted"):
        assert claim not in lowered, claim
