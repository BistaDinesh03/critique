"""Test that all relative Markdown links in the repository resolve to real files."""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Matches Markdown links and images: [text](target) or ![alt](target)
# Supports:
# - angle brackets: [text](<path/with parens>)
# - single-level balanced parentheses: [text](path(1)/file.md)
# - optional title suffix: [text](path/to/file.md "Title")
MARKDOWN_LINK_PATTERN = re.compile(
    r"!?\[([^\]]*)\]\((<[^>]+>|(?:[^()\s]|\([^()\s]*\))+)(?:\s+[\"'][^\"']*[\"'])?\)"
)


@dataclass
class MarkdownLink:
    source_file: Path
    line_number: int
    text: str
    raw_target: str
    target_path: Path


def normalize_target(raw_target: str) -> str | None:
    """Extract and normalize the file path component of a link target.

    Returns None for external URLs, mailto links, or pure in-page anchors.
    Strips fragment identifiers, title attributes, and enclosing angle brackets.
    """
    target = raw_target.strip()
    if not target:
        return None

    # Strip enclosing angle brackets, e.g. [text](<path>)
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()

    # Drop optional title suffix, e.g. [text](path/to/file "title")
    target = target.split()[0] if target else ""
    if not target or target.startswith("#"):
        return None

    parsed = urllib.parse.urlparse(target)
    if parsed.scheme:
        # External URLs (http, https, mailto, etc.)
        return None

    # Strip fragment and query parameters
    path_part = parsed.path
    if not path_part:
        return None

    return urllib.parse.unquote(path_part)


def find_markdown_files(root: Path = ROOT) -> list[Path]:
    """Collect Markdown files from the repository root and docs directory."""
    root_files = [f for f in root.glob("*.md") if f.is_file()]
    docs_dir = root / "docs"
    docs_files = [f for f in docs_dir.rglob("*.md") if f.is_file()] if docs_dir.is_dir() else []
    return sorted(root_files + docs_files)


def extract_relative_links(file_path: Path, root: Path = ROOT) -> list[MarkdownLink]:
    """Extract relative Markdown links from a file, skipping fenced code blocks."""
    content = file_path.read_text(encoding="utf-8")
    links: list[MarkdownLink] = []
    fence: str | None = None

    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()

        # Handle fenced code blocks with backticks (```) or tildes (~~~)
        if fence is not None:
            if stripped.startswith(fence):
                fence = None
            continue
        if stripped.startswith("```"):
            fence = "```"
            continue
        if stripped.startswith("~~~"):
            fence = "~~~"
            continue

        for match in MARKDOWN_LINK_PATTERN.finditer(line):
            text = match.group(1)
            raw_target = match.group(2)
            normalized_path = normalize_target(raw_target)
            if normalized_path is None:
                continue

            if normalized_path.startswith("/"):
                target_path = (root / normalized_path.lstrip("/")).resolve()
            else:
                target_path = (file_path.parent / normalized_path).resolve()

            links.append(
                MarkdownLink(
                    source_file=file_path,
                    line_number=line_number,
                    text=text,
                    raw_target=raw_target,
                    target_path=target_path,
                )
            )

    return links


def test_markdown_files_discovered():
    """Verify markdown file discovery finds root and docs files."""
    files = find_markdown_files(ROOT)
    filenames = {f.name for f in files}
    assert "README.md" in filenames
    assert "CONTRIBUTING.md" in filenames
    assert "SECURITY.md" in filenames
    assert "issue-roadmap.md" in filenames


def test_all_relative_markdown_links_exist():
    """All relative Markdown links in repo root and docs/ must exist on disk."""
    md_files = find_markdown_files(ROOT)
    assert md_files, "No Markdown files found to check"

    broken_links: list[str] = []
    total_checked = 0

    for md_file in md_files:
        links = extract_relative_links(md_file, ROOT)
        for link in links:
            total_checked += 1
            if not link.target_path.exists():
                rel_source = link.source_file.relative_to(ROOT)
                broken_links.append(
                    f"{rel_source}:{link.line_number} -> '{link.raw_target}' "
                    f"(target does not exist: {link.target_path})"
                )

    assert total_checked > 0, "No relative links found across Markdown files"
    assert not broken_links, (
        f"Found {len(broken_links)} broken relative link(s):\n"
        + "\n".join(f"  - {entry}" for entry in broken_links)
    )


def test_external_links_and_anchors_are_skipped():
    """External URLs and pure in-page anchors should be ignored; fragments stripped."""
    assert normalize_target("https://critique.page/discover") is None
    assert normalize_target("http://127.0.0.1:8000") is None
    assert normalize_target("mailto:maintainer@example.com") is None
    assert normalize_target("#section-header") is None
    assert normalize_target("docs/api.md#endpoints") == "docs/api.md"
    assert normalize_target("<docs/api.md>") == "docs/api.md"
    assert normalize_target('docs/api.md "API Documentation"') == "docs/api.md"


def test_broken_link_detection(tmp_path):
    """The link extractor correctly detects when a target file does not exist."""
    fake_doc = tmp_path / "index.md"
    fake_doc.write_text(
        "Here is a [good link](existing.txt) and a [broken link](missing.txt).\n"
        "And an external link [critique](https://example.com).\n",
        encoding="utf-8",
    )
    (tmp_path / "existing.txt").write_text("hello", encoding="utf-8")

    links = extract_relative_links(fake_doc, root=tmp_path)
    assert len(links) == 2

    existing_link = next(l for l in links if l.raw_target == "existing.txt")
    missing_link = next(l for l in links if l.raw_target == "missing.txt")

    assert existing_link.target_path.exists()
    assert not missing_link.target_path.exists()


def test_fenced_code_blocks_and_edge_cases(tmp_path):
    """Fenced code blocks (``` and ~~~), nested parens, and angle brackets are supported."""
    (tmp_path / "valid(1).txt").write_text("ok", encoding="utf-8")
    (tmp_path / "angle.txt").write_text("ok", encoding="utf-8")

    doc = tmp_path / "edge_cases.md"
    doc.write_text(
        "```markdown\n"
        "[ignored in backtick fence](broken1.txt)\n"
        "```\n"
        "~~~\n"
        "[ignored in tilde fence](broken2.txt)\n"
        "~~~\n"
        "[nested paren](valid(1).txt)\n"
        "[angle brackets](<angle.txt>)\n",
        encoding="utf-8",
    )

    links = extract_relative_links(doc, root=tmp_path)
    assert len(links) == 2
    assert all(link.target_path.exists() for link in links)
    raw_targets = {link.raw_target for link in links}
    assert raw_targets == {"valid(1).txt", "<angle.txt>"}
