"""Unknown routes serve a branded HTML 404 to browsers while JSON clients --
and every /api/* route -- keep the default {"detail": ...} shape."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_unknown_browser_route_returns_html_404():
    """A browser navigating to an unknown path gets the styled HTML page."""
    response = client.get("/nonexistent", headers={"Accept": "text/html"})
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert "Page not found" in response.text
    # The page offers a way onward: home and Discover.
    assert 'href="/"' in response.text
    assert 'href="/discover"' in response.text


def test_unknown_route_json_client_keeps_json_shape():
    """An explicit JSON client still gets the default detail body."""
    response = client.get("/nonexistent", headers={"Accept": "application/json"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_unknown_route_default_accept_keeps_json_shape():
    """The default Accept (*/*) is treated as a non-HTML client."""
    response = client.get("/nonexistent")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_unknown_api_route_stays_json_even_for_browser():
    """Anything under /api/ keeps JSON regardless of the Accept header."""
    response = client.get("/api/does-not-exist", headers={"Accept": "text/html"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_api_resource_404_stays_json_even_for_browser():
    """A real API 404 (missing resource) is untouched by the HTML handler."""
    response = client.get("/api/projects/999999", headers={"Accept": "text/html"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}
