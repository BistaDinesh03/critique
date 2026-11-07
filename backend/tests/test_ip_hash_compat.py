import os

from app import ip_hash as ip_hash_module
from app.ip_hash import hash_ip


def test_empty_salt_preserves_original_behavior(monkeypatch):
    """When IP_HASH_SALT is empty, hash_ip uses the original unsalted algorithm."""
    monkeypatch.setattr(ip_hash_module.settings, "SECRET_KEY", "test-secret")
    monkeypatch.setattr(ip_hash_module.settings, "IP_HASH_SALT", "")
    # Original algorithm: secret=SECRET_KEY, context only, message=value+ip
    import hashlib, hmac
    secret = b"test-secret"
    derived = hmac.new(secret, b"critique:ip-hash:key:v1", hashlib.sha256).digest()
    expected = hmac.new(derived, b"critique:ip-hash:value:v1\x00" + b"192.0.2.10", hashlib.sha256).hexdigest()
    assert hash_ip("192.0.2.10") == expected


def test_salt_changes_hash(monkeypatch):
    monkeypatch.setattr(ip_hash_module.settings, "SECRET_KEY", "test-secret")
    monkeypatch.setattr(ip_hash_module.settings, "IP_HASH_SALT", "deployment-alpha")
    first = hash_ip("192.0.2.10")

    monkeypatch.setattr(ip_hash_module.settings, "IP_HASH_SALT", "deployment-beta")
    second = hash_ip("192.0.2.10")

    assert first != second


def test_same_salt_deterministic(monkeypatch):
    monkeypatch.setattr(ip_hash_module.settings, "SECRET_KEY", "test-secret")
    monkeypatch.setattr(ip_hash_module.settings, "IP_HASH_SALT", "deployment-alpha")
    assert hash_ip("192.0.2.10") == hash_ip("192.0.2.10")