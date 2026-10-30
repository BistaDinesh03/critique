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

import html
import logging
from urllib.parse import urlparse

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


def _app_base_url() -> str:
    """Normalized APP_URL with trailing slash stripped.

    Empty string if APP_URL is unset. Operator configuration is trusted;
    callers that interpolate it into HTML must escape.
    """
    return (settings.APP_URL or "").rstrip("/")


def _app_display_host() -> str:
    """Host portion of APP_URL for human-readable display (e.g. footer text).

    Falls back to the full base if no netloc can be parsed.
    """
    base = _app_base_url()
    if not base:
        return "Critique"
    parsed = urlparse(base)
    return parsed.netloc or base


def _build_login_url(raw_token: str) -> str:
    """Construct the magic-link URL from the configured APP_URL."""
    base = _app_base_url()
    return f"{base}/auth/email/verify?token={raw_token}"


# ===== blue header band + text wordmark email template =====
def _render_email_html(login_url: str) -> str:
    """Render the email body. No user-controlled content interpolated.

    Absolute URLs (logo, footer) are derived from settings.APP_URL.
    APP_URL is operator configuration and is therefore trusted, but we
    still HTML-escape it on interpolation to be defensive.
    """
    base = _app_base_url()
    logo_src = f"{base}/static/logo.png" if base else "/static/logo.png"
    footer_href = html.escape(base or "#", quote=True)
    footer_text = html.escape(_app_display_host())
    return (
        '<!DOCTYPE html>'
        '<html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="color-scheme" content="light only">'
        '<title>Your Critique sign-in link</title>'
        '</head>'
        '<body style="margin:0;padding:0;background:#f5f5f7;">'

        # Hidden preheader
        '<div style="display:none;max-height:0;overflow:hidden;'
        'font-size:1px;color:#f5f5f7;line-height:1px;">'
        'Your secure sign-in link for Critique. Expires in 15 minutes.'
        '</div>'

        # Outer wrapper
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
        'style="background:#f5f5f7;padding:32px 16px;">'
        '<tr><td align="center">'

        # Card
        '<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" '
        'style="max-width:600px;width:100%;background:#ffffff;'
        'border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;">'

        # Blue header band with wordmark
        '<tr><td bgcolor="#2563eb" '
        'style="background:#2563eb;padding:20px 32px;">'
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0">'
        '<tr>'
        '<td style="vertical-align:middle;padding-right:12px;">'
        '<img src="' + html.escape(logo_src, quote=True) + '" alt="Critique" '
        'width="28" height="28" '
        'style="display:block;border:0;outline:none;text-decoration:none;">'
        '</td>'
        '<td style="vertical-align:middle;">'
        '<div style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,'
        'Helvetica,Arial,sans-serif;font-size:18px;line-height:1.3;'
        'font-weight:700;color:#ffffff;letter-spacing:-0.01em;">'
        'Critique'
        '</div>'
        '</td>'
        '</tr>'
        '</table>'
        '</td></tr>'

        # Body
        '<tr><td style="padding:32px 32px 8px 32px;'
        'font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
        'font-size:16px;line-height:24px;color:#111111;">'

        '<h1 style="margin:0 0 12px 0;font-size:24px;line-height:32px;'
        'font-weight:700;color:#111111;letter-spacing:-0.01em;">'
        'Your Critique sign-in link'
        '</h1>'

        '<p style="margin:0 0 28px 0;color:#374151;font-size:16px;line-height:24px;">'
        'You requested a sign-in link for Critique. Click the button below to continue.'
        '</p>'

        # Full-width CTA button
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">'
        '<tr><td bgcolor="#2563eb" align="center" '
        'style="background:#2563eb;border-radius:8px;">'
        '<a href="' + login_url + '" '
        'style="display:block;padding:14px 24px;'
        'font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
        'font-size:16px;font-weight:600;color:#ffffff;text-decoration:none;'
        'border-radius:8px;background:#2563eb;">'
        'Continue to Critique'
        '</a>'
        '</td></tr></table>'

        '<p style="margin:28px 0 8px 0;color:#6b7280;font-size:14px;line-height:20px;">'
        'This link expires in 15 minutes and can only be used once.'
        '</p>'

        '<p style="margin:0 0 8px 0;color:#6b7280;font-size:14px;line-height:20px;">'
        'If the button doesn\'t work, copy and paste this URL into your browser:'
        '</p>'

        '<p style="margin:0 0 32px 0;word-break:break-all;'
        'font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;'
        'font-size:13px;line-height:20px;">'
        '<a href="' + login_url + '" '
        'style="color:#2563eb;text-decoration:underline;">' + login_url + '</a>'
        '</p>'

        '</td></tr>'

        # Divider
        '<tr><td style="padding:0 32px;">'
        '<div style="height:1px;background:#e5e7eb;line-height:1px;font-size:1px;">&nbsp;</div>'
        '</td></tr>'

        # Footer
        '<tr><td style="padding:20px 32px 28px 32px;'
        'font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
        'font-size:13px;line-height:20px;color:#9ca3af;">'
        'You received this email because someone requested a sign-in link for this address. '
        'If it wasn\'t you, you can safely ignore this message.'
        '<br><br>'
        'Critique &middot; '
        '<a href="' + footer_href + '" style="color:#9ca3af;text-decoration:underline;">'
        + footer_text +
        '</a>'
        '</td></tr>'

        '</table>'
        '</td></tr></table>'
        '</body></html>'
    )


def _render_email_text(login_url: str) -> str:
    """Plain-text fallback. No user-controlled content interpolated.

    The footer URL is derived from settings.APP_URL.
    """
    base = _app_base_url()
    footer = base or "Critique"
    return (
        "Critique\n"
        "========\n\n"
        "Your Critique sign-in link\n\n"
        "You requested a sign-in link for Critique. Open the link below to continue:\n\n"
        f"{login_url}\n\n"
        "This link expires in 15 minutes and can only be used once.\n\n"
        "You received this email because someone requested a sign-in link for this\n"
        "address. If it wasn't you, you can safely ignore this message.\n\n"
        "---\n"
        f"Critique \u00b7 {footer}\n"
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
