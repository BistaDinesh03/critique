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
        '<!DOCTYPE html>'
        '<html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Your Critique sign-in link</title>'
        '</head>'
        '<body style="margin:0;padding:0;background:#f5f5f7;">'
        # Preheader
        '<div style="display:none;max-height:0;overflow:hidden;color:#f5f5f7;">'
        'Your secure sign-in link for Critique. Expires in 15 minutes.'
        '</div>'
        # Outer wrapper
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
        'style="background:#f5f5f7;padding:32px 16px;">'
        '<tr><td align="center">'
        # Card
        '<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" '
        'style="max-width:600px;width:100%;background:#ffffff;'
        'border:1px solid #e5e7eb;border-radius:12px;">'
        '<tr><td style="padding:32px 32px 8px 32px;">'
        '<img src="https://critique.page/static/logo.svg" alt="Critique" width="32" height="32" '
        'style="display:block;border:0;outline:none;text-decoration:none;">'
        '</td></tr>'
        '<tr><td style="padding:8px 32px 0 32px;'
        'font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
        'font-size:16px;line-height:24px;color:#111111;">'
        '<h1 style="margin:0 0 16px 0;font-size:22px;line-height:28px;font-weight:600;color:#111111;">'
        'Your Critique sign-in link'
        '</h1>'
        '<p style="margin:0 0 24px 0;color:#374151;">'
        'You requested a sign-in link for Critique. Click the button below to continue.'
        '</p>'
        # CTA button
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0">'
        '<tr><td bgcolor="#2563eb" style="border-radius:6px;background:#2563eb;">'
        '<a href="' + login_url + '" '
        'style="display:inline-block;padding:12px 20px;'
        'font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
        'font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;'
        'border-radius:6px;background:#2563eb;">'
        'Continue to Critique'
        '</a>'
        '</td></tr></table>'
        '<p style="margin:24px 0 8px 0;color:#6b7280;font-size:14px;line-height:20px;">'
        'This link expires in 15 minutes and can only be used once.'
        '</p>'
        '<p style="margin:0 0 8px 0;color:#6b7280;font-size:14px;line-height:20px;">'
        'If the button doesn\'t work, copy and paste this URL into your browser:'
        '</p>'
        '<p style="margin:0 0 24px 0;word-break:break-all;'
        'font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;'
        'font-size:13px;line-height:20px;color:#2563eb;">'
        '<a href="' + login_url + '" style="color:#2563eb;text-decoration:underline;">'
        + login_url +
        '</a>'
        '</p>'
        '</td></tr>'
        # Divider + footer
        '<tr><td style="padding:0 32px;"><div style="height:1px;background:#e5e7eb;"></div></td></tr>'
        '<tr><td style="padding:16px 32px 28px 32px;'
        'font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
        'font-size:13px;line-height:20px;color:#9ca3af;">'
        'If you did not request this email, you can safely ignore it. '
        'No action is required.'
        '<br><br>'
        'Critique &middot; <a href="https://critique.page" style="color:#9ca3af;text-decoration:underline;">critique.page</a>'
        '</td></tr>'
        '</table>'
        # Bottom spacer
        '</td></tr></table>'
        '</body></html>'
    )


def _render_email_text(login_url: str) -> str:
    """Plain-text fallback. No user-controlled content interpolated."""
    return (
        "Your Critique sign-in link\n"
        "==========================\n\n"
        "You requested a sign-in link for Critique. Open the link below to continue:\n\n"
        f"{login_url}\n\n"
        "This link expires in 15 minutes and can only be used once.\n\n"
        "If you did not request this email, you can safely ignore it.\n"
        "No action is required.\n\n"
        "---\n"
        "Critique · https://critique.page\n"
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
            "reply_to": settings.EMAIL_FROM,
            "html": _render_email_html(login_url),
            "text": _render_email_text(login_url),
        })
        return True
    except Exception:
        # Log the failure without including the token or recipient.
        logger.exception("send_login_link: provider call failed")
        return False