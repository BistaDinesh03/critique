from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Project, Question, Response as ResponseModel

router = APIRouter(prefix="/badge", tags=["badge"])


def format_count(count: int) -> str:
    """Format count with thousand separator for 1000+."""
    if count >= 1000:
        return f"{count:,}"
    return str(count)


@router.get("/{project_id}.svg")
def get_badge(project_id: int, db: Session = Depends(get_db)):
    """Return a dynamic SVG badge showing feedback count for a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    question = (
        db.query(Question)
        .filter(Question.project_id == project_id, Question.is_active == True)
        .order_by(Question.created_at.desc())
        .first()
    )

    count = 0
    if question:
        count = (
            db.query(func.count(ResponseModel.id))
            .filter(ResponseModel.question_id == question.id)
            .scalar()
        )

    count_text = format_count(count)
    label = "feedback" if count != 1 else "feedback"

    # Calculate text width based on count length for proper scaling
    text_width = 70 + (len(count_text) - 1) * 8
    badge_width = 44 + text_width

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{badge_width}" height="28" viewBox="0 0 {badge_width} 28">
  <rect width="{badge_width}" height="28" rx="6" fill="#16181A"/>
  <path d="M13 18h8" fill="none" stroke="#56E83F" stroke-width="2.5" stroke-linecap="round"/>
  <path d="M21 18h2" fill="none" stroke="#56E83F" stroke-width="2.5" stroke-linecap="round"/>
  <path d="M23 18c3 0 5.5-1.7 6-4.7.4-3-1.3-5.1-3.9-5.1-2.1 0-3.4 1.3-3.4 3" fill="none" stroke="#56E83F" stroke-width="1.8" stroke-linecap="round"/>
  <path d="M22 15l.4 2.5 2.6-.9" fill="none" stroke="#56E83F" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
  <text x="36" y="18.5" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="12" font-weight="600" fill="#ffffff">{count_text} {label}</text>
</svg>'''

    return FastAPIResponse(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-cache"},
    )
