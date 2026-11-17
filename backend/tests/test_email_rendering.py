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


def test_build_login_url_handles_trailing_slash_variants(monkeypatch):
    """_build_login_url strips trailing slashes so no double slash appears in the path."""
    token = "secret_verification_token_456"

    # With trailing slash
    monkeypatch.setattr(settings, "APP_URL", "https://app.example.com/")
    url_with_slash = _build_login_url(token)
    assert url_with_slash == f"https://app.example.com/auth/email/verify?token={token}"
    assert "//auth" not in url_with_slash

    # Without trailing slash
    monkeypatch.setattr(settings, "APP_URL", "https://app.example.com")
    url_without_slash = _build_login_url(token)
    assert url_without_slash == f"https://app.example.com/auth/email/verify?token={token}"

    # Token appears exactly once in the URL
    assert url_with_slash.count(token) == 1
    assert url_with_slash.count("token=") == 1


def test_build_login_url_with_empty_app_url(monkeypatch):
    """When APP_URL is empty, _build_login_url still produces a valid relative path."""
    monkeypatch.setattr(settings, "APP_URL", "")
    url = _build_login_url("token_empty_app_url")
    assert url == "/auth/email/verify?token=token_empty_app_url"


def test_render_email_html_cta_fallback_and_expiry_promises():
    """_render_email_html includes the login URL in CTA and fallback, and promises 15-minute expiry."""
    test_url = "https://app.example.com/auth/email/verify?token=custom-test-token"
    html_output = _render_email_html(test_url)

    # CTA button link
    assert f'href="{test_url}"' in html_output
    assert "Continue to Critique" in html_output

    # Fallback text link shows the URL both in href and text
    assert f'<a href="{test_url}"' in html_output
    assert f'>{test_url}</a>' in html_output

    # Expiry promises to user
    assert "15 minutes" in html_output
    assert "can only be used once" in html_output


def test_render_email_text_contains_url_and_expiry_promises():
    """_render_email_text plain text fallback includes the URL and expiry promise."""
    test_url = "https://app.example.com/auth/email/verify?token=plain-text-token"
    text_output = _render_email_text(test_url)

    # URL is present in the plain text
    assert test_url in text_output

    # Expiry and single-use promises to user
    assert "expires in 15 minutes" in text_output
    assert "can only be used once" in text_output

