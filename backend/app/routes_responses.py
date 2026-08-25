import hashlib
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Project, Question, Response, User
from app.schemas import ResponseCreate, ResponseOut
from app.auth import get_current_user
from app.csrf import require_csrf
from app.rate_limit import rate_limit

router = APIRouter(prefix="/api/projects", tags=["responses"])


def hash_ip(ip: str) -> str:
    """Hash an IP address for privacy-preserving duplicate detection."""
    return hashlib.sha256(ip.encode()).hexdigest()


@router.post("/{project_id}/responses", response_model=ResponseOut, status_code=201)
def create_response(
    project_id: int,
    response_data: ResponseCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
    __: None = Depends(rate_limit("response_submit")),
):
    """Submit a structured response. Requires authentication and CSRF."""
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
        raise HTTPException(status_code=404, detail="No active question for this project")

    client_ip = request.client.host if request.client else "unknown"
    ip_hash = hash_ip(client_ip)

    existing = (
        db.query(Response)
        .filter(Response.question_id == question.id, Response.user_id == user.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="You have already responded to this question")

    response = Response(
        clarity=response_data.clarity,
        would_use=response_data.would_use,
        suggestion=response_data.suggestion,
        question_id=question.id,
        user_id=user.id,
        ip_hash=ip_hash,
    )
    db.add(response)
    db.commit()
    db.refresh(response)

    return response


@router.get("/{project_id}/responses", response_model=list[ResponseOut])
def list_responses(project_id: int, db: Session = Depends(get_db)):
    """List all responses for a project's active question. Public endpoint."""
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
        return []

    responses = (
        db.query(Response)
        .filter(Response.question_id == question.id)
        .order_by(Response.created_at.desc())
        .all()
    )

    return responses


