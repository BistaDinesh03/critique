from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="Ask one question. Get real answers.",
    version="0.1.0",
)

# Serve static files (CSS, JS, images)
static_dir = Path(__file__).resolve().parent.parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
def homepage():
    """Serve the minimal homepage."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Critique</title>
    </head>
    <body>
        <main>
            <h1>Critique</h1>
            <p>Ask one question. Get real answers.</p>
        </main>
    </body>
    </html>
    """


@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "ok"}
