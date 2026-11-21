"""Tests for SVG and PNG favicon assets and index.html link tags."""

from html.parser import HTMLParser
from pathlib import Path
import re
import struct

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from app.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = REPO_ROOT / "static"
FRONTEND_DIR = REPO_ROOT / "frontend"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

client = TestClient(app)


class _LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "link":
            self.links.append(dict(attrs))


def test_svg_favicon_present_with_brand_colors():
    svg_path = STATIC_DIR / "favicon.svg"
    assert svg_path.is_file()
    content = svg_path.read_text(encoding="utf-8")
    assert 'viewBox="0 0 64 64"' in content
    assert 'stroke="#16181A"' in content
    assert 'stroke="#56E83F"' in content


@pytest.mark.parametrize(
    ("filename", "expected_size"),
    [
        ("favicon-16.png", 16),
        ("favicon-32.png", 32),
    ],
)
def test_png_favicon_files_valid_and_match_brand(filename: str, expected_size: int):
    png_path = STATIC_DIR / filename
    assert png_path.is_file()

    raw = png_path.read_bytes()
    assert raw[:8] == PNG_MAGIC
    assert raw[12:16] == b"IHDR"
    width, height = struct.unpack(">II", raw[16:24])
    assert (width, height) == (expected_size, expected_size)

    with Image.open(png_path) as img:
        assert img.size == (expected_size, expected_size)
        rgba = img.convert("RGBA").tobytes()

    pixels = [
        (rgba[i], rgba[i + 1], rgba[i + 2], rgba[i + 3])
        for i in range(0, len(rgba), 4)
    ]
    transparent = [p for p in pixels if p[3] == 0]
    dark_brand = [
        p for p in pixels if p[3] > 100 and p[0] < 50 and p[1] < 50 and p[2] < 50
    ]
    green_brand = [
        p for p in pixels if p[3] > 100 and p[1] > 180 and p[0] < 130 and p[2] < 130
    ]
    assert transparent, f"{filename} should have a transparent background"
    assert dark_brand, f"{filename} should include #16181A brand stroke pixels"
    assert green_brand, f"{filename} should include #56E83F brand accent pixels"


@pytest.mark.parametrize("filename", ["favicon-16.png", "favicon-32.png"])
def test_png_favicons_served_via_static(filename: str):
    response = client.get(f"/static/{filename}")
    assert response.status_code == 200
    assert response.headers.get("content-type") == "image/png"
    assert response.content == (STATIC_DIR / filename).read_bytes()


def test_index_html_head_declares_svg_and_png_favicons():
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    head_match = re.search(r"<head>(.*?)</head>", html, re.DOTALL | re.IGNORECASE)
    assert head_match is not None

    parser = _LinkCollector()
    parser.feed(head_match.group(1))
    icon_links = [link for link in parser.links if link.get("rel") == "icon"]

    assert {
        "rel": "icon",
        "type": "image/svg+xml",
        "href": "/static/favicon.svg",
    } in icon_links
    assert {
        "rel": "icon",
        "type": "image/png",
        "sizes": "16x16",
        "href": "/static/favicon-16.png",
    } in icon_links
    assert {
        "rel": "icon",
        "type": "image/png",
        "sizes": "32x32",
        "href": "/static/favicon-32.png",
    } in icon_links
