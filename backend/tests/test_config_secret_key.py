import os

import pytest


def test_resolve_secret_key_missing_in_production_raises(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    from app import config

    with pytest.raises(RuntimeError, match="SECRET_KEY is not set"):
        config._resolve_secret_key("production")


def test_resolve_secret_key_empty_in_production_raises(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "")
    from app import config

    with pytest.raises(RuntimeError, match="SECRET_KEY is not set"):
        config._resolve_secret_key("production")


def test_resolve_secret_key_whitespace_in_production_raises(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "   ")
    from app import config

    with pytest.raises(RuntimeError, match="SECRET_KEY is not set"):
        config._resolve_secret_key("production")


def test_resolve_secret_key_dev_fallback_is_nonempty(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    from app import config

    key = config._resolve_secret_key("development")
    assert isinstance(key, str) and len(key) >= 16


def test_resolve_secret_key_valid_production(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "super-secret-production-key")
    from app import config

    assert config._resolve_secret_key("production") == "super-secret-production-key"
