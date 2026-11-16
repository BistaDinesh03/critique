"""Smoke tests for production dependency availability.

These tests verify that the production dependency manifest includes
all required packages for the PostgreSQL deployment path. They run in
CI with the same dependency set Render installs.
"""

import os
import re

import pytest


def test_requirements_includes_psycopg_not_psycopg2():
    """Production requirements must include psycopg (v3), not psycopg2."""
    req_path = os.path.join(
        os.path.dirname(__file__), "..", "requirements.txt"
    )
    req_path = os.path.abspath(req_path)
    with open(req_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "psycopg" in content, "psycopg must be in requirements.txt"
    assert "psycopg2" not in content, "psycopg2 must NOT be in requirements.txt (use psycopg 3)"
    # Verify it's the binary variant for deployment
    assert "psycopg[binary]" in content, "Must use psycopg[binary] for deployment"


def test_psycopg_package_installed():
    """The psycopg package must be installed in the environment."""
    from importlib.metadata import version, PackageNotFoundError

    try:
        v = version("psycopg")
    except PackageNotFoundError:
        pytest.fail("psycopg is not installed")

    major = int(v.split(".")[0])
    assert major >= 3, f"Expected psycopg 3.x, got {v}"


def test_psycopg_importable():
    """The psycopg DBAPI must be importable (verifies binary wheels work)."""
    try:
        import psycopg

        assert hasattr(psycopg, "connect")
    except ImportError as e:
        pytest.fail(f"psycopg cannot be imported: {e}")


def test_sqlalchemy_postgresql_dialect_loads():
    """SQLAlchemy must be able to load the postgresql+psycopg dialect."""
    try:
        from sqlalchemy import create_engine

        engine = create_engine("postgresql+psycopg://user:pass@localhost/db")
        assert engine is not None
        assert engine.dialect.driver == "psycopg"
    except Exception as e:
        pytest.fail(f"SQLAlchemy postgresql+psycopg dialect failed to load: {e}")


def test_fastapi_app_imports():
    """The FastAPI application must import without errors."""
    from app.main import app

    assert app is not None
    assert app.title == "Critique"


def test_database_module_imports():
    """The database module must import without errors (uses SQLite by default)."""
    from app.database import engine, SessionLocal, Base

    assert engine is not None
    assert SessionLocal is not None
    assert Base is not None
