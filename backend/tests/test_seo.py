from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


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
