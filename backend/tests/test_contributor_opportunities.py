"""Tests for docs/contributor-opportunities.md and the README shortlist.

These tests run offline and read the real files on disk. They check the page's
structure, that every issue reference points at this repository, and that an
issue cannot be advertised as available while it is also listed as in progress.

The live open/closed state is checked against GitHub when the page is refreshed
(see the "Last verified" line in the document). A unit test must never make a
network call, so the closed-issue and duplicate guards below use the small set of
numbers that were removed during the 2026-11-14 refresh.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "contributor-opportunities.md"
README = ROOT / "README.md"

REPO = "BistaDinesh03/critique"
ISSUE_URL = re.compile(
    r"https://github\.com/" + re.escape(REPO) + r"/issues/(\d+)"
)
ANY_ISSUE_URL = re.compile(r"https://github\.com/([^/\s)]+)/([^/\s)]+)/issues/(\d+)")

# Issues closed before or during the 2026-11-14 refresh. They must never be
# advertised as available again.
KNOWN_CLOSED = {82, 225, 279, 330, 349, 350, 370, 526}

# #713 duplicates #88's request-logging proposal; only one may be listed.
KNOWN_DUPLICATE = {713}

SECTION_START = "Start here"
SECTION_MORE = "More open work"
SECTION_PROGRESS = "Work in progress"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _split_sections(text: str) -> dict[str, str]:
    """Split Markdown on level-two headings; keep the preamble separately."""
    sections: dict[str, str] = {}
    current = "__preamble__"
    buffer: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            sections[current] = "\n".join(buffer)
            current = match.group(1)
            buffer = []
        else:
            buffer.append(line)
    sections[current] = "\n".join(buffer)
    return sections


def _section(sections: dict[str, str], prefix: str) -> str:
    for heading, body in sections.items():
        if heading.startswith(prefix):
            return body
    raise AssertionError(f"missing section starting with {prefix!r}")


def _issue_numbers(text: str) -> list[int]:
    return [int(number) for number in ISSUE_URL.findall(text)]


def _available_numbers(text: str) -> list[int]:
    sections = _split_sections(text)
    return (
        _issue_numbers(_section(sections, SECTION_START))
        + _issue_numbers(_section(sections, SECTION_MORE))
    )


def _in_progress_numbers(text: str) -> list[int]:
    sections = _split_sections(text)
    return _issue_numbers(_section(sections, SECTION_PROGRESS))


def _glance_counts(text: str) -> dict[str, int]:
    patterns = {
        "total": r"\*\*(\d+) open issues\*\*",
        "listed": r"\*\*(\d+) are listed here as available\*\*",
        "progress": r"\*\*(\d+) are in progress\*\*",
        "not_recommended": r"\*\*(\d+) are not recommended by this page\*\*",
        "split": r"\((\d+)\s+in\s+\*Start here\*,\s+(\d+)\s+in\s+\*More open work\*\)",
    }
    counts: dict[str, int] = {}
    for name, pattern in patterns.items():
        match = re.search(pattern, text, re.S)
        assert match, f"missing 'at a glance' count: {name}"
        if name == "split":
            counts["start"], counts["more"] = (int(match.group(1)), int(match.group(2)))
        else:
            counts[name] = int(match.group(1))
    return counts


def test_document_and_readme_exist():
    assert DOC.is_file(), "docs/contributor-opportunities.md is missing"
    assert README.is_file(), "README.md is missing"


def test_required_sections_present():
    sections = _split_sections(_read(DOC))
    for heading in (SECTION_START, SECTION_MORE, SECTION_PROGRESS,
                    "How to claim an issue", "How this list is kept accurate"):
        assert any(key.startswith(heading) for key in sections), (
            f"missing required section: {heading}"
        )


def test_issue_links_use_this_repository():
    text = _read(DOC)
    links = ANY_ISSUE_URL.findall(text)
    assert links, "no GitHub issue links found"
    wrong = {(owner, repo) for owner, repo, _ in links
             if f"{owner}/{repo}" != REPO}
    assert not wrong, f"issue links point at the wrong repository: {sorted(wrong)}"
    assert ISSUE_URL.findall(text), "no canonical issue links found"


def test_available_and_in_progress_do_not_overlap():
    text = _read(DOC)
    available = set(_available_numbers(text))
    in_progress = set(_in_progress_numbers(text))
    overlap = available & in_progress
    assert not overlap, f"issues listed as both available and in progress: {sorted(overlap)}"


def test_available_issues_are_not_duplicated():
    available = _available_numbers(_read(DOC))
    duplicates = {n for n in available if available.count(n) > 1}
    assert not duplicates, f"duplicate available issues: {sorted(duplicates)}"


def test_glance_counts_match_the_tables():
    text = _read(DOC)
    counts = _glance_counts(text)
    available = _available_numbers(text)
    in_progress = _in_progress_numbers(text)

    assert counts["listed"] == len(available) == len(set(available))
    assert counts["start"] + counts["more"] == counts["listed"]
    assert counts["start"] == len(_issue_numbers(_section(_split_sections(text), SECTION_START)))
    assert counts["more"] == len(_issue_numbers(_section(_split_sections(text), SECTION_MORE)))
    assert counts["progress"] == len(set(in_progress))
    assert counts["total"] == (
        counts["listed"] + counts["progress"] + counts["not_recommended"]
    ), "the at-a-glance counts do not add up to the open-issue total"


def test_closed_and_duplicate_issues_are_not_available():
    available = set(_available_numbers(_read(DOC)))
    leaked_closed = available & KNOWN_CLOSED
    leaked_duplicates = available & KNOWN_DUPLICATE
    assert not leaked_closed, f"closed issues advertised as available: {sorted(leaked_closed)}"
    assert not leaked_duplicates, (
        f"duplicate opportunities advertised as available: {sorted(leaked_duplicates)}"
    )


def test_issue_with_open_pull_request_is_in_progress_not_available():
    """#773 has PR #775. A closed/claimed issue must not be advertised as free."""
    text = _read(DOC)
    available = set(_available_numbers(text))
    in_progress = set(_in_progress_numbers(text))
    assert 773 not in available
    assert 773 in in_progress


def test_readme_snapshot_is_subset_of_start_here():
    readme = _read(README)
    match = re.search(r"### Good issues to contribute\n(.*?)(?=\n## |\Z)", readme, re.S)
    assert match, "README is missing the 'Good issues to contribute' section"

    readme_numbers = _issue_numbers(match.group(1))
    assert readme_numbers, "README shortlist has no issue links"
    assert len(readme_numbers) == len(set(readme_numbers)), (
        "README shortlist contains a duplicate issue"
    )

    start_here = set(_issue_numbers(_section(_split_sections(_read(DOC)), SECTION_START)))
    missing = set(readme_numbers) - start_here
    assert not missing, (
        "README shortlist issues are not in the verified 'Start here' list: "
        f"{sorted(missing)}"
    )


def test_helpers_detect_duplicates_and_overlap():
    """Prove the parser fails on the mistakes these tests are meant to catch."""
    text = (
        "## Start here\n"
        f"[#1](https://github.com/{REPO}/issues/1)\n"
        f"[#1](https://github.com/{REPO}/issues/1)\n"
        "## More open work\n"
        f"[#2](https://github.com/{REPO}/issues/2)\n"
        f"## {SECTION_PROGRESS} — please don't duplicate\n"
        f"[#2](https://github.com/{REPO}/issues/2)\n"
    )
    available = _available_numbers(text)
    in_progress = _in_progress_numbers(text)
    assert available.count(1) == 2
    assert set(available) & set(in_progress) == {2}
