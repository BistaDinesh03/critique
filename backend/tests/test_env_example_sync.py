"""Ensure .env.example remains in sync with Settings declared in config.py."""

import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PY = ROOT_DIR / "backend" / "app" / "config.py"
ENV_EXAMPLE = ROOT_DIR / ".env.example"


def _extract_config_env_vars() -> set[str]:
    content = CONFIG_PY.read_text(encoding="utf-8")
    # Matches os.getenv("NAME", ...) or os.getenv('NAME', ...)
    pattern = re.compile(r'os\.getenv\(["\']([A-Z0-9_]+)["\']')
    return set(pattern.findall(content))


def _extract_env_example_keys() -> set[str]:
    content = ENV_EXAMPLE.read_text(encoding="utf-8")
    keys = set()
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        # Strip optional comment prefix "# "
        if line.startswith("#"):
            line = line.lstrip("#").strip()
        if "=" in line:
            key = line.split("=", 1)[0].strip()
            if re.match(r"^[A-Z0-9_]+$", key):
                keys.add(key)
    return keys


def test_env_example_contains_all_config_settings():
    config_vars = _extract_config_env_vars()
    example_keys = _extract_env_example_keys()

    # Allowed intentional omissions (none currently)
    allowlist = set()

    missing = (config_vars - allowlist) - example_keys
    assert not missing, f"Variables in config.py missing from .env.example: {sorted(missing)}"


def test_no_real_secrets_in_env_example():
    content = ENV_EXAMPLE.read_text(encoding="utf-8")
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("#") or not line or "=" not in line:
            continue
        key, val = line.split("=", 1)
        val = val.strip().strip("'\"")
        if "KEY" in key or "SECRET" in key:
            assert "your_" in val or val == "" or "here" in val, f"Suspected real secret in .env.example: {line}"
