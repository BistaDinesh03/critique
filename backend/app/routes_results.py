from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Project, Question, Response
from app.schemas import ResponseOut
from app.stats import calculate_stats

router = APIRouter(prefix="/api/projects", tags=["results"])


@router.get("/{project_id}/results")
def get_project_results(project_id: int, db: Session = Depends(get_db)):
    """Get aggregated results and individual responses for a project."""
    # Validate project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get active question
    question = (
        db.query(Question)
        .filter(Question.project_id == project_id, Question.is_active == True)
        .order_by(Question.created_at.desc())
        .first()
    )
    if not question:
        return {
            "project_id": project_id,
            "project_title": project.title,
            "question_text": None,
            "stats": calculate_stats([]),
            "responses": [],
        }

    # Get all responses for this question
    responses = (
        db.query(Response)
        .filter(Response.question_id == question.id)
        .order_by(Response.created_at.desc())
        .all()
    )

    # Calculate stats
    stats = calculate_stats(responses)

    # Convert responses to output format
    response_out = [
        ResponseOut(
            id=r.id,
            clarity=r.clarity,
            would_use=r.would_use,
            suggestion=r.suggestion,
            question_id=r.question_id,
            created_at=r.created_at,
        )
        for r in responses
    ]

    return {
        "project_id": project_id,
        "project_title": project.title,
        "question_text": question.text,
        "stats": stats,
        "responses": response_out,
    }
