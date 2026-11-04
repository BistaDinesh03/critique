"""Pin the contract of the two machine-facing SEO endpoints.

``GET /robots.txt`` and ``GET /sitemap.xml`` are the only places Critique
hands absolute URLs to a third party (a crawler). Both the shape of the
responses and the origin they are built from are pinned here: a refactor that
silently dropped a ``Disallow`` line would be a privacy regression, and one
that reintroduced a hardcoded origin would misdirect every self-hosted
instance's crawlers to the production site.

Fixtures and style follow ``test_badge.py``: rows are seeded through
``SessionLocal`` and deleted again when the test ends.
"""
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import settings
from app.database import SessionLocal
from app.main import app
from app.models import Project, User
from app.routes_seo import DEFAULT_APP_URL, site_url

# The origin production is configured with (see render.yaml).
PRODUCTION_ORIGIN = "https://critique.page"

# Exactly what robots.txt served before the origin became configurable.
EXPECTED_ROBOTS_BODY = (
    "User-agent: *\n"
    "Allow: /\n"
    "Disallow: /my-projects\n"
    "Disallow: /api/\n"
    "Disallow: /auth/\n"
    "Disallow: /health\n"
    "Disallow: /google8ffd0ae5f931d1e6.html\n"
    "\n"
)

PRIVATE_PATHS = ("/my-projects", "/api/", "/auth/", "/health")


def _build_project():
    """Insert a project (and its owner) so it shows up in the sitemap."""
    unique = uuid.uuid4().hex[:12]
    with SessionLocal() as db:
        owner = User(github_id=int(uuid.uuid4().int % 100000000),
                     username=f"seo-owner-{unique}")
        db.add(owner)
        db.flush()

        project = Project(title=f"SEO project {unique}", owner_id=owner.id)
        db.add(project)
        db.commit()
        return project.id, owner.id


def _delete_project(project_id, owner_id):
    with SessionLocal() as db:
        db.query(Project).filter(Project.id == project_id).delete()
        db.query(User).filter(User.id == owner_id).delete()
        db.commit()


class _ProjectFixture:
    """Context manager so every seeded project is cleaned up afterwards."""

    def __enter__(self):
        self.project_id, self.owner_id = _build_project()
        return self.project_id

    def __exit__(self, *exc_info):
        _delete_project(self.project_id, self.owner_id)
        return False


def project_in_sitemap():
    return _ProjectFixture()


def get_robots():
    return TestClient(app).get("/robots.txt")


def get_sitemap():
    return TestClient(app).get("/sitemap.xml")


class TestRobotsTxt:
    """GET /robots.txt"""

    def test_returns_plain_text(self):
        response = get_robots()

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")

    def test_allows_root_and_disallows_private_paths(self):
        """Owner pages, the API, auth and /health must stay out of crawlers."""
        body = get_robots().text

        assert "Allow: /" in body
        for path in PRIVATE_PATHS:
            assert f"Disallow: {path}" in body

    def test_advertises_the_configured_sitemap(self, monkeypatch):
        monkeypatch.setattr(settings, "APP_URL", PRODUCTION_ORIGIN)

        assert f"Sitemap: {PRODUCTION_ORIGIN}/sitemap.xml" in get_robots().text

    def test_trailing_slash_does_not_produce_a_double_slash(self, monkeypatch):
        monkeypatch.setattr(settings, "APP_URL", PRODUCTION_ORIGIN + "/")

        body = get_robots().text

        assert f"Sitemap: {PRODUCTION_ORIGIN}/sitemap.xml" in body
        assert f"{PRODUCTION_ORIGIN}//" not in body

    def test_a_self_hosted_origin_is_advertised(self, monkeypatch):
        """The whole point of #138: the origin follows configuration, not a constant."""
        monkeypatch.setattr(settings, "APP_URL", "https://staging.example.com")

        body = get_robots().text

        assert "Sitemap: https://staging.example.com/sitemap.xml" in body
        assert "critique.page" not in body


class TestSitemapXml:
    """GET /sitemap.xml"""

    def test_returns_urlset_xml(self):
        response = get_sitemap()

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/xml")
        assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in response.text
        assert response.text.rstrip().endswith("</urlset>")

    def test_includes_root_and_discover(self, monkeypatch):
        monkeypatch.setattr(settings, "APP_URL", PRODUCTION_ORIGIN)

        body = get_sitemap().text

        assert f"<loc>{PRODUCTION_ORIGIN}/</loc>" in body
        assert f"<loc>{PRODUCTION_ORIGIN}/discover</loc>" in body

    def test_newly_created_projects_appear(self, monkeypatch):
        monkeypatch.setattr(settings, "APP_URL", PRODUCTION_ORIGIN)

        with project_in_sitemap() as project_id:
            body = get_sitemap().text

        assert f"<loc>{PRODUCTION_ORIGIN}/project/{project_id}</loc>" in body

    def test_trailing_slash_does_not_produce_a_double_slash(self, monkeypatch):
        monkeypatch.setattr(settings, "APP_URL", PRODUCTION_ORIGIN + "/")

        body = get_sitemap().text

        assert f"<loc>{PRODUCTION_ORIGIN}/discover</loc>" in body
        assert f"{PRODUCTION_ORIGIN}//" not in body

    def test_a_self_hosted_origin_is_used_for_every_loc(self, monkeypatch):
        """Every <loc> must point at the configured deployment, never production."""
        monkeypatch.setattr(settings, "APP_URL", "https://staging.example.com")

        body = get_sitemap().text

        assert f"<loc>https://staging.example.com/</loc>" in body
        assert "critique.page" not in body


class TestOriginComesFromConfiguration:
    """site_url() and the fallback behaviour documented in issue #138"""

    def test_uses_the_configured_origin(self, monkeypatch):
        monkeypatch.setattr(settings, "APP_URL", "https://staging.example.com")

        assert site_url() == "https://staging.example.com"

    def test_strips_a_trailing_slash(self, monkeypatch):
        monkeypatch.setattr(settings, "APP_URL", "https://staging.example.com///")

        assert site_url() == "https://staging.example.com"

    def test_falls_back_to_the_local_default_when_blank(self, monkeypatch):
        """A blank APP_URL must not emit root-relative URLs no crawler can resolve."""
        monkeypatch.setattr(settings, "APP_URL", "   ")

        assert site_url() == DEFAULT_APP_URL
        assert get_sitemap().text.count("<loc>/") == 0

    def test_production_robots_output_is_unchanged(self, monkeypatch):
        """Byte-identical to the hardcoded-origin version when APP_URL is set."""
        monkeypatch.setattr(settings, "APP_URL", PRODUCTION_ORIGIN)

        assert get_robots().text.startswith(EXPECTED_ROBOTS_BODY)
        assert get_robots().text == EXPECTED_ROBOTS_BODY + (
            f"Sitemap: {PRODUCTION_ORIGIN}/sitemap.xml\n"
        )


class TestGoogleVerificationRoute:
    def test_serves_committed_verification_file(self):
        client = TestClient(app)
        res = client.get("/google8ffd0ae5f931d1e6.html")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]
        assert res.text == "google-site-verification: google8ffd0ae5f931d1e6.html"

    def test_returns_404_when_file_is_absent(self, monkeypatch):
        monkeypatch.setattr(Path, "is_file", lambda self: False)
        client = TestClient(app)
        res = client.get("/google8ffd0ae5f931d1e6.html")
        assert res.status_code == 404
        assert res.json() == {"detail": "Verification file not found"}

