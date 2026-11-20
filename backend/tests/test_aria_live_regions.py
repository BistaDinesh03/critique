"""Dynamic homepage updates are announced politely, once, and without cards.

The stats strip is one atomic polite status (so a refresh reads as one
sentence, not three loose numbers), and the project grid has a separate
polite summary like discover.html's, so screen readers hear "Showing 1
project" instead of every card.
"""

import re

from tests.test_loading_ux import FRONTEND_DIR, PROJECT_ITEM, PROJECTS_URL, run


def index_source():
    return (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")


def tag(source, element_id):
    match = re.search(r'<[^>]*\bid="%s"[^>]*>' % element_id, source)
    assert match, f"#{element_id} missing"
    return match.group(0)


def test_stats_strip_is_one_atomic_polite_status():
    stats = tag(index_source(), "real-activity")
    assert 'aria-live="polite"' in stats
    assert 'role="status"' in stats
    assert 'aria-atomic="true"' in stats


def test_stat_values_are_not_individually_live():
    source = index_source()
    for element_id in ("stat-projects", "stat-responses", "stat-questions"):
        assert "aria-live" not in tag(source, element_id)


def test_social_proof_text_is_an_atomic_polite_status():
    proof = tag(index_source(), "social-proof-text")
    assert 'aria-live="polite"' in proof
    assert 'aria-atomic="true"' in proof


def test_homepage_project_summary_is_a_polite_status_outside_the_grid():
    source = index_source()
    status = tag(source, "homepage-projects-status")
    assert 'class="sr-only"' in status
    assert 'role="status"' in status
    assert 'aria-live="polite"' in status
    # The grid itself is not live: replacing cards must not re-read them.
    assert "aria-live" not in tag(source, "homepage-projects")


def test_homepage_announces_project_count_not_cards(tmp_path):
    result = run(
        tmp_path,
        "index.html",
        [{"fn": "loadHomepageProjects", "args": []}],
        fetch={PROJECTS_URL: {"status": 200, "body": {"items": [PROJECT_ITEM], "total": 1}}},
    )
    assert result["ids"]["homepage-projects-status"] == "Showing 1 project."


def test_homepage_announces_plural_count(tmp_path):
    items = [dict(PROJECT_ITEM, id=i) for i in (1, 2, 3)]
    result = run(
        tmp_path,
        "index.html",
        [{"fn": "loadHomepageProjects", "args": []}],
        fetch={PROJECTS_URL: {"status": 200, "body": {"items": items, "total": 3}}},
    )
    assert result["ids"]["homepage-projects-status"] == "Showing 3 projects."


def test_homepage_announces_empty_list(tmp_path):
    result = run(
        tmp_path,
        "index.html",
        [{"fn": "loadHomepageProjects", "args": []}],
        fetch={PROJECTS_URL: {"status": 200, "body": {"items": [], "total": 0}}},
    )
    assert result["ids"]["homepage-projects-status"] == "No projects waiting for feedback yet."


def test_homepage_failure_is_not_announced_twice(tmp_path):
    # The error box already has role="alert"; the summary stays silent.
    result = run(
        tmp_path,
        "index.html",
        [{"fn": "loadHomepageProjects", "args": []}],
        fetch={PROJECTS_URL: {"status": 500, "body": {}}},
    )
    assert result["ids"]["homepage-projects-status"] == ""
    classes = [meta["className"] for meta in result["createdMeta"]]
    assert "error-state" in classes
