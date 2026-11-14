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
    try:
        response_cols = {c["name"]: c for c in inspector.get_columns("responses")}
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(
            "FAILED to inspect responses table: %s", exc
        )
        raise RuntimeError(
            "Database migration failed: could not inspect responses table. "
            "Guest feedback submission requires a responses table with a user_id column."
        ) from exc

    user_id_col = response_cols.get("user_id")
    if user_id_col is None:
        # The responses table exists but user_id column is missing.
        # This indicates an incompatible schema - fail loudly.
        import logging
        logging.getLogger(__name__).error(
            "responses.user_id column is missing. "
            "Expected schema: responses(user_id INTEGER, nullable=True). "
            "Run migrations or recreate the table."
        )
        raise RuntimeError(
            "Database migration failed: responses.user_id column is missing. "
            "Guest feedback submission requires this column. "
            "The table may need to be recreated or migrated manually."
        )

    if not user_id_col.get("nullable", True):
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


def _make_responses_user_id_nullable_sqlite():
    """Make responses.user_id nullable on SQLite.

    SQLite has no ``ALTER TABLE ... ALTER COLUMN ... DROP NOT NULL``, so a
    legacy NOT NULL column has to be rebuilt. This follows the standard SQLite
    table-rebuild procedure. Genuine failures raise ``RuntimeError``; an
    already-nullable column is a no-op.
    """
    import logging

    try:
        inspector = inspect(engine)
        response_cols = {c["name"]: c for c in inspector.get_columns("responses")}
    except Exception as exc:
        logging.getLogger(__name__).error(
            "FAILED to inspect responses table on SQLite: %s", exc
        )
        raise RuntimeError(
            "Database migration failed: could not inspect the responses table. "
            "Guest feedback submission requires a responses table with a "
            "user_id column."
        ) from exc

    if "user_id" not in response_cols:
        logging.getLogger(__name__).error(
            "responses.user_id column is missing on SQLite."
        )
        raise RuntimeError(
            "Database migration failed: responses.user_id column is missing. "
            "Guest feedback submission requires this column. The table may need "
            "to be recreated or migrated manually."
        )

    if response_cols["user_id"].get("nullable", True):
        return  # Already nullable - nothing to do.

    # Rebuild the table with a nullable user_id. Keep the column list in sync
    # with backend/app/models.py::Response.
    column_names = list(response_cols)
    common = [c for c in ("id", "clarity", "would_use", "suggestion",
                          "created_at", "question_id", "user_id", "ip_hash")
              if c in column_names]

    try:
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE TABLE responses_new ("
                "id INTEGER PRIMARY KEY, "
                "clarity VARCHAR(20) NOT NULL, "
                "would_use VARCHAR(10) NOT NULL, "
                "suggestion TEXT, "
                "created_at DATETIME, "
                "question_id INTEGER NOT NULL REFERENCES questions(id), "
                "user_id INTEGER REFERENCES users(id), "
                "ip_hash VARCHAR(64) NOT NULL"
                ")"
            ))
            if common:
                cols = ", ".join(common)
                conn.execute(text(
                    "INSERT INTO responses_new (%s) SELECT %s FROM responses"
                    % (cols, cols)
                ))
            conn.execute(text("DROP TABLE responses"))
            conn.execute(text("ALTER TABLE responses_new RENAME TO responses"))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_responses_question_id "
                "ON responses (question_id)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_responses_user_id "
                "ON responses (user_id)"
            ))
    except Exception as exc:
        logging.getLogger(__name__).error(
            "FAILED to make responses.user_id nullable on SQLite: %s", exc
        )
        raise RuntimeError(
            "Database migration failed: could not make responses.user_id "
            "nullable on SQLite. Guest feedback submission requires a nullable "
            "user_id column. See logs for details."
        ) from exc


def _migrate_sqlite():
    """Add missing columns to existing tables on SQLite.

    Mirrors ``_migrate_postgresql`` so a legacy SQLite database ends up with
    the same shape. Statements are guarded on ``inspect()`` so a second run is
    a no-op, and genuine failures raise instead of being swallowed.
    """
    import logging

    try:
        inspector = inspect(engine)
    except Exception as exc:
        logging.getLogger(__name__).error(
            "FAILED to inspect SQLite database: %s", exc
        )
        raise RuntimeError(
            "Database migration failed: could not inspect the SQLite database."
        ) from exc

    # --- users table -------------------------------------------------------
    try:
        user_cols = {c["name"] for c in inspector.get_columns("users")}
    except Exception as exc:
        logging.getLogger(__name__).error(
            "FAILED to inspect users table on SQLite: %s", exc
        )
        raise RuntimeError(
            "Database migration failed: could not inspect the users table."
        ) from exc

    try:
        with engine.begin() as conn:
            if "feedback_given_count" not in user_cols:
                conn.execute(text(
                    "ALTER TABLE users ADD COLUMN feedback_given_count "
                    "INTEGER DEFAULT 0 NOT NULL"
                ))
            if "feedback_helpful_count" not in user_cols:
                conn.execute(text(
                    "ALTER TABLE users ADD COLUMN feedback_helpful_count "
                    "INTEGER DEFAULT 0 NOT NULL"
                ))
            if "feedback_score" not in user_cols:
                conn.execute(text(
                    "ALTER TABLE users ADD COLUMN feedback_score "
                    "INTEGER DEFAULT 0 NOT NULL"
                ))
            if "email" not in user_cols:
                conn.execute(text(
                    "ALTER TABLE users ADD COLUMN email VARCHAR(320)"
                ))
                conn.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email "
                    "ON users (email)"
                ))
    except Exception as exc:
        logging.getLogger(__name__).error(
            "FAILED to migrate users table on SQLite: %s", exc
        )
        raise RuntimeError(
            "Database migration failed on the users table (SQLite)."
        ) from exc

    # --- responses table ---------------------------------------------------
    _make_responses_user_id_nullable_sqlite()

    # --- projects table ----------------------------------------------------
    try:
        project_cols = {c["name"] for c in inspector.get_columns("projects")}
    except Exception as exc:
        logging.getLogger(__name__).error(
            "FAILED to inspect projects table on SQLite: %s", exc
        )
        raise RuntimeError(
            "Database migration failed: could not inspect the projects table."
        ) from exc

    try:
        with engine.begin() as conn:
            if "feedback_count" not in project_cols:
                conn.execute(text(
                    "ALTER TABLE projects ADD COLUMN feedback_count "
                    "INTEGER DEFAULT 0 NOT NULL"
                ))
            if "last_feedback_at" not in project_cols:
                conn.execute(text(
                    "ALTER TABLE projects ADD COLUMN last_feedback_at TIMESTAMP"
                ))
            if "last_served_at" not in project_cols:
                conn.execute(text(
                    "ALTER TABLE projects ADD COLUMN last_served_at TIMESTAMP"
                ))
            if "discover_impressions" not in project_cols:
                conn.execute(text(
                    "ALTER TABLE projects ADD COLUMN discover_impressions "
                    "INTEGER DEFAULT 0 NOT NULL"
                ))
    except Exception as exc:
        logging.getLogger(__name__).error(
            "FAILED to migrate projects table on SQLite: %s", exc
        )
        raise RuntimeError(
            "Database migration failed on the projects table (SQLite)."
        ) from exc


def init_db():
    """Create all tables and run lightweight migrations."""
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Add missing columns on the appropriate backend. Failures are deliberate:
    # a silent pass here is exactly what let legacy schemas drift.
    if settings.DATABASE_URL.startswith("sqlite"):
        _migrate_sqlite()
    else:
        _migrate_postgresql()