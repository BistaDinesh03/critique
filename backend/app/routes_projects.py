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
from app.rate_limit import rate_limit

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("/", response_model=ProjectWithQuestion, status_code=201)
def create_project_with_question(
    project_data: ProjectCreate,
    question_data: QuestionCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
    __: None = Depends(rate_limit("project_create")),
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
    """List projects with pagination. Public endpoint. Optimized with single query."""
    total = db.query(func.count(Project.id)).scalar()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    offset = (page - 1) * page_size

    # Single optimized query with subqueries for question and response count
    question_subq = (
        db.query(
            Question.project_id,
            Question.text.label("question_text"),
        )
        .filter(Question.is_active == True)
        .distinct(Question.project_id)
        .order_by(Question.project_id, Question.created_at.desc())
        .subquery()
    )

    response_count_subq = (
        db.query(
            Response.question_id,
            func.count(Response.id).label("response_count"),
        )
        .group_by(Response.question_id)
        .subquery()
    )

    projects = (
        db.query(
            Project,
            question_subq.c.question_text,
            func.coalesce(response_count_subq.c.response_count, 0).label("response_count"),
        )
        .outerjoin(question_subq, question_subq.c.project_id == Project.id)
        .outerjoin(response_count_subq, response_count_subq.c.question_id == question_subq.c.project_id)
        .order_by(Project.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = []
    for project, question_text, response_count in projects:
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


@router.get("/my/list")
def list_my_projects(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List projects owned by the current user."""
    question_subq = (
        db.query(
            Question.project_id,
            Question.text.label("question_text"),
        )
        .filter(Question.is_active == True)
        .distinct(Question.project_id)
        .order_by(Question.project_id, Question.created_at.desc())
        .subquery()
    )

    response_count_subq = (
        db.query(
            Response.question_id,
            func.count(Response.id).label("response_count"),
        )
        .group_by(Response.question_id)
        .subquery()
    )

    projects = (
        db.query(
            Project,
            question_subq.c.question_text,
            func.coalesce(response_count_subq.c.response_count, 0).label("response_count"),
        )
        .outerjoin(question_subq, question_subq.c.project_id == Project.id)
        .outerjoin(response_count_subq, response_count_subq.c.question_id == question_subq.c.project_id)
        .filter(Project.owner_id == user.id)
        .order_by(Project.created_at.desc())
        .all()
    )

    items = []
    for project, question_text, response_count in projects:
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

    return items


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
    __: None = Depends(rate_limit("project_create")),
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
