import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.orm import Session
from app.database import get_db, in_int64_range
from app.models import Project, Question, Response, User
from app.schemas import ResponseOwnerOut
from app.stats import calculate_stats
from app.auth import get_current_user, get_current_user_optional

router = APIRouter(prefix="/api/projects", tags=["results"])


def _sanitize_csv_cell(value: str) -> str:
    """Neutralize spreadsheet formula injection for CSV export."""
    if value and isinstance(value, str):
        if value[0] in ("=", "+", "-", "@", "\t", "\r"):
            return "'" + value
    return value if value is not None else ""


@router.get("/{project_id}/results.csv")
def export_project_results_csv(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export project feedback to CSV. Owner only."""
    if not in_int64_range(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    question = (
        db.query(Question)
        .filter(Question.project_id == project_id, Question.is_active == True)
        .order_by(Question.created_at.desc())
        .first()
    )

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["created_at", "clarity", "would_use", "suggestion"])

    if question:
        responses = (
            db.query(Response)
            .filter(Response.question_id == question.id)
            .order_by(Response.created_at.desc())
            .all()
        )
        for r in responses:
            writer.writerow([
                r.created_at.isoformat() if r.created_at else "",
                _sanitize_csv_cell(r.clarity),
                _sanitize_csv_cell(r.would_use),
                _sanitize_csv_cell(r.suggestion or ""),
            ])

    return FastAPIResponse(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="project-{project_id}-feedback.csv"',
        },
    )


@router.get("/{project_id}/results")
def get_project_results(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Get aggregated results. Public stats; owner sees written responses."""
    if not in_int64_range(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Server-side authorization: use authenticated session, NOT client headers
    is_owner = current_user is not None and project.owner_id == current_user.id

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
            "is_owner": is_owner,
        }

    responses = (
        db.query(Response)
        .filter(Response.question_id == question.id)
        .order_by(Response.created_at.desc())
        .all()
    )

    stats = calculate_stats(responses)

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
