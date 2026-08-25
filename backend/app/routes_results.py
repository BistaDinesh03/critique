from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Project, Question, Response, User
from app.schemas import ResponseOwnerOut
from app.stats import calculate_stats

router = APIRouter(prefix="/api/projects", tags=["results"])


@router.get("/{project_id}/results")
def get_project_results(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get aggregated results. Public stats; owner sees written responses."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

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
            "is_owner": False,
        }

    responses = (
        db.query(Response)
        .filter(Response.question_id == question.id)
        .order_by(Response.created_at.desc())
        .all()
    )

    stats = calculate_stats(responses)

    # Determine if the requester is the owner using the X-Owner-ID header
    owner_id_header = request.headers.get("X-Owner-ID")
    is_owner = False
    if owner_id_header:
        try:
            is_owner = int(owner_id_header) == project.owner_id
        except ValueError:
            is_owner = False

    response_out = []
    if is_owner:
        response_out = [
            ResponseOwnerOut(
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
        "is_owner": is_owner,
    }
