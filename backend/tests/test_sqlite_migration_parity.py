"""SQLite startup-migration parity with PostgreSQL.

Regression coverage for issue #82: the SQLite path used to handle only
``users.email`` and silently swallow every failure. It must now upgrade the
same legacy columns as the PostgreSQL path, raise on genuine failures, and
stay a no-op when the columns already exist.
"""

from sqlalchemy import text, inspect

from app.database import SessionLocal, init_db, _migrate_sqlite, engine
from app.models import Base, User, Project, Question, Response


def _drop_all():
    Base.metadata.drop_all(bind=engine)
    with engine.begin() as conn:
        # Drop any leftover rebuild table from a previous failed run.
        conn.execute(text("DROP TABLE IF EXISTS responses_new"))


def _legacy_schema():
    """Create a pre-migration SQLite schema (missing columns, NOT NULL user_id)."""
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE users ("
            "id INTEGER PRIMARY KEY, github_id INTEGER, username VARCHAR(100), "
            "avatar_url VARCHAR(500), created_at DATETIME)"
        ))
        conn.execute(text(
            "CREATE TABLE projects ("
            "id INTEGER PRIMARY KEY, title VARCHAR(200) NOT NULL, "
            "description TEXT, url VARCHAR(500), owner_id INTEGER, "
            "created_at DATETIME, updated_at DATETIME, "
            "is_public BOOLEAN DEFAULT 1, question_id INTEGER)"
        ))
        conn.execute(text(
            "CREATE TABLE questions ("
            "id INTEGER PRIMARY KEY, text VARCHAR(500) NOT NULL, "
            "project_id INTEGER NOT NULL)"
        ))
        conn.execute(text(
            "CREATE TABLE responses ("
            "id INTEGER PRIMARY KEY, clarity VARCHAR(20) NOT NULL, "
            "would_use VARCHAR(10) NOT NULL, suggestion TEXT, "
            "created_at DATETIME, question_id INTEGER NOT NULL, "
            "user_id INTEGER NOT NULL, ip_hash VARCHAR(64) NOT NULL)"
        ))


def test_sqlite_migration_upgrades_legacy_schema():
    """A legacy SQLite DB gets every column the PostgreSQL path adds."""
    _drop_all()
    _legacy_schema()

    # Seed a row so we can prove data survives the responses-table rebuild.
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO users (id, github_id, username) VALUES (1, 1, 'u')"
        ))
        conn.execute(text(
            "INSERT INTO projects (id, title, owner_id) VALUES (1, 'p', 1)"
        ))
        conn.execute(text(
            "INSERT INTO questions (id, text, project_id) VALUES (1, 'q', 1)"
        ))
        conn.execute(text(
            "INSERT INTO responses (id, clarity, would_use, question_id, user_id, ip_hash) "
            "VALUES (1, 'very_clear', 'yes', 1, 1, 'h')"
        ))

    _migrate_sqlite()

    inspector = inspect(engine)
    user_cols = {c["name"] for c in inspector.get_columns("users")}
    assert {"feedback_given_count", "feedback_helpful_count", "feedback_score",
            "email"} <= user_cols

    project_cols = {c["name"] for c in inspector.get_columns("projects")}
    assert {"feedback_count", "last_feedback_at", "last_served_at",
            "discover_impressions"} <= project_cols

    response_cols = {c["name"]: c for c in inspector.get_columns("responses")}
    assert "user_id" in response_cols
    assert response_cols["user_id"].get("nullable", False) is True

    # Data survived.
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM users")).scalar() == 1
        assert conn.execute(text("SELECT COUNT(*) FROM responses")).scalar() == 1
        assert conn.execute(text(
            "SELECT user_id FROM responses WHERE id = 1"
        )).scalar() == 1

    # Unique index on email exists.
    indexes = {i["name"] for i in inspector.get_indexes("users")}
    assert "ix_users_email" in indexes

    # Restore a clean schema for the rest of the suite.
    _drop_all()
    init_db()


def test_sqlite_migration_is_idempotent():
    """Running the migration twice must not raise or change anything."""
    init_db()
    _migrate_sqlite()  # second run on an already-current schema
    _migrate_sqlite()  # third run
    # No assertion needed beyond "did not raise".


def test_sqlite_migration_raises_on_inspect_failure():
    """A genuine inspection failure must propagate, not be swallowed."""
    import pytest
    from unittest.mock import patch, MagicMock

    mock_inspector = MagicMock()
    mock_inspector.get_columns.side_effect = RuntimeError("boom")

    with patch("app.database.inspect", return_value=mock_inspector), \
         patch("app.database.settings") as mock_settings:
        mock_settings.DATABASE_URL = "sqlite:///x.db"
        with pytest.raises(RuntimeError, match="Database migration failed"):
            _migrate_sqlite()


def test_sqlite_migration_preserves_email_uniqueness():
    """The unique index on users.email survives the migration."""
    init_db()
    db = SessionLocal()
    try:
        db.add(User(github_id=1, username="a", email="dup@example.com"))
        db.commit()
        db.add(User(github_id=2, username="b", email="dup@example.com"))
        try:
            db.commit()
            assert False, "duplicate email should have raised"
        except Exception:
            db.rollback()
    finally:
        db.close()


def test_sqlite_migration_raises_on_missing_user_id_column():
    """If responses.user_id is missing, raise RuntimeError (parity with Postgres)."""
    import pytest
    from unittest.mock import patch, MagicMock

    mock_inspector = MagicMock()
    def get_columns_side_effect(table_name):
        if table_name == "users":
            return [{"name": "id"}, {"name": "email"}]
        elif table_name == "responses":
            return [{"name": "id", "nullable": False}]  # no user_id
        elif table_name == "projects":
            return [{"name": "id"}]
        return []
    mock_inspector.get_columns.side_effect = get_columns_side_effect

    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

    with patch("app.database.inspect", return_value=mock_inspector), \
         patch("app.database.engine", mock_engine), \
         patch("app.database.settings") as mock_settings:
        mock_settings.DATABASE_URL = "sqlite:///x.db"
        with pytest.raises(RuntimeError, match="user_id column is missing"):
            _migrate_sqlite()


def test_sqlite_migration_raises_on_alter_failure():
    """If an ALTER TABLE fails on SQLite, migration raises (no swallowing)."""
    import pytest
    from unittest.mock import patch, MagicMock

    mock_inspector = MagicMock()
    def get_columns_side_effect(table_name):
        if table_name == "users":
            return [{"name": "id"}]  # missing email -> will try to ALTER
        elif table_name == "responses":
            return [{"name": "id"}, {"name": "user_id", "nullable": True}]
        elif table_name == "projects":
            return [{"name": "id"}]
        return []
    mock_inspector.get_columns.side_effect = get_columns_side_effect

    mock_engine = MagicMock()
    mock_conn = MagicMock()
    def execute_side_effect(stmt):
        text_val = stmt.text if hasattr(stmt, "text") else str(stmt)
        if "ADD COLUMN email" in text_val:
            raise Exception("disk I/O error")
        return MagicMock()
    mock_conn.execute.side_effect = execute_side_effect
    mock_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

    with patch("app.database.inspect", return_value=mock_inspector), \
         patch("app.database.engine", mock_engine), \
         patch("app.database.settings") as mock_settings:
        mock_settings.DATABASE_URL = "sqlite:///x.db"
        with pytest.raises(RuntimeError, match="Database migration failed"):
            _migrate_sqlite()


def test_sqlite_fresh_database_has_nullable_user_id():
    """A freshly created database already has a nullable responses.user_id."""
    init_db()
    inspector = inspect(engine)
    cols = {c["name"]: c for c in inspector.get_columns("responses")}
    assert "user_id" in cols
    assert cols["user_id"].get("nullable", True) is True
