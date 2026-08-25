from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.config import settings
from app.database import init_db
from app.routes_projects import router as projects_router

app = FastAPI(
    title=settings.APP_NAME,
    description="Ask one question. Get real answers.",
    version="0.1.0",
)


@app.on_event("startup")
def startup_event():
    """Initialize database on application startup."""
    init_db()


# Include routers
app.include_router(projects_router)


# Serve static files (CSS, JS, images)
static_dir = Path(__file__).resolve().parent.parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
def homepage():
    """Serve the frontend HTML."""
    frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
    html_file = frontend_dir / "index.html"
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "ok"}
