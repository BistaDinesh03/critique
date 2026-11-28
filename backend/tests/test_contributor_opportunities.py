"""Tests for docs/contributor-opportunities.md and the README shortlist.

These tests run offline and read the real files on disk. They check the page's
structure, that every issue reference points at this repository, and that an
issue cannot be advertised as available while it is also listed as in progress.

The live open/closed state is checked against GitHub when the page is refreshed
(see the "Last checked" line in the document). A unit test must never make a
network call, so the closed-issue and duplicate guards below use the numbers
removed during the 2026-11-28 refresh.
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

# Issues closed before or during the 2026-11-28 refresh. They must never be
# advertised as available again.
KNOWN_CLOSED = {
    21, 31, 32, 77, 82, 143, 163, 225, 279, 330, 349, 350, 362, 370, 526,
    765, 766, 767, 768, 770, 772, 773, 774,
}

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


def test_closed_and_duplicate_issues_are_not_available():
    available = set(_available_numbers(_read(DOC)))
    leaked_closed = available & KNOWN_CLOSED
    leaked_duplicates = available & KNOWN_DUPLICATE
    assert not leaked_closed, f"closed issues advertised as available: {sorted(leaked_closed)}"
    assert not leaked_duplicates, (
        f"duplicate opportunities advertised as available: {sorted(leaked_duplicates)}"
    )


def test_claimed_issue_is_in_progress_not_available():
    """#909 is assigned and has an open PR, so it must not be advertised as free."""
    text = _read(DOC)
    available = set(_available_numbers(text))
    in_progress = set(_in_progress_numbers(text))
    assert 909 not in available
    assert 909 in in_progress


def test_document_points_to_live_sources():
    text = _read(DOC)
    assert "Last checked against the live tracker" in text
    for target in (
        "labels/good%20first%20issue",
        "labels/help%20wanted",
        "/issues",
        "/pulls",
    ):
        assert target in text, f"missing live source link: {target}"


def test_readme_links_to_verified_contributor_opportunities():
    readme = _read(README)
    assert "docs/contributor-opportunities.md" in readme, (
        "README must link to the verified contributor opportunities list"
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
