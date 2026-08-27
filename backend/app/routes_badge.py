from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Project, Question, Response as ResponseModel

router = APIRouter(prefix="/badge", tags=["badge"])


def format_count(count: int) -> str:
    """Format count for display. 1000+ shows as 1k+."""
    if count >= 1000:
        return "1k+"
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
    label = "reviews" if count != 1 else "review"

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg"
     width="215" height="40" viewBox="0 0 215 40">

  <rect width="215" height="40" rx="20" fill="#16181A"/>

  <g transform="translate(8 7)">
    <path d="M1 19h12M13 19h4"
          fill="none" stroke="#fff" stroke-width="4"
          stroke-linecap="round"/>
    <path d="M17 19C23 19 28 16 29 11C30 6 27 2 23 2C19 2 17 4 17 8"
          fill="none" stroke="#fff" stroke-width="3"
          stroke-linecap="round"/>
    <path d="M17 8l1 5 5-2"
          fill="none" stroke="#56E83F" stroke-width="2.5"
          stroke-linecap="round" stroke-linejoin="round"/>
  </g>

  <text x="43" y="25" fill="#fff"
        font-family="Arial,sans-serif"
        font-size="12" font-weight="700">Critique</text>

  <circle cx="99" cy="20" r="2" fill="#555B60"/>

  <text x="108" y="25" fill="#56E83F"
        font-family="Arial,sans-serif"
        font-size="12" font-weight="700">{count_text}</text>

  <text x="128" y="25" fill="#D1D5D8"
        font-family="Arial,sans-serif"
        font-size="11">{label}</text>

  <text x="178" y="25" fill="#56E83F"
        font-family="Arial,sans-serif"
        font-size="11" font-weight="700">&#8599;</text>
</svg>'''

    return FastAPIResponse(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-cache"},
    )

