"""Tests for database migration safety."""

from unittest.mock import MagicMock, patch, call
import pytest


def test_migrate_postgresql_skips_already_nullable_user_id():
    """When responses.user_id is already nullable, no ALTER is executed."""
    from app.database import _migrate_postgresql

    mock_inspector = MagicMock()
    def get_columns_side_effect(table_name):
        if table_name == "users":
            return [{"name": "id"}, {"name": "email"}]
        elif table_name == "responses":
            return [
                {"name": "id", "nullable": False},
                {"name": "user_id", "nullable": True},
            ]
        return []
    mock_inspector.get_columns.side_effect = get_columns_side_effect

    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

    with patch("app.database.inspect", return_value=mock_inspector), \
         patch("app.database.engine", mock_engine), \
         patch("app.database.settings") as mock_settings:
        mock_settings.DATABASE_URL = "postgresql://user:pass@localhost/db"
        _migrate_postgresql()

    # ALTER for user_id should NOT have been called.
    # (users table migration may have called execute for other columns)
    calls = [c.args[0].text if hasattr(c.args[0], "text") else str(c.args[0]) for c in mock_conn.execute.call_args_list]
    user_id_alters = [c for c in calls if "DROP NOT NULL" in c]
    assert len(user_id_alters) == 0, f"Unexpected user_id ALTER: {user_id_alters}"


def test_migrate_postgresql_alters_non_nullable_user_id():
    """When responses.user_id is NOT NULL, ALTER TABLE is executed."""
    from app.database import _migrate_postgresql
    from sqlalchemy import text

    mock_inspector = MagicMock()
    def get_columns_side_effect(table_name):
        if table_name == "users":
            return [{"name": "id"}, {"name": "email"}]
        elif table_name == "responses":
            return [
                {"name": "id", "nullable": False},
                {"name": "user_id", "nullable": False},
            ]
        return []
    mock_inspector.get_columns.side_effect = get_columns_side_effect

    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

    with patch("app.database.inspect", return_value=mock_inspector), \
         patch("app.database.engine", mock_engine), \
         patch("app.database.settings") as mock_settings:
        mock_settings.DATABASE_URL = "postgresql://user:pass@localhost/db"
        _migrate_postgresql()

    # ALTER for user_id should have been called.
    calls = [c.args[0].text if hasattr(c.args[0], "text") else str(c.args[0]) for c in mock_conn.execute.call_args_list]
    user_id_alters = [c for c in calls if "DROP NOT NULL" in c]
    assert len(user_id_alters) == 1, f"Expected 1 user_id ALTER, got {len(user_id_alters)}"


def test_migrate_postgresql_raises_on_alter_failure():
    """If ALTER TABLE fails, migration raises RuntimeError."""
    from app.database import _migrate_postgresql

    mock_inspector = MagicMock()
    def get_columns_side_effect(table_name):
        if table_name == "users":
            return [{"name": "id"}, {"name": "email"}]
        elif table_name == "responses":
            return [
                {"name": "id", "nullable": False},
                {"name": "user_id", "nullable": False},
            ]
        return []
    mock_inspector.get_columns.side_effect = get_columns_side_effect

    mock_engine = MagicMock()
    mock_conn = MagicMock()
    def execute_side_effect(stmt):
        text_val = stmt.text if hasattr(stmt, "text") else str(stmt)
        if "DROP NOT NULL" in text_val:
            raise Exception("permission denied")
        return MagicMock()
    mock_conn.execute.side_effect = execute_side_effect
    mock_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

    with patch("app.database.inspect", return_value=mock_inspector), \
         patch("app.database.engine", mock_engine), \
         patch("app.database.settings") as mock_settings:
        mock_settings.DATABASE_URL = "postgresql://user:pass@localhost/db"
        with pytest.raises(RuntimeError, match="Database migration failed"):
            _migrate_postgresql()


def test_migrate_postgresql_raises_on_missing_user_id_column():
    """If responses.user_id column is missing, raise RuntimeError."""
    from app.database import _migrate_postgresql
    import pytest

    mock_inspector = MagicMock()
    def get_columns_side_effect(table_name):
        if table_name == "users":
            return [{"name": "id"}, {"name": "email"}]
        elif table_name == "responses":
            return [
                {"name": "id", "nullable": False},
            ]
        return []
    mock_inspector.get_columns.side_effect = get_columns_side_effect

    mock_engine = MagicMock()

    with patch("app.database.inspect", return_value=mock_inspector), \
         patch("app.database.engine", mock_engine), \
         patch("app.database.settings") as mock_settings:
        mock_settings.DATABASE_URL = "postgresql://user:pass@localhost/db"
        with pytest.raises(RuntimeError, match="user_id column is missing"):
            _migrate_postgresql()
