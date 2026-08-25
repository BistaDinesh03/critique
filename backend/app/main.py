from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.config import settings
from app.database import init_db
from app.auth import router as auth_router
from app.routes_projects import router as projects_router
from app.routes_responses import router as responses_router
from app.routes_results import router as results_router
from app.csrf import generate_csrf_token


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

# Include routers
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(responses_router)
app.include_router(results_router)

# Serve static files
static_dir = Path(__file__).resolve().parent.parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


def _read_frontend_file(filename: str) -> str:
    """Read a file from the frontend directory."""
    frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
    file_path = frontend_dir / filename
    return file_path.read_text(encoding="utf-8")




@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    """Generic error handler that doesn't leak stack traces."""
    return {"detail": "Internal server error"}

@app.get("/", response_class=HTMLResponse)
def homepage():
    """Serve the submission form."""
    return HTMLResponse(content=_read_frontend_file("index.html"))


@app.get("/discover", response_class=HTMLResponse)
def discover_page():
    """Serve the discovery page."""
    return HTMLResponse(content=_read_frontend_file("discover.html"))


@app.get("/project/{project_id}", response_class=HTMLResponse)
def project_detail_page(project_id: int):
    """Serve the project detail page."""
    return HTMLResponse(content=_read_frontend_file("project_detail.html"))


@app.get("/project/{project_id}/results", response_class=HTMLResponse)
def project_results_page(project_id: int):
    """Serve the project results page."""
    return HTMLResponse(content=_read_frontend_file("project_results.html"))


@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "ok"}

