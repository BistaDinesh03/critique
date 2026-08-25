"""
TEMPORARY DEVELOPMENT USER — WILL BE REPLACED BY GITHUB OAUTH.

This module provides a temporary user for development.
When authentication is implemented, this entire module will be removed
and replaced with proper GitHub OAuth user resolution.
"""

from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User

DEV_USERNAME = "dev_user"
DEV_GITHUB_ID = 99999999


def get_or_create_dev_user(db: Session = Depends(get_db)) -> User:
    """Get or create the development user."""
    user = db.query(User).filter(User.username == DEV_USERNAME).first()
    if not user:
        user = User(github_id=DEV_GITHUB_ID, username=DEV_USERNAME)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
