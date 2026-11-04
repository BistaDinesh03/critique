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
- IP addresses used for duplicate detection and email-login auditing are
  stored as HMAC-SHA-256 digests using a dedicated key derived from
  `SECRET_KEY` with the `critique:ip-hash:key:v1` context. The IP digest
  uses the separate `critique:ip-hash:value:v1` context. Raw IPs are not
  persisted by these hashing paths. Hashes remain stable while `SECRET_KEY`
  is unchanged; rotating the key changes new digests and does not backfill
  existing records. Configure a persistent `SECRET_KEY` to preserve
  hash stability across application restarts.
- No third-party tracking scripts

## For Contributors

- Never commit secrets, tokens, credentials, or `.env` files
- Use environment variables for all sensitive values
- Test changes for common vulnerabilities (XSS, CSRF, injection, IDOR)
- Do not weaken existing security checks to make a feature easier to build
