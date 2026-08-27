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

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg"
     width="150"
     height="40"
     viewBox="0 0 150 40"
     role="img"
     aria-label="Critique {count_text} feedback">

  <rect width="150" height="40" rx="8" fill="#16181A"/>

  <g transform="translate(7 6)">
    <path d="M1 19h13"
          fill="none"
          stroke="#FFFFFF"
          stroke-width="5"
          stroke-linecap="round"/>
    <path d="M14 19h4"
          fill="none"
          stroke="#56E83F"
          stroke-width="5"
          stroke-linecap="round"/>
    <path d="M18 19
             C25 19 31 15 32 9
             C33 4 29 0 24 0
             C19 0 16 3 16 7"
          fill="none"
          stroke="#FFFFFF"
          stroke-width="3.5"
          stroke-linecap="round"/>
    <path d="M16 7l1 5 5-2"
          fill="none"
          stroke="#56E83F"
          stroke-width="3"
          stroke-linecap="round"
          stroke-linejoin="round"/>
  </g>

  <path d="M55 9v22"
        stroke="#34383B"
        stroke-width="1"/>

  <circle cx="68" cy="14.5" r="3"
          fill="#56E83F"/>
  <circle cx="76" cy="16" r="2.3"
          fill="#8C9297"/>
  <path d="M62.5 27
           C62.5 22.5 65 20 68 20
           C71 20 73.5 22.5 73.5 27"
        fill="none"
        stroke="#56E83F"
        stroke-width="2.5"
        stroke-linecap="round"/>

  <text x="83"
        y="25"
        fill="#FFFFFF"
        font-family="Arial, Helvetica, sans-serif"
        font-size="15"
        font-weight="700">
    {count_text}
  </text>

  <text x="105"
        y="25"
        fill="#9CA1A5"
        font-family="Arial, Helvetica, sans-serif"
        font-size="10.5">
    feedback
  </text>

</svg>'''

    return FastAPIResponse(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-cache"},
    )
