from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Project, Question, Response, User
from app.schemas import (
    ProjectCreate,
    ProjectOut,
    ProjectListItem,
    QuestionCreate,
    QuestionOut,
    ProjectWithQuestion,
    PaginatedProjects,
)
from app.auth import get_current_user
from app.csrf import require_csrf

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("/", response_model=ProjectWithQuestion, status_code=201)
def create_project_with_question(
    project_data: ProjectCreate,
    question_data: QuestionCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    """Create a project with its first question. Requires authentication and CSRF."""
    project = Project(
        title=project_data.title,
        description=project_data.description,
        url=project_data.url,
        image_url=project_data.image_url,
        owner_id=user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    question = Question(
        text=question_data.text,
        project_id=project.id,
        is_active=True,
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    return ProjectWithQuestion(project=project, question=question)


@router.get("/", response_model=PaginatedProjects)
def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """List projects with pagination. Public endpoint."""
    total = db.query(func.count(Project.id)).scalar()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    offset = (page - 1) * page_size

    projects = (
        db.query(Project)
        .order_by(Project.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = []
    for project in projects:
        question = (
            db.query(Question)
            .filter(Question.project_id == project.id, Question.is_active == True)
            .order_by(Question.created_at.desc())
            .first()
        )

        response_count = 0
        question_text = None
        if question:
            question_text = question.text
            response_count = (
                db.query(func.count(Response.id))
                .filter(Response.question_id == question.id)
                .scalar()
            )

        items.append(
            ProjectListItem(
                id=project.id,
                title=project.title,
                description=project.description,
                url=project.url,
                image_url=project.image_url,
                owner_id=project.owner_id,
                created_at=project.created_at,
                question_text=question_text,
                response_count=response_count,
            )
        )

    return PaginatedProjects(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{project_id}", response_model=ProjectWithQuestion)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get a project with its active question. Public endpoint."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    question = (
        db.query(Question)
        .filter(Question.project_id == project_id, Question.is_active == True)
        .order_by(Question.created_at.desc())
        .first()
    )

    return ProjectWithQuestion(project=project, question=question)


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    """Delete a project. Only the owner can delete it. Requires CSRF."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="You cannot delete this project")

    questions = db.query(Question).filter(Question.project_id == project_id).all()
    for question in questions:
        db.query(Response).filter(Response.question_id == question.id).delete()
        db.delete(question)

    db.delete(project)
    db.commit()
