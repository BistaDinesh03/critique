"""Tests asserting presence and wiring of Open Graph and Twitter Card metadata."""

from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


def test_index_html_has_social_meta_tags():
    index_html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    assert '<meta property="og:title"' in index_html
    assert '<meta property="og:description"' in index_html
    assert '<meta property="og:image"' in index_html
    assert '<meta property="og:type"' in index_html
    assert '<meta name="twitter:card"' in index_html
    assert '<meta name="twitter:title"' in index_html
    assert '<meta name="twitter:description"' in index_html
    assert '<meta name="twitter:image"' in index_html


def test_discover_html_has_social_meta_tags():
    discover_html = (FRONTEND_DIR / "discover.html").read_text(encoding="utf-8")
    assert '<meta property="og:title"' in discover_html
    assert '<meta property="og:description"' in discover_html
    assert '<meta property="og:image"' in discover_html
    assert '<meta property="og:type"' in discover_html
    assert '<meta name="twitter:card"' in discover_html
    assert '<meta name="twitter:title"' in discover_html
    assert '<meta name="twitter:description"' in discover_html
    assert '<meta name="twitter:image"' in discover_html


def test_project_detail_html_has_social_meta_tags_and_dynamic_hooks():
    detail_html = (FRONTEND_DIR / "project_detail.html").read_text(encoding="utf-8")
    assert 'id="og-title"' in detail_html
    assert 'id="og-description"' in detail_html
    assert 'id="og-image"' in detail_html
    assert 'id="tw-title"' in detail_html
    assert 'id="tw-description"' in detail_html
    assert 'id="tw-image"' in detail_html
    assert '<meta name="twitter:card"' in detail_html

    # Dynamic DOM update logic in renderProject
    assert "ogTitle.setAttribute('content'" in detail_html
    assert "twTitle.setAttribute('content'" in detail_html
    assert "ogDesc.setAttribute('content'" in detail_html
    assert "twDesc.setAttribute('content'" in detail_html
    assert "ogImg.setAttribute('content'" in detail_html
    assert "twImg.setAttribute('content'" in detail_html
