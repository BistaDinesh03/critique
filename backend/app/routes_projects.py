from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Project, Question, Response
from app.schemas import (
    ProjectCreate,
    ProjectOut,
    ProjectListItem,
    QuestionCreate,
    QuestionOut,
    ProjectWithQuestion,
    PaginatedProjects,
)
from app.temp_user import get_or_create_dev_user

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("/", response_model=ProjectWithQuestion, status_code=201)
def create_project_with_question(
    project_data: ProjectCreate,
    question_data: QuestionCreate,
    db: Session = Depends(get_db),
    user=Depends(get_or_create_dev_user),
):
    """Create a project with its first question."""
    # Create project
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

    # Create question
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
    """List projects with pagination and response counts."""
    # Get total count
    total = db.query(func.count(Project.id)).scalar()

    # Calculate pagination
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    offset = (page - 1) * page_size

    # Get projects for current page
    projects = (
        db.query(Project)
        .order_by(Project.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    # Build list items with question text and response count
    items = []
    for project in projects:
        # Get active question
        question = (
            db.query(Question)
            .filter(Question.project_id == project.id, Question.is_active == True)
            .order_by(Question.created_at.desc())
            .first()
        )

        # Count responses for active question
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
    """Get a project with its active question."""
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

    return ProjectWithQuestion(project=project, question=question)
