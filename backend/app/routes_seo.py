from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Project

router = APIRouter(tags=["seo"])

SITE_URL = "https://critique.page"


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
    content += "Sitemap: " + SITE_URL + "/sitemap.xml\n"
    return Response(content=content, media_type="text/plain")


@router.get("/sitemap.xml", response_class=Response)
def sitemap_xml(db: Session = Depends(get_db)):
    projects = db.query(Project.id).order_by(Project.created_at.desc()).all()

    urls = []
    urls.append("  <url>\n    <loc>" + SITE_URL + "/</loc>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>")
    urls.append("  <url>\n    <loc>" + SITE_URL + "/discover</loc>\n    <changefreq>daily</changefreq>\n    <priority>0.9</priority>\n  </url>")

    for (project_id,) in projects:
        urls.append("  <url>\n    <loc>" + SITE_URL + "/project/" + str(project_id) + "</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.7</priority>\n  </url>")

    body = "\n".join(urls)
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += body + "\n"
    xml += "</urlset>\n"
    return Response(content=xml, media_type="application/xml")
