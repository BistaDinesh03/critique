from fastapi import FastAPI
from app.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="Ask one question. Get real answers.",
    version="0.1.0",
)


@app.get("/")
def root():
    """Root endpoint - basic welcome message."""
    return {
        "message": "Welcome to Critique",
        "tagline": "Ask one question. Get real answers.",
        "status": "running",
    }


@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "ok"}
