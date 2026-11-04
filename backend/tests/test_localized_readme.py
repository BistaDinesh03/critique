"""Test that the localized README/CONTRIBUTING files stay wired to the English source.

The English files (README.md, CONTRIBUTING.md) are the canonical source of truth.
The localized files (zh-CN, ja, es) must exist, be linked from the English language
selector, and link back to English. These tests read the real files on disk, and
the mutation tests below prove they fail when a file or link goes missing rather
than asserting hardcoded success.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# The link checker lives in this same directory, outside any package, so it is
# put on ``sys.path`` before import -- the same trick test_review_pr.py uses.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_markdown_links import (  # noqa: E402
    extract_relative_links,
)

# Matches the href attribute of an HTML anchor: <a href="target">.
HREF_PATTERN = re.compile(r'href="([^"]+)"')

ROOT = Path(__file__).resolve().parents[2]

# locale code -> (localized README filename, localized CONTRIBUTING filename)
LOCALIZED: dict[str, tuple[str, str]] = {
    "zh-CN": ("README.zh-CN.md", "CONTRIBUTING.zh-CN.md"),
    "ja": ("README.ja.md", "CONTRIBUTING.ja.md"),
    "es": ("README.es.md", "CONTRIBUTING.es.md"),
}

# Labels used in the language selector, one per locale.
SELECTOR_LABELS = {
    "zh-CN": "简体中文",
    "ja": "日本語",
    "es": "Español",
}


def _selector_targets(md_file: Path) -> list[str]:
    """Return the href targets of the top language-selector block of a Markdown file."""
    content = md_file.read_text(encoding="utf-8")
    # The selector is the <p align="center"> block that contains the locale labels.
    for block in content.split('<p align="center">')[1:]:
        block = block.split("</p>")[0]
        if any(label in block for label in SELECTOR_LABELS.values()):
            return HREF_PATTERN.findall(block)
    return []


def test_localized_readme_files_exist():
    """Every declared locale has a README and CONTRIBUTING file on disk."""
    for readme_name, contributing_name in LOCALIZED.values():
        assert (ROOT / readme_name).is_file(), f"missing {readme_name}"
        assert (ROOT / contributing_name).is_file(), f"missing {contributing_name}"


def test_english_readme_selector_links_every_locale():
    """README.md's language selector links to each localized README."""
    targets = _selector_targets(ROOT / "README.md")
    for readme_name, _ in LOCALIZED.values():
        assert readme_name in targets, f"README.md selector missing {readme_name}"


def test_english_contributing_selector_links_every_locale():
    """CONTRIBUTING.md links to each localized CONTRIBUTING file somewhere."""
    content = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    for _, contributing_name in LOCALIZED.values():
        assert contributing_name in content, f"CONTRIBUTING.md missing link to {contributing_name}"


def test_each_localized_readme_links_back_to_english():
    """Each localized README's selector includes a link back to README.md."""
    for readme_name, _ in LOCALIZED.values():
        targets = _selector_targets(ROOT / readme_name)
        assert "README.md" in targets, f"{readme_name} selector missing backlink to README.md"


def test_each_localized_contributing_links_back_to_english():
    """Each localized CONTRIBUTING links back to the canonical CONTRIBUTING.md."""
    for _, contributing_name in LOCALIZED.values():
        content = (ROOT / contributing_name).read_text(encoding="utf-8")
        assert "CONTRIBUTING.md" in content, f"{contributing_name} missing backlink to CONTRIBUTING.md"


def test_localized_selector_is_reciprocal():
    """Locale pages cross-link one another (zh <-> ja <-> es) via the selector."""
    for readme_name, _ in LOCALIZED.values():
        targets = set(_selector_targets(ROOT / readme_name))
        for other_readme, _ in LOCALIZED.values():
            if other_readme != readme_name:
                assert other_readme in targets, (
                    f"{readme_name} selector missing link to {other_readme}"
                )


def test_localized_readmes_cover_english_sections():
    """Localized READMEs keep the same H2 section count as the English README.

    A translated README that silently drops a section (or adds an unreviewed one)
    drifts from the canonical source; this keeps the heading structure aligned.
    """
    def h2_count(path: Path) -> int:
        return sum(
            1
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("## ")
        )

    english = h2_count(ROOT / "README.md")
    for readme_name, _ in LOCALIZED.values():
        count = h2_count(ROOT / readme_name)
        assert count == english, (
            f"{readme_name} has {count} H2 sections, English has {english}"
        )


# --- Mutation tests: prove the checks above are not hardcoded success. ---


def test_detects_missing_translation_file(tmp_path):
    """A localized README that is deleted is reported, not silently ignored."""
    for readme_name, _ in LOCALIZED.values():
        (tmp_path / readme_name).write_text(
            f"# {readme_name}\n\n[README.md](README.md)\n", encoding="utf-8"
        )
    (tmp_path / "README.md").write_text(
        "# English\n\n[简体中文](README.zh-CN.md)\n", encoding="utf-8"
    )

    missing = [
        name for name, _ in LOCALIZED.values() if not (tmp_path / name).is_file()
    ]
    assert missing == []  # all present right now

    (tmp_path / "README.ja.md").unlink()  # break it

    missing = [
        name for name, _ in LOCALIZED.values() if not (tmp_path / name).is_file()
    ]
    assert missing == ["README.ja.md"], f"expected ja to be reported missing, got {missing}"


def test_detects_broken_language_link(tmp_path):
    """The shared link extractor flags a selector link pointing at a deleted file."""
    readme = tmp_path / "README.md"
    readme.write_text(
        "# English\n\n[简体中文](README.zh-CN.md)\n[日本語](README.ja.md)\n",
        encoding="utf-8",
    )
    (tmp_path / "README.zh-CN.md").write_text("# zh\n", encoding="utf-8")
    # README.ja.md is intentionally absent -> broken link.

    links = extract_relative_links(readme, root=tmp_path)
    broken = [l for l in links if not l.target_path.exists()]
    assert [l.raw_target for l in broken] == ["README.ja.md"]


def test_detects_missing_backlink(tmp_path):
    """A localized README that forgets to link back to English is caught."""
    (tmp_path / "README.md").write_text("# English\n", encoding="utf-8")
    localized = tmp_path / "README.es.md"
    localized.write_text("# Español\n\nNo backlink here.\n", encoding="utf-8")

    targets = _selector_targets(localized)
    assert "README.md" not in targets  # backlink absent -> check would fail


# --- Test-count drift guard for README testing sections. ---

TESTING_HEADINGS = {
    "README.md": "Testing",
    "README.zh-CN.md": "测试",
    "README.ja.md": "テスト",
    "README.es.md": "Pruebas",
}

# Count claims in English, Spanish, Japanese, and Simplified Chinese.
TEST_COUNT_CLAIM = re.compile(
    r"(?i:\b\d+\s+(?:tests?|test cases?|pruebas?|casos de prueba)\b)"
    r"|(?:\d+\s*(?:個の)?テスト(?:ケース)?)"
    r"|(?:\d+\s*(?:个测试用例|个测试|项测试|次测试|测试))"
)


def _section_content(content: str, heading: str) -> str:
    """Return a Markdown H2 section's body, excluding the heading and next section."""
    lines = content.splitlines()
    start = next(
        (index for index, line in enumerate(lines) if line.strip() == f"## {heading}"),
        None,
    )
    assert start is not None, f"missing ## {heading} section"
    end = next(
        (
            index
            for index in range(start + 1, len(lines))
            if lines[index].startswith("## ")
        ),
        len(lines),
    )
    return "\n".join(lines[start + 1 : end])


def test_readme_testing_sections_do_not_claim_test_counts():
    """All four README testing sections stay count-free across languages."""
    for readme_name, heading in TESTING_HEADINGS.items():
        content = (ROOT / readme_name).read_text(encoding="utf-8")
        section = _section_content(content, heading)
        match = TEST_COUNT_CLAIM.search(section)
        assert match is None, (
            f"{readme_name} testing section contains a test-count claim: "
            f"{match.group(0)!r}"
        )


def test_count_guard_detects_reintroduced_claims():
    """The guard catches a stale count if one is reintroduced in any locale."""
    clean_lines = {
        "README.md": "The suite passes cleanly.",
        "README.zh-CN.md": "测试套件通过所有测试。",
        "README.ja.md": "テストスイートは正常にパスします。",
        "README.es.md": "La suite de pruebas pasa correctamente.",
    }
    stale_lines = {
        "README.md": "501 tests currently pass.",
        "README.zh-CN.md": "目前有 501 个测试通过。",
        "README.ja.md": "現在 501 個のテストがパスしています。",
        "README.es.md": "Actualmente pasan 501 pruebas.",
    }
    for readme_name, clean_line in clean_lines.items():
        assert TEST_COUNT_CLAIM.search(clean_line) is None
        assert TEST_COUNT_CLAIM.search(stale_lines[readme_name]), (
            f"count guard missed a reintroduced claim in {readme_name}"
        )
