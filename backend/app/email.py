"""Email delivery for Critique via Resend.

One function: send_login_link. Called only by the email-auth routes.

Design notes:
- Never logs the token, the API key, or the recipient address.
- Returns True on success, False on any failure.
- Builds the magic link from settings.APP_URL, never from a hardcoded URL.
- The Resend client is created per call via _build_client() so tests can
  monkeypatch the seam without touching the network.
"""
from __future__ import annotations

import logging

from app.config import settings

logger = logging.getLogger(__name__)


def _build_client():
    """Return a configured Resend client.

    Kept as a separate function so tests can monkeypatch it to inject a
    fake client without importing the resend package or making any
    network call.
    """
    import resend
    resend.api_key = settings.RESEND_API_KEY
    return resend.Emails


def _build_login_url(raw_token: str) -> str:
    """Construct the magic-link URL from the configured APP_URL."""
    base = (settings.APP_URL or "").rstrip("/")
    return f"{base}/auth/email/verify?token={raw_token}"


def _render_email_html(login_url: str) -> str:
    """Render the email body. No user-controlled content interpolated."""
    return (
        '<div style="font-family: -apple-system, Segoe UI, Roboto, sans-serif; '
        'font-size: 16px; line-height: 1.5; color: #111;">'
        "<p>You requested a sign-in link for Critique.</p>"
        f'<p><a href="{login_url}" '
        'style="display:inline-block;padding:10px 16px;background:#2563eb;'
        'color:#fff;text-decoration:none;border-radius:6px;">'
        "Continue to Critique</a></p>"
        "<p>This link expires soon and can only be used once.</p>"
        "<p>If you did not request this, you can ignore this email.</p>"
        "</div>"
    )


def _render_email_text(login_url: str) -> str:
    """Plain-text fallback. No user-controlled content interpolated."""
    return (
        "You requested a sign-in link for Critique.\n\n"
        f"Continue to Critique: {login_url}\n\n"
        "This link expires soon and can only be used once.\n"
        "If you did not request this, you can ignore this email.\n"
    )


def send_login_link(to_email: str, raw_token: str) -> bool:
    """Send the magic-link email.

    Returns True if the provider accepted the send, False otherwise.
    Never raises. Never logs the token or the recipient address.
    """
    if not settings.RESEND_API_KEY:
        logger.error("send_login_link: RESEND_API_KEY is not configured")
        return False
    if not settings.EMAIL_FROM:
        logger.error("send_login_link: EMAIL_FROM is not configured")
        return False

    login_url = _build_login_url(raw_token)

    try:
        client = _build_client()
        client.send({
            "from": settings.EMAIL_FROM,
            "to": [to_email],
            "subject": "Your Critique sign-in link",
            "html": _render_email_html(login_url),
            "text": _render_email_text(login_url),
        })
        return True
    except Exception:
        # Log the failure without including the token or recipient.
        logger.exception("send_login_link: provider call failed")
        return False