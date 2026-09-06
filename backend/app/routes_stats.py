from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import User, Project

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Return real platform stats for social proof."""
    total_builders = db.query(func.count(User.id)).scalar()
    total_projects = db.query(func.count(Project.id)).scalar()

    users = (
        db.query(User.username, User.avatar_url)
        .order_by(User.created_at.desc())
        .limit(4)
        .all()
    )

    builders = [
        {"username": u[0], "avatar_url": u[1]}
        for u in users
        if u[1]
    ]

    return {
        "total_builders": total_builders,
        "total_projects": total_projects,
        "builders": builders,
    }
