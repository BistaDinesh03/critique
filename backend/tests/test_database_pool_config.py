import os
from unittest.mock import patch
from app.config import Settings, settings
from app.database import get_engine_kwargs


def test_default_database_pool_settings():
    """Verify default database connection pool settings."""
    assert settings.DB_POOL_SIZE == 5
    assert settings.DB_MAX_OVERFLOW == 10
    assert settings.DB_POOL_TIMEOUT == 30
    assert settings.DB_POOL_RECYCLE == 1800


def test_custom_database_pool_settings_from_env():
    """Verify database connection pool settings are configurable via environment variables."""
    env = {
        "DB_POOL_SIZE": "25",
        "DB_MAX_OVERFLOW": "50",
        "DB_POOL_TIMEOUT": "60",
        "DB_POOL_RECYCLE": "3600",
    }
    with patch.dict(os.environ, env):
        custom_settings = Settings()
        assert custom_settings.DB_POOL_SIZE == 25
        assert custom_settings.DB_MAX_OVERFLOW == 50
        assert custom_settings.DB_POOL_TIMEOUT == 60
        assert custom_settings.DB_POOL_RECYCLE == 3600


def test_get_engine_kwargs_for_sqlite_vs_postgresql():
    """Verify sqlite gets check_same_thread and postgresql gets pool configuration."""
    sqlite_kwargs = get_engine_kwargs("sqlite:///./critique.db")
    assert sqlite_kwargs == {"connect_args": {"check_same_thread": False}}

    pg_kwargs = get_engine_kwargs("postgresql://user:pass@localhost:5432/critique")
    assert pg_kwargs["pool_size"] == settings.DB_POOL_SIZE
    assert pg_kwargs["max_overflow"] == settings.DB_MAX_OVERFLOW
    assert pg_kwargs["pool_timeout"] == settings.DB_POOL_TIMEOUT
    assert pg_kwargs["pool_recycle"] == settings.DB_POOL_RECYCLE
    assert pg_kwargs["pool_pre_ping"] is True


def test_get_engine_kwargs_with_monkeypatched_settings(monkeypatch):
    """Verify get_engine_kwargs respects monkeypatched settings."""
    monkeypatch.setattr(settings, "DB_POOL_SIZE", 42)
    monkeypatch.setattr(settings, "DB_MAX_OVERFLOW", 84)
    pg_kwargs = get_engine_kwargs("postgresql://user:pass@localhost:5432/critique")
    assert pg_kwargs["pool_size"] == 42
    assert pg_kwargs["max_overflow"] == 84


def test_get_engine_kwargs_with_custom_settings_instance():
    """Verify get_engine_kwargs accepts an explicit custom Settings instance."""
    custom = Settings()
    custom.DB_POOL_SIZE = 15
    custom.DB_MAX_OVERFLOW = 30
    pg_kwargs = get_engine_kwargs("postgresql://user:pass@localhost:5432/critique", config=custom)
    assert pg_kwargs["pool_size"] == 15
    assert pg_kwargs["max_overflow"] == 30
