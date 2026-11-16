"""Tests for discover feed scroll preservation on navigation."""
from pathlib import Path


def test_discover_html_includes_scroll_preservation_logic():
    html_path = Path(__file__).resolve().parents[2] / 'frontend' / 'discover.html'
    html = html_path.read_text(encoding='utf-8')

    assert 'critique_discover_scroll' in html
    assert 'critique_discover_page' in html
    assert 'sessionStorage.getItem' in html
    assert 'sessionStorage.setItem' in html
    assert 'sessionStorage.removeItem' in html
    assert 'window.scrollTo' in html
