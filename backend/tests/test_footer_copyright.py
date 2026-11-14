"""Test that the footer copyright year is updated dynamically from Date."""

from pathlib import Path

import pytest

REPO_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = REPO_DIR / "frontend"
UI_JS = REPO_DIR / "static" / "ui.js"

PAGES = [
    "index.html",
    "discover.html",
    "my_projects.html",
    "project_detail.html",
    "project_results.html",
    "404.html",
]


def test_ui_js_updates_copyright_from_date():
    """ui.js must derive the footer year from Date.getFullYear()."""
    source = UI_JS.read_text(encoding="utf-8")
    assert "footer-copyright" in source
    assert "new Date().getFullYear()" in source
    assert "© " in source  # the template string


@pytest.mark.parametrize("page", PAGES)
def test_pages_have_footer_copyright_id_and_no_bare_hardcoded_year(page):
    """Every public page marks the footer for dynamic update and keeps a fallback year."""
    path = FRONTEND_DIR / page
    html = path.read_text(encoding="utf-8")
    assert 'id="footer-copyright"' in html, f"{page} missing footer-copyright id"
    # The fallback year is allowed, but the element must be marked so JS can replace it.
    assert "© 2026 Critique · Open source · Free to use" in html
    # Ensure we did not leave a bare hard-coded span without the id.
    bare = "<span>© 2026 Critique · Open source · Free to use</span>"
    assert bare not in html, f"{page} still contains an unmarked hard-coded copyright span"
