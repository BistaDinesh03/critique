import hashlib
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Project, Question, Response, User
from app.schemas import ResponseCreate, ResponseOut, ResponseOwnerOut
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


@router.get("/{project_id}/responses")
def list_responses(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """List responses. Public sees stats only; owner sees written suggestions."""
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

    # Determine if the requester is the owner using the X-Owner-ID header
    # Frontend sets this header when the user is authenticated as the project owner
    owner_id_header = request.headers.get("X-Owner-ID")
    is_owner = owner_id_header is not None and int(owner_id_header) == project.owner_id

    if is_owner:
        return [
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

    return [
        ResponseOut(
            id=r.id,
            clarity=r.clarity,
            would_use=r.would_use,
            question_id=r.question_id,
            created_at=r.created_at,
        )
        for r in responses
    ]
