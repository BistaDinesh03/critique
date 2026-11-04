import html
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import Project

router = APIRouter(tags=["seo"])

# Used when APP_URL is unset or blank. An absolute origin is not optional
# here: a root-relative <loc> cannot be resolved by a crawler, and the
# robots.txt "Sitemap:" line is specified as an absolute URL.
DEFAULT_APP_URL = "http://127.0.0.1:8000"


def site_url() -> str:
    """Return the configured public origin, without a trailing slash.

    These two endpoints are the only place the app emits absolute URLs to
    third parties (crawlers), so they take the origin from configuration the
    same way app/email.py builds magic links -- a self-hosted or staging
    deployment then advertises itself instead of the production domain.

    The value is read per request rather than at import time so it tracks
    configuration (and test overrides) instead of being frozen on first
    import.
    """
    return (settings.APP_URL or "").strip().rstrip("/") or DEFAULT_APP_URL


@router.get("/robots.txt", response_class=Response)
def robots_txt():
    content = "User-agent: *\n"
    content += "Allow: /\n"
    content += "Disallow: /my-projects\n"
    content += "Disallow: /api/\n"
    content += "Disallow: /auth/\n"
    content += "Disallow: /health\n"
    content += "Disallow: /google8ffd0ae5f931d1e6.html\n"
    content += "\n"
    content += "Sitemap: " + site_url() + "/sitemap.xml\n"
    return Response(content=content, media_type="text/plain")


@router.get("/sitemap.xml", response_class=Response)
def sitemap_xml(db: Session = Depends(get_db)):
    projects = db.query(Project.id).order_by(Project.created_at.desc()).all()

    urls = []
    urls.append("  <url>\n    <loc>" + site_url() + "/</loc>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>")
    urls.append("  <url>\n    <loc>" + site_url() + "/discover</loc>\n    <changefreq>daily</changefreq>\n    <priority>0.9</priority>\n  </url>")

    for (project_id,) in projects:
        urls.append("  <url>\n    <loc>" + site_url() + "/project/" + str(project_id) + "</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.7</priority>\n  </url>")

    body = "\n".join(urls)
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += body + "\n"
    xml += "</urlset>\n"
    return Response(content=xml, media_type="application/xml")


@router.get("/feed.xml", response_class=Response)
def rss_feed(db: Session = Depends(get_db)):
    projects = (
        db.query(Project)
        .order_by(Project.created_at.desc())
        .limit(50)
        .all()
    )

    origin = site_url()
    items = []
    for p in projects:
        title = html.escape(p.title)
        link = f"{origin}/project/{p.id}"
        desc = html.escape(p.description or "")
        pub_date = p.created_at.strftime("%a, %d %b %Y %H:%M:%S GMT") if p.created_at else ""
        items.append(
            f"    <item>\n"
            f"      <title>{title}</title>\n"
            f"      <link>{link}</link>\n"
            f"      <guid isPermaLink=\"true\">{link}</guid>\n"
            f"      <description>{desc}</description>\n"
            f"      <pubDate>{pub_date}</pubDate>\n"
            f"    </item>"
        )

    items_xml = "\n".join(items)
    if items_xml:
        items_xml = "\n" + items_xml

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        '  <channel>\n'
        f'    <title>{html.escape(settings.APP_NAME)}</title>\n'
        f'    <link>{origin}/discover</link>\n'
        f'    <description>New projects waiting for feedback on {html.escape(settings.APP_NAME)}</description>\n'
        f'    <language>en</language>{items_xml}\n'
        '  </channel>\n'
        '</rss>\n'
    )
    return Response(content=xml, media_type="application/rss+xml")
