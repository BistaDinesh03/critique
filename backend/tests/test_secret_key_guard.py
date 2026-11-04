"""Regression tests for the SECRET_KEY guard (issue #93).

Two policies are enforced:

- In production, an empty SECRET_KEY refuses to start the app.
- Everywhere else, an empty SECRET_KEY falls back to a random per-process
  key, so the app never signs session or OAuth-state tokens with '' and a
  token forged with the empty-key serializer is rejected.
"""

import subprocess
import sys
from pathlib import Path

from itsdangerous import URLSafeTimedSerializer

import app.auth as auth_module
from app.config import settings

_BACKEND_DIR = Path(__file__).resolve().parent.parent


def test_settings_never_uses_an_empty_secret_key():
    """Whatever the environment, the configured signing key is non-empty."""
    assert settings.SECRET_KEY != ""


def test_empty_key_forged_session_token_is_rejected():
    """A token signed with the empty-key serializer must not verify."""
    forged = URLSafeTimedSerializer("", salt="session").dumps({"user_id": 1})
    try:
        auth_module.serializer.loads(forged, max_age=settings.SESSION_COOKIE_MAX_AGE)
    except Exception:
        return  # any itsdangerous rejection (BadSignature/SignatureExpired) is a pass
    raise AssertionError("empty-key forged session token was accepted")


def test_empty_key_forged_oauth_state_is_rejected():
    """An OAuth state signed with the empty-key serializer must not verify."""
    forged = URLSafeTimedSerializer("", salt="oauth_state").dumps(
        {"github_state": "atk", "return_to": "/"}
    )
    try:
        auth_module.oauth_state_serializer.loads(forged, max_age=600)
    except Exception:
        return
    raise AssertionError("empty-key forged OAuth state was accepted")


def test_production_with_empty_secret_key_refuses_to_start():
    """APP_ENV=production without SECRET_KEY must fail with a clear message.

    Runs in a subprocess so it cannot mutate the imported settings object.
    """
    import os

    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("APP_ENV", "PYTHONPATH")
    }
    # Explicitly empty, not merely absent: a repo-local .env file must not be
    # able to rescue the process via load_dotenv() either.
    env["SECRET_KEY"] = ""
    env["APP_ENV"] = "production"
    env.setdefault("PATH", os.environ.get("PATH", "/usr/bin:/bin"))
    result = subprocess.run(
        [sys.executable, "-c", "import app.config"],
        cwd=_BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode != 0
    assert "SECRET_KEY" in result.stderr
    # The error must not leak key material — there is none to leak, but the
    # assertion documents the contract: no value, empty or otherwise.
    assert "your_secret_key" not in result.stderr
