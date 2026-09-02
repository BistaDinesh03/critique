from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Project, Question, Response, User, ProjectView
from app.schemas import (
    ProjectCreate,
    ProjectOut,
    ProjectListItem,
    QuestionCreate,
    QuestionOut,
    ProjectWithQuestion,
    PaginatedProjects,
)
from app.auth import get_current_user, get_current_user_optional
from app.csrf import require_csrf
from app.rate_limit import rate_limit
from app.ranking import calculate_project_score, get_match_reason, calculate_need_score, calculate_freshness_score, calculate_unseen_score, calculate_question_score, calculate_reciprocity_score, calculate_exploration_score
from datetime import datetime, timedelta, timezone

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
    """Create a project with its first question."""
    project = Project(
        title=project_data.title,
        description=project_data.description,
        url=project_data.url,
        image_url=project_data.image_url,
        owner_id=user.id,
        feedback_count=0,
        discover_impressions=0,
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
    current_user: User = Depends(get_current_user_optional),
):
    """List projects with ranking. Public endpoint."""
    total = db.query(func.count(Project.id)).scalar()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    offset = (page - 1) * page_size

    # Get recently viewed project IDs for current user (24h cooldown)
    recent_viewed = set()
    if current_user:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_views = (
            db.query(ProjectView.project_id)
            .filter(ProjectView.user_id == current_user.id, ProjectView.viewed_at >= cutoff)
            .all()
        )
        recent_viewed = {v[0] for v in recent_views}

    # Get candidate projects with question text
    # SQLite-compatible: use GROUP BY to get latest active question per project
    question_subq = (
        db.query(
            Question.project_id,
            func.max(Question.text).label("question_text"),
        )
        .filter(Question.is_active == True)
        .group_by(Question.project_id)
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
        .all()
    )

    # Filter eligible and rank
    ranked_items = []
    for project, question_text, response_count in projects:
        # Exclude user's own projects from Discover
        if current_user and project.owner_id == current_user.id:
            continue

        # Exclude recently viewed
        if project.id in recent_viewed:
            continue

        # Update feedback_count if stale (from response_count subquery)
        if response_count != (project.feedback_count or 0):
            project.feedback_count = response_count

        score_components = {
            "need": calculate_need_score(project),
            "freshness": calculate_freshness_score(project),
            "unseen": calculate_unseen_score(project, current_user, recent_viewed),
            "question": calculate_question_score(project, question_text),
            "reciprocity": calculate_reciprocity_score(current_user),
            "exploration": calculate_exploration_score(project, current_user),
        }

        score = min(sum(score_components.values()), 100)
        match_reason = get_match_reason(project, score_components)

        ranked_items.append({
            "project": project,
            "question_text": question_text,
            "response_count": response_count,
            "score": score,
            "match_reason": match_reason,
        })

    # Sort by score descending
    ranked_items.sort(key=lambda x: x["score"], reverse=True)

    # Apply diversity: max 1 project per owner in first 6 results
    first_six = []
    seen_owners = set()
    others = []
    for item in ranked_items:
        owner_id = item["project"].owner_id
        if len(first_six) < 6:
            if owner_id not in seen_owners:
                first_six.append(item)
                seen_owners.add(owner_id)
            else:
                others.append(item)
        else:
            others.append(item)

    final_ranked = first_six + others

    # Paginate
    page_items = final_ranked[offset:offset + page_size]

    items = []
    for item in page_items:
        p = item["project"]
        items.append(
            ProjectListItem(
                id=p.id,
                title=p.title,
                description=p.description,
                url=p.url,
                image_url=p.image_url,
                owner_id=p.owner_id,
                created_at=p.created_at,
                question_text=item["question_text"],
                response_count=item["response_count"],
            )
        )

    # Update discover impressions
    for item in page_items:
        item["project"].discover_impressions = (item["project"].discover_impressions or 0) + 1
    db.commit()

    return PaginatedProjects(
        items=items,
        total=len(items),
        page=page,
        page_size=page_size,
        total_pages=max(1, (len(final_ranked) + page_size - 1) // page_size),
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
def get_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_optional)):
    """Get a project with its active question. Public endpoint."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Record project view
    if current_user:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        existing_view = (
            db.query(ProjectView)
            .filter(
                ProjectView.user_id == current_user.id,
                ProjectView.project_id == project_id,
                ProjectView.viewed_at >= cutoff,
            )
            .first()
        )
        if not existing_view:
            view = ProjectView(user_id=current_user.id, project_id=project_id)
            db.add(view)
            db.commit()

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
    """Delete a project. Only the owner can delete it."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="You cannot delete this project")

    questions = db.query(Question).filter(Question.project_id == project_id).all()
    for question in questions:
        db.query(Response).filter(Response.question_id == question.id).delete()
        db.delete(question)

    db.query(ProjectView).filter(ProjectView.project_id == project_id).delete()
    db.delete(project)
    db.commit()
