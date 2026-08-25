from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Project, Question
from app.schemas import ProjectCreate, ProjectOut, QuestionCreate, QuestionOut, ProjectWithQuestion
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


@router.get("/", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    """List all projects."""
    return db.query(Project).order_by(Project.created_at.desc()).all()


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
