import os
from contextlib import contextmanager
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

def get_engine_kwargs(database_url: str = None, config=None) -> dict:
    """Return engine keyword arguments based on the database URL and config settings."""
    cfg = config or settings
    url = database_url if database_url is not None else cfg.DATABASE_URL
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {
        "pool_size": getattr(cfg, "DB_POOL_SIZE", 5),
        "max_overflow": getattr(cfg, "DB_MAX_OVERFLOW", 10),
        "pool_timeout": getattr(cfg, "DB_POOL_TIMEOUT", 30),
        "pool_recycle": getattr(cfg, "DB_POOL_RECYCLE", 1800),
        "pool_pre_ping": True,
    }


if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        settings.DATABASE_URL,
        **get_engine_kwargs(settings.DATABASE_URL),
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        **get_engine_kwargs(settings.DATABASE_URL),
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency that provides a database session, ensuring rollback and closure on exception."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def db_session():
    """Context manager that commits on clean exit, rolls back on error, and closes."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def in_int64_range(value: int) -> bool:
    """SQLite cannot bind integers outside its signed 64-bit range."""
    return -(2**63) <= value < 2**63


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
        if "email" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(320)"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)"))
    
    # Check responses table - make user_id nullable for guest submissions.
    # This is a required migration: guest feedback submission depends on it.
    response_cols = {c["name"]: c for c in inspector.get_columns("responses")}
    user_id_col = response_cols.get("user_id")
    if user_id_col is not None and not user_id_col.get("nullable", True):
        # Column exists and is NOT NULL - migrate it.
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE responses ALTER COLUMN user_id DROP NOT NULL"))
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error(
                "FAILED to make responses.user_id nullable for guest submissions: %s", exc
            )
            raise RuntimeError(
                "Database migration failed: could not make responses.user_id nullable. "
                "Guest feedback submission requires a nullable user_id column. "
                "See logs for details."
            ) from exc

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


def _migrate_sqlite():
    """Add missing columns to existing tables on SQLite."""
    inspector = inspect(engine)
    user_cols = {c["name"] for c in inspector.get_columns("users")}
    with engine.begin() as conn:
        if "email" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(320)"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)"))


def init_db():
    """Create all tables and run lightweight migrations."""
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Add missing columns on the appropriate backend
    if settings.DATABASE_URL.startswith("sqlite"):
        try:
            _migrate_sqlite()
        except Exception:
            pass  # Columns may already exist
    else:
        _migrate_postgresql()