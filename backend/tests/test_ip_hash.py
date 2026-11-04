
import hashlib
import re
import subprocess
import sys
from pathlib import Path

import app.ip_hash as ip_hash_module
from app.ip_hash import hash_ip


def test_ip_hash_is_stable_for_same_ip_and_secret(monkeypatch):
    monkeypatch.setattr(
        ip_hash_module.settings, "SECRET_KEY", "test-secret-one"
    )
    assert hash_ip("192.0.2.10") == hash_ip("192.0.2.10")


def test_ip_hash_is_stable_across_processes():
    backend_dir = Path(__file__).resolve().parents[1]
    script = """
from app.config import settings
settings.SECRET_KEY = "test-secret-one"
from app.ip_hash import hash_ip
print(hash_ip("192.0.2.10"))
"""

    first = subprocess.run(
        [sys.executable, "-c", script],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    second = subprocess.run(
        [sys.executable, "-c", script],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    assert first == second


def test_ip_hash_changes_when_secret_changes(monkeypatch):
    monkeypatch.setattr(
        ip_hash_module.settings, "SECRET_KEY", "test-secret-one"
    )
    first = hash_ip("192.0.2.10")

    monkeypatch.setattr(
        ip_hash_module.settings, "SECRET_KEY", "test-secret-two"
    )
    second = hash_ip("192.0.2.10")

    assert first != second


def test_ip_hash_is_64_lowercase_hex_characters(monkeypatch):
    monkeypatch.setattr(
        ip_hash_module.settings, "SECRET_KEY", "test-secret-one"
    )
    digest = hash_ip("192.0.2.10")

    assert re.fullmatch(r"[0-9a-f]{64}", digest)


def test_ip_hash_does_not_match_precomputed_plain_sha256_table(monkeypatch):
    monkeypatch.setattr(
        ip_hash_module.settings, "SECRET_KEY", "test-secret-one"
    )

    # Fixed, precomputed unsalted SHA-256 digests for known IP addresses.
    plain_sha256_table = {
        "192.0.2.10": "6d99cbd08fc6c99cdb2d942a4cbb097c6b54496bbbc3ffd6351b145508dd2935",
        "192.0.2.11": "997c7ba95aa3f7c552c8ce042ea48b12fd2617f818f75492ab81747706f2c3bb",
        "198.51.100.7": "e183220b699c10a83ca7be3433d228ed0860a5ecf9480f83e9655f16bad58908",
        "203.0.113.42": "17af1cf3d1b5332c53349fc789abdc853bbeea7ed33eff727ff794ab741ccac9",
    }

    for ip, plain_digest in plain_sha256_table.items():
        assert hash_ip(ip) != plain_digest


def test_ip_hash_changes_when_ip_changes(monkeypatch):
    monkeypatch.setattr(
        ip_hash_module.settings, "SECRET_KEY", "test-secret-one"
    )

    assert hash_ip("192.0.2.10") != hash_ip("192.0.2.11")
