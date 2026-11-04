"""Focused tests for magic-link email rendering helpers.

Verifies that absolute URLs in the email (logo, footer) are derived from
settings.APP_URL rather than hardcoded production origins.
"""
from app.config import settings
from app.email import _render_email_html, _render_email_text, _build_login_url


def test_email_rendering_uses_configured_app_url(monkeypatch):
    """All absolute URLs in HTML and text come from APP_URL; production origin is absent."""
    custom_origin = "https://selfhosted.example.com"
    monkeypatch.setattr(settings, "APP_URL", custom_origin)

    login_url = _build_login_url("raw-token-xyz")
    html = _render_email_html(login_url)
    text = _render_email_text(login_url)

    # Configured origin appears
    assert custom_origin in html
    assert custom_origin in text
    assert custom_origin in login_url

    # Hardcoded production origin does not
    assert "https://critique.page" not in html
    assert "https://critique.page" not in text
    assert "critique.page" not in html
    assert "critique.page" not in text

    # Logo points at the configured origin
    assert f"{custom_origin}/static/logo.png" in html

    # Footer link uses the configured origin
    assert f'href="{custom_origin}"' in html

    # Display host is the netloc
    assert "selfhosted.example.com" in html


def test_email_rendering_with_default_app_url():
    """Default local APP_URL still produces valid rendering and a well-formed login URL."""
    # Default is http://127.0.0.1:8000 (see config.py)
    login_url = _build_login_url("tok")
    html = _render_email_html(login_url)
    text = _render_email_text(login_url)

    assert login_url.startswith("http://127.0.0.1:8000/auth/email/verify?token=tok")
    assert "http://127.0.0.1:8000" in html
    assert "http://127.0.0.1:8000" in text
    assert "https://critique.page" not in html
    assert "https://critique.page" not in text
    # Rendering does not raise and produces non-empty content
    assert "<html" in html
    assert "Your Critique sign-in link" in text
