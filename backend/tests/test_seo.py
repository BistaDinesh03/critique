import json
from pathlib import Path
import re

from fastapi.testclient import TestClient
import pytest

from app.config import settings
from app.main import app

client = TestClient(app)

# These assertions are written against the production origin. The SEO routes
# now build their absolute URLs from settings.APP_URL, so pin it here rather
# than depending on whatever the test environment happens to be configured
# with (the sitemap rows below would otherwise assert against the wrong host).
PRODUCTION_ORIGIN = "https://critique.page"


@pytest.fixture(autouse=True)
def configured_origin(monkeypatch):
    monkeypatch.setattr(settings, "APP_URL", PRODUCTION_ORIGIN)


def test_robots_txt_returns_200():
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]


def test_robots_txt_references_sitemap():
    response = client.get("/robots.txt")
    assert "Sitemap: https://critique.page/sitemap.xml" in response.text


def test_robots_txt_disallows_private_areas():
    response = client.get("/robots.txt")
    text = response.text
    assert "Disallow: /my-projects" in text
    assert "Disallow: /api/" in text
    assert "Disallow: /auth/" in text


def test_sitemap_returns_200():
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert "xml" in response.headers["content-type"]


def test_sitemap_contains_homepage():
    response = client.get("/sitemap.xml")
    assert "https://critique.page/" in response.text


def test_sitemap_contains_discover():
    response = client.get("/sitemap.xml")
    assert "https://critique.page/discover" in response.text


def test_sitemap_is_valid_xml():
    import xml.etree.ElementTree as ET
    response = client.get("/sitemap.xml")
    root = ET.fromstring(response.text)
    assert root.tag.endswith("urlset")


def test_sitemap_does_not_include_private_pages():
    response = client.get("/sitemap.xml")
    text = response.text
    assert "/my-projects" not in text
    assert "/api/" not in text
    assert "/auth/" not in text


def test_og_image_webp_and_png_assets_served():
    """Ensure both optimized og-image.webp and fallback og-image.png are served."""
    res_webp = client.get("/static/og-image.webp")
    assert res_webp.status_code == 200
    assert "webp" in res_webp.headers.get("content-type", "")

    res_png = client.get("/static/og-image.png")
    assert res_png.status_code == 200
    assert "png" in res_png.headers.get("content-type", "")


def test_homepage_declares_webp_og_and_twitter_image():
    """Ensure index.html includes WebP for modern social crawlers."""
    res = client.get("/")
    assert res.status_code == 200
    assert '<meta property="og:image" content="https://critique.page/static/og-image.webp">' in res.text
    assert '<meta property="og:image:type" content="image/webp">' in res.text
    assert '<meta name="twitter:image" content="https://critique.page/static/og-image.webp">' in res.text


def test_social_image_dimensions_and_alt_attributes():
    """Ensure og:image dimensions, og:image:alt, and twitter:image:alt are present on pages."""
    res = client.get("/")
    assert res.status_code == 200
    assert '<meta property="og:image:width" content="1200">' in res.text
    assert '<meta property="og:image:height" content="630">' in res.text
    assert '<meta property="og:image:alt" content="Critique — Ask one question. Get real answers.">' in res.text
    assert '<meta name="twitter:image:alt" content="Critique — Ask one question. Get real answers.">' in res.text

    # Also verify project detail template has the tags
    frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
    html = (frontend_dir / "project_detail.html").read_text(encoding="utf-8")
    assert '<meta property="og:image:width" content="1200">' in html
    assert '<meta property="og:image:height" content="630">' in html
    assert '<meta property="og:image:alt" content="Critique — Ask one question. Get real answers.">' in html
    assert '<meta name="twitter:image:alt" content="Critique — Ask one question. Get real answers.">' in html


def test_homepage_has_application_and_organization_structured_data():
    response = client.get("/")
    assert response.status_code == 200
    head = re.search(r"<head>(.*?)</head>", response.text, re.DOTALL).group(1)
    blocks = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', head, re.DOTALL
    )
    assert len(blocks) == 1
    data = json.loads(blocks[0])
    assert data["@context"] == "https://schema.org"
    entities = {entity["@type"]: entity for entity in data["@graph"]}
    assert set(entities) == {"SoftwareApplication", "Organization"}
    application = entities["SoftwareApplication"]
    organization = entities["Organization"]
    assert application["name"] == organization["name"] == "Critique"
    assert application["url"] == organization["url"] == f"{PRODUCTION_ORIGIN}/"
    assert application["@id"] != organization["@id"]
    assert application["publisher"] == {"@id": organization["@id"]}
    assert application["description"]
