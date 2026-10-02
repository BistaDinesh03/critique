# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not** open a public
issue.

Report it privately through GitHub's vulnerability reporting:

https://github.com/BistaDinesh03/critique/security/advisories/new

If that page is not available to you, contact the maintainer privately
through GitHub instead. Please include:

- The affected endpoint or page
- Steps to reproduce
- The potential impact

Valid reports are acknowledged and, with your permission, credited
publicly.

## Supported Versions

The deployed site at https://critique.page and the latest commit on `main`
are supported. There are no versioned releases.

## Security-Relevant Behavior

These controls exist in the codebase today — useful context when reporting
or reviewing:

- CSRF protection (double-submit cookie) on all state-changing requests
- Session cookies are `HttpOnly`, `SameSite=Lax`, and `Secure` in production
- Server-side ownership checks on every mutation, based on the session —
  never on client-supplied headers
- Rate limiting on authentication, email login, project creation, deletion,
  feedback submission, and analytics
- Pydantic input validation (length limits, URL scheme checks, enums)
- HTML escaping of user content in the frontend
- Analytics events validated against a strict server-side allowlist
- IP addresses are stored only as SHA-256 hashes for duplicate detection;
  raw IPs are never persisted
- No third-party tracking scripts

## For Contributors

- Never commit secrets, tokens, credentials, or `.env` files
- Use environment variables for all sensitive values
- Test changes for common vulnerabilities (XSS, CSRF, injection, IDOR)
- Do not weaken existing security checks to make a feature easier to build
