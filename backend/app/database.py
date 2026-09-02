import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=5,
        max_overflow=3,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_postgresql():
    """Add missing columns to existing tables on PostgreSQL."""
    inspector = inspect(engine)
    
    # Check users table
    user_cols = {c["name"] for c in inspector.get_columns("users")}
    with engine.begin() as conn:
        if "feedback_given_count" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN feedback_given_count INTEGER DEFAULT 0 NOT NULL"))
        if "feedback_helpful_count" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN feedback_helpful_count INTEGER DEFAULT 0 NOT NULL"))
        if "feedback_score" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN feedback_score INTEGER DEFAULT 0 NOT NULL"))
    
    # Check projects table
    project_cols = {c["name"] for c in inspector.get_columns("projects")}
    with engine.begin() as conn:
        if "feedback_count" not in project_cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN feedback_count INTEGER DEFAULT 0 NOT NULL"))
        if "last_feedback_at" not in project_cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN last_feedback_at TIMESTAMP"))
        if "last_served_at" not in project_cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN last_served_at TIMESTAMP"))
        if "discover_impressions" not in project_cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN discover_impressions INTEGER DEFAULT 0 NOT NULL"))


def init_db():
    """Create all tables and run lightweight migrations."""
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    
    # Add missing columns on PostgreSQL
    if not settings.DATABASE_URL.startswith("sqlite"):
        try:
            _migrate_postgresql()
        except Exception:
            pass  # Columns may already exist
