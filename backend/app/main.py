from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import settings
from app.database import init_db
from app.auth import router as auth_router
from app.auth import session_cookie_is_valid
from app.csrf import generate_csrf_token, set_csrf_cookie
from app.routes_projects import router as projects_router
from app.routes_responses import router as responses_router
from app.routes_results import router as results_router
from app.routes_badge import router as badge_router
from app.routes_stats import router as stats_router
from app.routes_analytics import router as analytics_router
from app.routes_analytics_dashboard import router as analytics_dashboard_router
from app.routes_seo import router as seo_router


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Add cache headers to static files."""
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=86400"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Ask one question. Get real answers.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(CacheControlMiddleware)

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(responses_router)
app.include_router(results_router)
app.include_router(badge_router)
app.include_router(stats_router)
app.include_router(analytics_router)
app.include_router(analytics_dashboard_router)
app.include_router(seo_router)

static_dir = Path(__file__).resolve().parent.parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


def _read_frontend_file(filename: str) -> str:
    frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
    file_path = frontend_dir / filename
    return file_path.read_text(encoding="utf-8")


# Early auth state for the navbar. Stamped into <head> before the header is
# parsed, so a returning authenticated visitor's first paint already shows the
# logged-in header instead of flashing Login while /auth/check is in flight.
# The client-side check remains authoritative: its inline styles override
# these rules, so a failed or 401 check always lands on the logged-out UI.
_EARLY_AUTH_SCRIPT = (
    '<script>document.documentElement.setAttribute("data-auth","in");</script>'
)
_EARLY_AUTH_STYLE = (
    "<style>"
    'html[data-auth="in"] #login-btn{display:none}'
    'html[data-auth="in"] #logout-btn{display:inline-flex}'
    "</style>"
)


def _page_response(request: Request, filename: str) -> HTMLResponse:
    """Serve a frontend page, stamping early auth state when a valid session
    cookie accompanies the request (signature + age only, no DB lookup)."""
    html = _read_frontend_file(filename)
    if session_cookie_is_valid(request):
        html = html.replace(
            "</head>", _EARLY_AUTH_SCRIPT + _EARLY_AUTH_STYLE + "</head>", 1
        )
    response = HTMLResponse(content=html)
    # The body varies with the session cookie (the early-auth stamp), so no
    # cache -- shared or browser -- may replay one visitor's page to another.
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Cookie"
    set_csrf_cookie(response, generate_csrf_token())
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    """Generic error handler that doesn't leak stack traces."""
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/", response_class=HTMLResponse)
def homepage(request: Request):
    return _page_response(request, "index.html")


@app.get("/my-projects", response_class=HTMLResponse)
def my_projects_page(request: Request):
    return _page_response(request, "my_projects.html")


@app.get("/discover", response_class=HTMLResponse)
def discover_page(request: Request):
    return _page_response(request, "discover.html")


@app.get("/project/{project_id}", response_class=HTMLResponse)
def project_detail_page(request: Request, project_id: int):
    return _page_response(request, "project_detail.html")


@app.get("/project/{project_id}/results", response_class=HTMLResponse)
def project_results_page(request: Request, project_id: int):
    return _page_response(request, "project_results.html")




@app.get("/google8ffd0ae5f931d1e6.html", response_class=HTMLResponse)
def google_verification():
    """Serve Google Search Console verification file."""
    static_dir = Path(__file__).resolve().parent.parent.parent / "static"
    file_path = static_dir / "google8ffd0ae5f931d1e6.html"
    return HTMLResponse(content=file_path.read_text(encoding="utf-8"))


@app.get("/health")
def health_check():
    return {"status": "ok"}




