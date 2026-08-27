from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Project, Question, Response

router = APIRouter(prefix="/badge", tags=["badge"])


def format_count(count: int) -> str:
    """Format response count for badge display."""
    if count >= 1000:
        return "1k+"
    return str(count)


@router.get("/{project_id}.svg")
def get_badge(project_id: int, db: Session = Depends(get_db)):
    """Return a dynamic SVG badge showing feedback count for a project."""
    # Get project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Count responses for active question
    question = (
        db.query(Question)
        .filter(Question.project_id == project_id, Question.is_active == True)
        .order_by(Question.created_at.desc())
        .first()
    )

    count = 0
    if question:
        count = (
            db.query(func.count(Response.id))
            .filter(Response.question_id == question.id)
            .scalar()
        )

    count_text = format_count(count)
    label = "feedback" if count != 1 else "feedback"

    # Build SVG badge
    # Use original Critique colors: #16181A background, #56E83F green accent
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="180" height="32" viewBox="0 0 180 32">
  <rect width="180" height="32" rx="6" fill="#16181A"/>
  <path d="M16 21h11" fill="none" stroke="#56E83F" stroke-width="3" stroke-linecap="round"/>
  <path d="M27 21h2" fill="none" stroke="#56E83F" stroke-width="3" stroke-linecap="round"/>
  <path d="M29 21c3.5 0 6.5-2 7-5.5.5-3.5-1.5-6-4.5-6-2.5 0-4 1.5-4 3.5" fill="none" stroke="#56E83F" stroke-width="2" stroke-linecap="round"/>
  <path d="M27.5 17.5l.5 3 3-1" fill="none" stroke="#56E83F" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  <text x="44" y="21" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="13" font-weight="600" fill="#ffffff">{count_text} {label}</text>
</svg>'''

    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-cache"},
    )
