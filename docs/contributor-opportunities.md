# Contributor Opportunities

This is the list of work that is **open, unassigned, not claimed in a comment, and
not attached to an open pull request**. If an issue is on this page, nobody is on
it — comment on the issue and it is yours.

**Last verified against the live tracker:** 2026-11-13.

At a glance: **166 open issues**, of which **70 are claimable here** (19 in
*Start here*, 51 in *Other open work*), **34 are in progress** (6 assigned, 3
claimed in comments, 27 linked to an open pull request — 2 are both), and the
other **62 are deliberately not listed** — see
[How this list is kept accurate](#how-this-list-is-kept-accurate).

- For general contribution guidelines, see [CONTRIBUTING.md](../CONTRIBUTING.md).
- For a step-by-step first contribution, see [first-contribution.md](first-contribution.md).
- For the historical roadmap that produced many of these issues, see
  [issue-roadmap.md](issue-roadmap.md). It is a dated record, not a task list.

## Start here

These have a bounded scope, a clear definition of done, and touch one or two files.
You should be able to read the issue and start without asking anything.

### Beginner

| Issue | What you'll build | Skills |
|-------|-------------------|--------|
| [#77](https://github.com/BistaDinesh03/critique/issues/77) | Add a `<noscript>` notice to the five pages that render their content with `fetch()` | HTML |
| [#21](https://github.com/BistaDinesh03/critique/issues/21) | Add `pytest-cov`, document the command, and surface coverage in CI | pytest, YAML |
| [#143](https://github.com/BistaDinesh03/critique/issues/143) | Add a weekly `schedule:` to the test workflow to catch dependency drift | YAML |

### Intermediate

| Issue | What you'll build | Skills |
|-------|-------------------|--------|
| [#71](https://github.com/BistaDinesh03/critique/issues/71) | Make the denormalized feedback counters consistent — they currently inflate ranking forever | Python, SQLAlchemy |
| [#82](https://github.com/BistaDinesh03/critique/issues/82) | Bring the SQLite startup migration in line with PostgreSQL instead of swallowing failures | Python, SQL |
| [#83](https://github.com/BistaDinesh03/critique/issues/83) | Use one shared client-IP helper so `Response.ip_hash` cannot disagree with rate limiting | Python |
| [#84](https://github.com/BistaDinesh03/critique/issues/84) | Purge expired `email_login_tokens` rows | Python, SQLAlchemy |
| [#140](https://github.com/BistaDinesh03/critique/issues/140) | Add indexes on the hot foreign keys (`projects.owner_id`, `questions.project_id`, `responses.*`) | SQL |
| [#151](https://github.com/BistaDinesh03/critique/issues/151) | Add a least-privilege `permissions:` block to `tests.yml` | YAML, security |
| [#178](https://github.com/BistaDinesh03/critique/issues/178) | Pin the three Actions to full commit SHAs and stop persisting the token into `.git` | YAML, security |
| [#220](https://github.com/BistaDinesh03/critique/issues/220) | Stop one person from creating two user rows by signing in with GitHub *and* a magic link | Python, data model |
| [#277](https://github.com/BistaDinesh03/critique/issues/277) | Add keyword search to Discover, with the query reflected in the URL and a real no-results state | Python, FastAPI, JS |

### Advanced

| Issue | What you'll build | Skills |
|-------|-------------------|--------|
| [#94](https://github.com/BistaDinesh03/critique/issues/94) | Server-side session invalidation, so logout ends the session beyond the current browser | Python, auth |
| [#141](https://github.com/BistaDinesh03/critique/issues/141) | Turn `GET /auth/logout` into a CSRF-protected POST and update every page | Python, frontend |
| [#158](https://github.com/BistaDinesh03/critique/issues/158) | Fix rate-limit keying: unconditional `CF-Connecting-IP` trust and the shared-bucket fallback | Python, HTTP |
| [#162](https://github.com/BistaDinesh03/critique/issues/162) | Stop link prefetchers from consuming the single-use email verification token | Python, auth |
| [#179](https://github.com/BistaDinesh03/critique/issues/179) | Add an account deletion path that erases the user row, projects, tokens, and authored feedback | Python, data model, frontend |
| [#249](https://github.com/BistaDinesh03/critique/issues/249) | Bound magic-link email volume, which is currently limited only by a per-address cooldown | Python, security |
| [#272](https://github.com/BistaDinesh03/critique/issues/272) | Stop acknowledging analytics events with HTTP 200 when the database write failed | Python |

## Work in progress — please don't duplicate

These are being worked on right now. If one of them is the thing you want to do,
comment and ask — the person may be stuck and glad of help.

### Assigned

| Issue | Who | Status |
|-------|-----|--------|
| [#31](https://github.com/BistaDinesh03/critique/issues/31) | @Kailashnegi07 | PR [#753](https://github.com/BistaDinesh03/critique/pull/753) in review |
| [#36](https://github.com/BistaDinesh03/critique/issues/36) | @dheeraj1174 | Assigned |
| [#163](https://github.com/BistaDinesh03/critique/issues/163) | @n-o-t-mugen | Assigned |
| [#362](https://github.com/BistaDinesh03/critique/issues/362) | @IG-ABHINAV | Assigned — meta tags for the remaining pages |
| [#722](https://github.com/BistaDinesh03/critique/issues/722) | @Jogall5 | Assigned |
| [#723](https://github.com/BistaDinesh03/critique/issues/723) | @d1vyPandey | Assigned |

### Claimed in comments, no pull request yet

These were claimed in a comment but are still unassigned and have no pull request.
Treat them as taken — ask on the issue before starting.

| Issue | Claimed by | Since |
|-------|-----------|-------|
| [#20](https://github.com/BistaDinesh03/critique/issues/20) | @Aaqibhafeezkhan | 2026-10-28 |
| [#25](https://github.com/BistaDinesh03/critique/issues/25) | @Aaqibhafeezkhan | 2026-10-28 |
| [#34](https://github.com/BistaDinesh03/critique/issues/34) | @Aaqibhafeezkhan | 2026-10-28 |

### Has an open pull request

[#137](https://github.com/BistaDinesh03/critique/issues/137) ·
[#180](https://github.com/BistaDinesh03/critique/issues/180) ·
[#225](https://github.com/BistaDinesh03/critique/issues/225) ·
[#273](https://github.com/BistaDinesh03/critique/issues/273) ·
[#279](https://github.com/BistaDinesh03/critique/issues/279) ·
[#280](https://github.com/BistaDinesh03/critique/issues/280) ·
[#288](https://github.com/BistaDinesh03/critique/issues/288) ·
[#295](https://github.com/BistaDinesh03/critique/issues/295) ·
[#296](https://github.com/BistaDinesh03/critique/issues/296) ·
[#298](https://github.com/BistaDinesh03/critique/issues/298) ·
[#312](https://github.com/BistaDinesh03/critique/issues/312) ·
[#327](https://github.com/BistaDinesh03/critique/issues/327) ·
[#329](https://github.com/BistaDinesh03/critique/issues/329) ·
[#331](https://github.com/BistaDinesh03/critique/issues/331) ·
[#333](https://github.com/BistaDinesh03/critique/issues/333) ·
[#349](https://github.com/BistaDinesh03/critique/issues/349) ·
[#350](https://github.com/BistaDinesh03/critique/issues/350) ·
[#353](https://github.com/BistaDinesh03/critique/issues/353) ·
[#357](https://github.com/BistaDinesh03/critique/issues/357) ·
[#358](https://github.com/BistaDinesh03/critique/issues/358) ·
[#361](https://github.com/BistaDinesh03/critique/issues/361) ·
[#364](https://github.com/BistaDinesh03/critique/issues/364) ·
[#370](https://github.com/BistaDinesh03/critique/issues/370) ·
[#371](https://github.com/BistaDinesh03/critique/issues/371) ·
[#526](https://github.com/BistaDinesh03/critique/issues/526)

Most of these PRs conflict with `main` and need a rebase before they can land. If you
want to help, a rebase plus a green test run is a genuinely useful contribution.

## Other open work

Real, scoped issues that are not first-contributor material — they need more context,
touch more of the codebase, or need a design decision first. Nothing here is claimed.

### Frontend

- [#79](https://github.com/BistaDinesh03/critique/issues/79) — Add owner-only project editing (API endpoint and edit UI)
- [#81](https://github.com/BistaDinesh03/critique/issues/81) — Report magic-link delivery failures without leaking account existence
- [#104](https://github.com/BistaDinesh03/critique/issues/104) — Remove duplicated sections and dead rules from `static/shared.css`
- [#105](https://github.com/BistaDinesh03/critique/issues/105) — Fix the orphaned native Share button left by the My Projects share row
- [#110](https://github.com/BistaDinesh03/critique/issues/110) — Define the UI internationalization architecture (none exists today)
- [#150](https://github.com/BistaDinesh03/critique/issues/150) — Serve a branded HTML 500 page for browser navigations
- [#200](https://github.com/BistaDinesh03/critique/issues/200) — Discover's pagination UI has no frontend-render coverage
- [#202](https://github.com/BistaDinesh03/critique/issues/202) — The render harness cannot dispatch keyboard events, so Escape-close paths are untestable
- [#224](https://github.com/BistaDinesh03/critique/issues/224) — The render harness discards fetch request headers, so the CSRF contract is untestable
- [#269](https://github.com/BistaDinesh03/critique/issues/269) — Successful sign-ins are only counted when a saved draft is restored
- [#274](https://github.com/BistaDinesh03/critique/issues/274) — Owners cannot replace the active question without deleting the project
- [#313](https://github.com/BistaDinesh03/critique/issues/313) — Navigation markup and `checkAuth()` are copy-pasted across every page
- [#330](https://github.com/BistaDinesh03/critique/issues/330) — Results page cannot filter responses by clarity rating
- [#337](https://github.com/BistaDinesh03/critique/issues/337) — Error messages are not associated with inputs via `aria-describedby`
- [#355](https://github.com/BistaDinesh03/critique/issues/355) — Add image optimization for the Open Graph image
- [#524](https://github.com/BistaDinesh03/critique/issues/524) — Add browser-level Playwright smoke tests for critical flows
- [#558](https://github.com/BistaDinesh03/critique/issues/558) — Add Playwright visual regression coverage for authentication states
- [#574](https://github.com/BistaDinesh03/critique/issues/574) — Add a "similar projects" section to project detail
- [#594](https://github.com/BistaDinesh03/critique/issues/594) — Add a feedback quality guide for reviewers
- [#596](https://github.com/BistaDinesh03/critique/issues/596) — Add a clarity distribution visualization to the results page
- [#717](https://github.com/BistaDinesh03/critique/issues/717) — Add project archival with soft delete

### Backend

- [#32](https://github.com/BistaDinesh03/critique/issues/32) — Make the analytics dashboard owner allowlist configurable
- [#33](https://github.com/BistaDinesh03/critique/issues/33) — Replace the analytics dashboard's sequential count queries
- [#35](https://github.com/BistaDinesh03/critique/issues/35) — Define a consistent JSON error contract for the API
- [#37](https://github.com/BistaDinesh03/critique/issues/37) — Set correct cache directives on authenticated JSON responses
- [#49](https://github.com/BistaDinesh03/critique/issues/49) — Document and harden the rate limiter's multi-instance and restart behaviour
- [#72](https://github.com/BistaDinesh03/critique/issues/72) — Run the test suite against PostgreSQL to cover dialect-specific code
- [#85](https://github.com/BistaDinesh03/critique/issues/85) — Enforce one response per user per question in the database
- [#86](https://github.com/BistaDinesh03/critique/issues/86) — Benchmark and bound the Discover ranking's full-table load
- [#87](https://github.com/BistaDinesh03/critique/issues/87) — Create project and question in one transaction
- [#88](https://github.com/BistaDinesh03/critique/issues/88) — Add request logging with request IDs that never logs secrets
- [#109](https://github.com/BistaDinesh03/critique/issues/109) — Enforce SQLite foreign keys and validate `project_id` in analytics tracking
- [#219](https://github.com/BistaDinesh03/critique/issues/219) — `ip_hash` columns are written on every row but read by nothing
- [#278](https://github.com/BistaDinesh03/critique/issues/278) — Project owners are never notified when they receive new feedback
- [#706](https://github.com/BistaDinesh03/critique/issues/706) — Add a "how to add a new API endpoint" guide
- [#709](https://github.com/BistaDinesh03/critique/issues/709) — Add a caching layer for public project listings
- [#711](https://github.com/BistaDinesh03/critique/issues/711) — Rate limit per user, not just per IP
- [#713](https://github.com/BistaDinesh03/critique/issues/713) — Add structured logging with correlation IDs
- [#715](https://github.com/BistaDinesh03/critique/issues/715) — Add a feedback export endpoint (JSON)
- [#719](https://github.com/BistaDinesh03/critique/issues/719) — Add a content moderation system for feedback

### Tests

- [#238](https://github.com/BistaDinesh03/critique/issues/238) — The render harness fabricates `getElementById` targets, so selector-driven DOM writes are untestable
- [#250](https://github.com/BistaDinesh03/critique/issues/250) — The suite shares one on-disk SQLite file across 13 divergent cleanup helpers
- [#38](https://github.com/BistaDinesh03/critique/issues/38) — Add Ruff configuration and document the lint command. Not a first task: default rules currently report 65 findings, so the config has to be scoped or the findings fixed

### Documentation

- [#55](https://github.com/BistaDinesh03/critique/issues/55) — Document the deployment and rollback process for maintainers
- [#203](https://github.com/BistaDinesh03/critique/issues/203) — Reconcile `render.yaml` (provisions a Render Postgres) with the README and the Neon `DATABASE_URL`
- [#697](https://github.com/BistaDinesh03/critique/issues/697) — Add a development setup verification script
- [#703](https://github.com/BistaDinesh03/critique/issues/703) — Add a "good first issue" labelling guide for maintainers
- [#18](https://github.com/BistaDinesh03/critique/issues/18) — Add a question issue template. Needs a decision first: the issue asks for a template that routes to issue #1, but `.github/ISSUE_TEMPLATE/config.yml` currently routes questions to Discussions

### Product

- [#3](https://github.com/BistaDinesh03/critique/issues/3) — Add GitHub repository integration to projects
- [#4](https://github.com/BistaDinesh03/critique/issues/4) — Add a "Feedback needed" status to projects
- [#5](https://github.com/BistaDinesh03/critique/issues/5) — Add project categories to Discover

## How to claim an issue

1. Comment on the issue and say you intend to work on it. That is the whole protocol.
2. Read [first-contribution.md](first-contribution.md).
3. Fork, branch, implement, and add a test.
4. Run the suite: `cd backend`, then
   `GITHUB_CLIENT_ID=ci-test-client-id python -m pytest tests/ -q`
   (PowerShell: `$env:GITHUB_CLIENT_ID = "ci-test-client-id"` first).
5. Open a pull request describing what changed, why, and the exact tests you ran.

If you are unsure whether an approach is right, ask on the issue before writing code.
A short question costs you a minute; a wrong-direction PR costs you a weekend.

## How this list is kept accurate

An issue appears here only if it is open, unassigned, **not claimed in a comment**,
and not linked to an open pull request at the time this page was last verified.
Issues are removed from this page when they are claimed, fixed, or blocked — not
when they become inconvenient.

The 62 open issues that are not listed here fall into five groups and are left out
on purpose:

- **52 future or speculative ideas** that have no current demand signal. They are
  open, but recommending them would waste a newcomer's time.
- **4 that need a scope rewrite** before anyone can act on them.
- **4 resolved or awaiting a merge**, including this page's own documentation change.
- **1 rejected duplicate.**
- **1 discussion thread** — [issue #1](https://github.com/BistaDinesh03/critique/issues/1),
  which is where questions go, not a task.

If you find a link here that is closed, assigned, claimed, or already has a PR,
that is a bug in this page. Say so in
[issue #1](https://github.com/BistaDinesh03/critique/issues/1) and it will be
corrected.
