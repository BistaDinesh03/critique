import time
import pytest
from app.config import settings
from app.email import send_login_link


class HangingEmailClient:
    @staticmethod
    def send(payload):
        # Simulate a provider hang
        time.sleep(2.0)
        return {"id": "123"}


def test_send_login_link_times_out_when_provider_hangs(monkeypatch):
    """Verify that send_login_link returns False within timeout deadline when provider hangs."""
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_test_key")
    monkeypatch.setattr(settings, "EMAIL_FROM", "login@critique.page")
    monkeypatch.setattr("app.email._build_client", lambda: HangingEmailClient)

    start = time.time()
    # Call with 0.1s timeout
    result = send_login_link("user@example.com", "raw-token-abc", timeout=0.1)
    duration = time.time() - start

    assert result is False
    assert duration < 1.0, f"Call hung for {duration} seconds"


def test_send_login_link_succeeds_when_responsive(monkeypatch):
    """Verify that send_login_link returns True when provider answers promptly."""
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_test_key")
    monkeypatch.setattr(settings, "EMAIL_FROM", "login@critique.page")

    class FastEmailClient:
        @staticmethod
        def send(payload):
            return {"id": "fast-123"}

    monkeypatch.setattr("app.email._build_client", lambda: FastEmailClient)

    assert send_login_link("user@example.com", "raw-token-abc", timeout=2.0) is True
