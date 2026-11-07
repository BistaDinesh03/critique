"""Canonical link tag tests for SEO."""
from pathlib import Path


def test_index_html_has_canonical_tag():
    html_path = Path(__file__).resolve().parents[2] / 'frontend' / 'index.html'
    html = html_path.read_text(encoding='utf-8')
    assert '<link rel="canonical" href="https://critique.page/">' in html
