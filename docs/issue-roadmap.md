# Critique issue roadmap

> ⚠️ **This document is a historical record, not a task list.**
>
> It was written on 2026-10-17 as a plan for 50 issues, and it is preserved as
> written. Many of the rows below have since shipped, been superseded, or been
> closed — the status column is **not** maintained.
>
> For work that is actually open, unassigned, and free of an open pull request,
> use **[contributor-opportunities.md](contributor-opportunities.md)**. That page
> is verified against the live tracker and is the only list you should act on.
>
> Live tracker: https://github.com/BistaDinesh03/critique/issues

A curated plan of **50 distinct issues**, originally prepared and validated against the live issue tracker and the current code on `BistaDinesh03/critique`.

**Prepared:** 2026-10-17 (row statuses re-verified 2026-11-04)  
**Repository:** https://github.com/BistaDinesh03/critique  
**Live issues:** https://github.com/BistaDinesh03/critique/issues


---

## Summary

| | |
|---|---|
| Total curated issues | 50 |
| Already open at roadmap creation | 8 |
| Issues published from roadmap | 42 |

### Category counts

| Category | Count |
|---|---|
| Beginner / good first issue | 12 |
| Frontend and user experience | 10 |
| Backend and API | 10 |
| Tests and developer experience | 7 |
| Security, performance and reliability | 6 |
| Community and product improvements | 5 |

### Difficulty counts

| Difficulty | Count |
|---|---|
| Beginner | 21 |
| Intermediate | 25 |
| Advanced | 4 |


## Existing issues accounted for

When this roadmap was prepared, the tracker had 10 open issues. They were handled as follows rather than being duplicated:

| Issue | Disposition |
|---|---|
| [#1](https://github.com/BistaDinesh03/critique/issues/1) | Question/discussion thread - kept as-is; new question issues are routed here by template A5. |
| [#2](https://github.com/BistaDinesh03/critique/issues/2) | Already implemented (static/share.js + test_project_share.py, test_share_analytics.py). Excluded from the roadmap; recommend closing - see roadmap issue F3. |

Reused directly as roadmap entries:

| Roadmap | Existing issue | Title |
|---|---|---|
| B2 | [#10](https://github.com/BistaDinesh03/critique/issues/10) | Improve project empty states |
| B3 | [#11](https://github.com/BistaDinesh03/critique/issues/11) | Improve feedback form UX |
| B4 | [#12](https://github.com/BistaDinesh03/critique/issues/12) | Add keyboard accessibility improvements |
| B5 | [#13](https://github.com/BistaDinesh03/critique/issues/13) | Improve project page navigation and information hierarchy |
| B6 | [#9](https://github.com/BistaDinesh03/critique/issues/9) | Extend loading states to the surfaces that do not have them yet |
| B7 | [#4](https://github.com/BistaDinesh03/critique/issues/4) | Show a "Feedback needed" status on projects |
| B8 | [#5](https://github.com/BistaDinesh03/critique/issues/5) | Add project categories to Discover |
| C1 | [#3](https://github.com/BistaDinesh03/critique/issues/3) | Add an optional GitHub repository link to projects |


## Ideas excluded as already implemented or out of scope

- **Share button (issue #2)** - already fully implemented in `static/share.js` (X, Reddit, copy link, copy post) with tests in `test_project_share.py` and `test_share_analytics.py`. Excluded; recommend closing.
- **Discover feed pagination** - already implemented (`page`, `page_size` bounded 1-50) and documented in `docs/api.md`. Replaced by the narrower issue C2, which targets the two endpoints that are still unbounded.
- **Homepage Open Graph metadata** - already complete in `index.html`. Replaced by B1, which targets the four pages that have none.
- **Image alt text** - every `<img>` in `frontend/` already carries `alt` (decorative images correctly use `alt=""`). Accessibility issues were retargeted at focus, landmarks and motion instead.
- **API reference documentation** - `docs/api.md` already covers every endpoint including `/health` and `/api/stats`. No filler documentation issue was created.
- **Content-Security-Policy bundled with security headers** - split into E1 and E2, because the frontend's inline scripts and `onerror` handlers make a bundled policy either useless or breaking.


---

## Index

| # | Title | Category | Difficulty | Status |
|---|---|---|---|---|
| A1 | Add a Code of Conduct and link it from the README and CONTRIBUTING | beginner | beginner | published [#14](https://github.com/BistaDinesh03/critique/issues/14) |
| A2 | Add a bug report issue template | beginner | beginner | published [#15](https://github.com/BistaDinesh03/critique/issues/15) |
| A3 | Add a feature request issue template | beginner | beginner | published [#16](https://github.com/BistaDinesh03/critique/issues/16) |
| A4 | Add a pull request template | beginner | beginner | published [#17](https://github.com/BistaDinesh03/critique/issues/17) |
| A5 | Add a question issue template that routes to issue #1 | beginner | beginner | published [#18](https://github.com/BistaDinesh03/critique/issues/18) |
| A6 | Add Dependabot configuration for pip and GitHub Actions | beginner | beginner | published [#19](https://github.com/BistaDinesh03/critique/issues/19) |
| A7 | Document the analytics event catalogue in docs/ | beginner | beginner | published [#20](https://github.com/BistaDinesh03/critique/issues/20) |
| A8 | Add coverage measurement with pytest-cov and document the command | beginner | beginner | published [#21](https://github.com/BistaDinesh03/critique/issues/21) |
| A9 | Explain how to run a single test in CONTRIBUTING.md | beginner | beginner | ✅ done — [#22](https://github.com/BistaDinesh03/critique/issues/22) |
| A10 | Reconcile the README analytics figures with the HTML analytics report | beginner | beginner | published [#23](https://github.com/BistaDinesh03/critique/issues/23) |
| A11 | Add an .editorconfig for consistent whitespace and line endings | beginner | beginner | ✅ done — [#24](https://github.com/BistaDinesh03/critique/issues/24) |
| A12 | Clarify the two requirements.txt files and how they relate | beginner | beginner | published [#25](https://github.com/BistaDinesh03/critique/issues/25) |
| B1 | Add Open Graph metadata to Discover and project pages | frontend | advanced | published [#26](https://github.com/BistaDinesh03/critique/issues/26) |
| B2 | Improve project empty states | frontend | beginner | existing #10 |
| B3 | Improve feedback form UX | frontend | beginner | existing #11 |
| B4 | Add keyboard accessibility improvements | frontend | intermediate | existing #12 |
| B5 | Improve project page navigation and information hierarchy | frontend | intermediate | existing #13 |
| B6 | Extend loading states to the surfaces that do not have them yet | frontend | intermediate | existing #9 |
| B7 | Show a "Feedback needed" status on projects | frontend | intermediate | existing #4 |
| B8 | Add project categories to Discover | frontend | intermediate | existing #5 |
| B9 | Add a skip-to-content link and semantic landmarks to every page | frontend | intermediate | published [#27](https://github.com/BistaDinesh03/critique/issues/27) |
| B10 | Honour prefers-reduced-motion in shared styles | frontend | intermediate | ✅ done — [#28](https://github.com/BistaDinesh03/critique/issues/28) |
| C1 | Add an optional GitHub repository link to projects | backend | intermediate | existing #3 |
| C2 | Bound the unbounded list endpoints with pagination | backend | intermediate | published [#29](https://github.com/BistaDinesh03/critique/issues/29) |
| C3 | Send a Retry-After header with 429 responses | backend | beginner | ✅ done — [#30](https://github.com/BistaDinesh03/critique/issues/30) |
| C4 | Make the analytics event allowlist a single source of truth | backend | intermediate | published [#31](https://github.com/BistaDinesh03/critique/issues/31) |
| C5 | Make the analytics dashboard owner allowlist configurable | backend | beginner | published [#32](https://github.com/BistaDinesh03/critique/issues/32) |
| C6 | Replace the analytics dashboard's sequential count queries | backend | intermediate | published [#33](https://github.com/BistaDinesh03/critique/issues/33) |
| C7 | Add conditional caching to the badge SVG endpoint | backend | intermediate | published [#34](https://github.com/BistaDinesh03/critique/issues/34) |
| C8 | Define a consistent JSON error contract for the API | backend | advanced | published [#35](https://github.com/BistaDinesh03/critique/issues/35) |
| C9 | Report database connectivity from the /health endpoint | backend | beginner | published [#36](https://github.com/BistaDinesh03/critique/issues/36) |
| C10 | Set correct cache directives on authenticated JSON responses | backend | intermediate | published [#37](https://github.com/BistaDinesh03/critique/issues/37) |
| D1 | Add Ruff configuration and document the lint command | tests | beginner | published [#38](https://github.com/BistaDinesh03/critique/issues/38) |
| D2 | Add a GitHub Actions workflow that runs the test suite | tests | intermediate | ✅ done — [#39](https://github.com/BistaDinesh03/critique/issues/39) |
| D3 | Run the frontend render tests in CI by installing Node | tests | intermediate | ✅ done — [#40](https://github.com/BistaDinesh03/critique/issues/40) |
| D4 | Add a regression test for the 429 Retry-After contract | tests | intermediate | published [#41](https://github.com/BistaDinesh03/critique/issues/41) |
| D5 | Add a test asserting security headers on HTML and API responses | tests | intermediate | published [#42](https://github.com/BistaDinesh03/critique/issues/42) |
| D6 | Add a test keeping the backend and frontend analytics allowlists in sync | tests | intermediate | ✅ done — [#43](https://github.com/BistaDinesh03/critique/issues/43) |
| D7 | Pin the analytics dashboard response shape with a contract test | tests | intermediate | published [#44](https://github.com/BistaDinesh03/critique/issues/44) |
| E1 | Add security response headers to HTML and API responses | security | intermediate | published [#45](https://github.com/BistaDinesh03/critique/issues/45) |
| E2 | Introduce a Content-Security-Policy without breaking the frontend | security | advanced | published [#46](https://github.com/BistaDinesh03/critique/issues/46) |
| E3 | Serve an HTML 404 page for unknown routes | security | beginner | ✅ done — [#47](https://github.com/BistaDinesh03/critique/issues/47) |
| E4 | Bound the in-memory rate limiter's growth | security | intermediate | ✅ done — [#48](https://github.com/BistaDinesh03/critique/issues/48) |
| E5 | Document and harden the rate limiter's multi-instance and restart behaviour | security | advanced | published [#49](https://github.com/BistaDinesh03/critique/issues/49) |
| E6 | Stop serving mutable JavaScript and CSS with a 24-hour cache | security | intermediate | ✅ done — [#50](https://github.com/BistaDinesh03/critique/issues/50) |
| F1 | Create and document a label taxonomy for the expanded issue tracker | community | beginner | published [#51](https://github.com/BistaDinesh03/critique/issues/51) |
| F2 | Write a first-contributor guide walking through one real issue | community | beginner | ✅ done — [#52](https://github.com/BistaDinesh03/critique/issues/52) |
| F3 | Define a triage policy and reconcile stale issues | community | intermediate | published [#53](https://github.com/BistaDinesh03/critique/issues/53) |
| F4 | Add a maintainer checklist for reviewing contributor pull requests | community | intermediate | ✅ done — [#54](https://github.com/BistaDinesh03/critique/issues/54) |
| F5 | Document the deployment and rollback process for maintainers | community | intermediate | published [#55](https://github.com/BistaDinesh03/critique/issues/55) |


---

## Full issue specifications


### Beginner / good first issue (12)


<a id="a1"></a>

#### A1 - Add a Code of Conduct and link it from the README and CONTRIBUTING

`**Published as [#14](https://github.com/BistaDinesh03/critique/issues/14)**` | difficulty: **beginner** | labels: `documentation`, `good first issue`

## The problem

Critique has a README, CONTRIBUTING.md and SECURITY.md, but no Code of Conduct. Right now the only behavioural guidance is a short "Communication" section inside CONTRIBUTING.md.

## Why it matters

A Code of Conduct is the standard first thing a new contributor looks for, and GitHub surfaces it in the community-health checklist. It tells people what is expected and gives a private route for reporting, which CONTRIBUTING.md alone does not provide.

## Scope and suggested direction

Add a `CODE_OF_CONDUCT.md` at the repository root. The Contributor Covenant v2.1 is the usual choice; if you use it, fill in the project contact method honestly rather than inventing an email address. Then link the file from the README (near the Contributing section) and from CONTRIBUTING.md's Communication section, replacing or expanding that section so the two do not contradict each other.

### Verified files

- `README.md`
- `CONTRIBUTING.md`

## Acceptance criteria

- [ ] A CODE_OF_CONDUCT.md exists at the repository root
- [ ] It states expected behaviour and a private reporting route
- [ ] README links to it
- [ ] CONTRIBUTING.md links to it and no longer conflicts with it
- [ ] No email address or handle is invented - the reporting route is real and reachable

## Notes for a first-time contributor

This is a documentation-only change: no application code is touched and no tests are affected. A good first pull request.

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="a2"></a>

#### A2 - Add a bug report issue template

`**Published as [#15](https://github.com/BistaDinesh03/critique/issues/15)**` | difficulty: **beginner** | labels: `documentation`, `good first issue`

## The problem

The repository has no `.github/` directory, so issues are opened with a blank body. Bug reports therefore often miss the details needed to reproduce them (page, browser, signed-in or not, steps).

## Why it matters

A structured template makes triage much faster and helps contributors give a complete report the first time. It also lowers the barrier for reporters who are not sure what is relevant.

## Scope and suggested direction

Create `.github/ISSUE_TEMPLATE/bug_report.md` with YAML front matter (`name`, `about`, `labels: bug`, `title`). Ask for: what happened, what you expected, exact steps to reproduce, the page URL, browser and OS, and whether you were signed in. Add a closing note pointing security reports to SECURITY.md instead, since Critique asks that vulnerabilities not be filed publicly.

### Verified files

- `SECURITY.md`

## Acceptance criteria

- [ ] .github/ISSUE_TEMPLATE/bug_report.md exists
- [ ] Front matter applies the existing `bug` label
- [ ] It asks for reproduction steps, page URL, browser/OS and auth state
- [ ] It links to SECURITY.md for vulnerability reports
- [ ] Language is welcoming and free of jargon

## Notes for a first-time contributor

A single Markdown file. Preview it with the GitHub UI before merging to confirm the front matter is valid.

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="a3"></a>

#### A3 - Add a feature request issue template

`**Published as [#16](https://github.com/BistaDinesh03/critique/issues/16)**` | difficulty: **beginner** | labels: `documentation`, `good first issue`

## The problem

Feature ideas currently arrive as free-form issues with no structure, so it is unclear whether a request solves a real problem or duplicates something already built.

## Why it matters

Critique's own philosophy is 'ask one focused question'. A template that asks requesters the same kind of focused question keeps the tracker useable and consistent with the product.

## Scope and suggested direction

Create `.github/ISSUE_TEMPLATE/feature_request.md` with front matter applying the existing `enhancement` label. Ask: the problem you hit, what you expected instead, and any idea you have. Add a checklist reminder to search existing issues first so duplicates are avoided.

## Acceptance criteria

- [ ] .github/ISSUE_TEMPLATE/feature_request.md exists
- [ ] Front matter applies the existing `enhancement` label
- [ ] It asks for the problem first, then the proposed solution
- [ ] It asks the reporter to search for duplicates first
- [ ] It does not promise the feature will be built

## Notes for a first-time contributor

A single Markdown file, no code involved.

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="a4"></a>

#### A4 - Add a pull request template

`**Published as [#17](https://github.com/BistaDinesh03/critique/issues/17)**` | difficulty: **beginner** | labels: `documentation`, `good first issue`

## The problem

Pull requests have no template, so reviewers often have to ask the same questions each time: what changed, why, how it was tested, and whether the change is user-visible.

## Why it matters

CONTRIBUTING.md already asks contributors to 'describe what you changed and why' and to 'run the tests'. A template turns that guidance into a consistent, unavoidable checklist and makes review faster for a small maintainer team.

## Scope and suggested direction

Create `.github/PULL_REQUEST_TEMPLATE.md` with short sections: summary of the change, why, how it was tested (including the exact pytest command and result), whether it changes visible behaviour or the data model, and a linked issue. Keep it short - a long template gets copy-pasted without reading.

## Acceptance criteria

- [ ] .github/PULL_REQUEST_TEMPLATE.md exists
- [ ] It asks for the test command and its result
- [ ] It asks whether behaviour or the data model changed
- [ ] It asks the author to link the related issue
- [ ] It stays under roughly 40 lines so it remains usable

## Notes for a first-time contributor

A single Markdown file at a well-known path.

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="a5"></a>

#### A5 - Add a question issue template that routes to issue #1

`**Published as [#18](https://github.com/BistaDinesh03/critique/issues/18)**` | difficulty: **beginner** | labels: `documentation`, `good first issue`

## The problem

Issue #1 is the designated place for questions, but nothing in the issue creation flow tells people that, so questions arrive as separate issues or go unasked.

## Why it matters

Consolidating questions in one thread keeps the tracker focused on actionable work while still giving newcomers a low-pressure place to ask. It also concentrates existing answers so the next person can find them.

## Scope and suggested direction

Create `.github/ISSUE_TEMPLATE/question.md` with front matter applying the existing `question` label and a description that says questions are also welcome in issue #1. Include a short body prompt asking what you are trying to do and where you got stuck. Reference #1 in the template text so it autolinks once published.

## Acceptance criteria

- [ ] .github/ISSUE_TEMPLATE/question.md exists
- [ ] Front matter applies the existing `question` label
- [ ] The template mentions issue #1 as an alternative place to ask
- [ ] It does not discourage questions

## Notes for a first-time contributor

A single Markdown file plus awareness of the existing labels.

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="a6"></a>

#### A6 - Add Dependabot configuration for pip and GitHub Actions

`**Published as [#19](https://github.com/BistaDinesh03/critique/issues/19)**` | difficulty: **beginner** | labels: `security`, `good first issue`

## The problem

The repository pins direct Python dependencies in `backend/requirements.txt` but has no automated way to be told when those versions have known vulnerabilities or newer patch releases. There is also no `.github/` directory, so no dependency update automation exists.

## Why it matters

Critique is a web app with an authentication surface. Automated update alerts are the cheapest way to learn about vulnerable pinned versions before a contributor stumbles on one.

## Scope and suggested direction

Add `.github/dependabot.yml` covering the `pip` ecosystem (root and `backend/`) and `github-actions`. Keep it modest: weekly checks, and open only a few pull requests at a time so a small maintainer team is not flooded. Do not upgrade the dependency pins in this issue - that is a separate, tested change.

### Verified files

- `backend/requirements.txt`
- `render.yaml`

## Acceptance criteria

- [ ] .github/dependabot.yml exists and is valid YAML
- [ ] It covers the `pip` ecosystem
- [ ] It covers `github-actions`
- [ ] It uses a weekly schedule with a small open-pull-requests limit
- [ ] No dependency version is changed by this PR

## Notes for a first-time contributor

Configuration only. Validate the YAML in the GitHub UI - a malformed file is silently ignored by Dependabot.

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="a7"></a>

#### A7 - Document the analytics event catalogue in docs/

`**Published as [#20](https://github.com/BistaDinesh03/critique/issues/20)**` | difficulty: **beginner** | labels: `documentation`, `good first issue`

## The problem

Critique records 20 analytics events, but the only authoritative list is the Python `VALID_EVENTS` set in `routes_analytics.py` (mirrored in `static/analytics.js`). `docs/api.md` describes the track endpoint but not the individual events, so a contributor adding a frontend feature has to read source to learn what already exists.

## Why it matters

A written catalogue prevents duplicate or near-duplicate event names (`share_copy_link` vs `share_copy_post` is exactly the kind of pair that gets confused) and makes the analytics surface legible to non-authors.

## Scope and suggested direction

Create a short `docs/analytics-events.md` listing every event name with a one-line description of when it fires, derived strictly from the current code. Note that the backend allowlist is the source of truth and that unknown names are rejected with `400`. Do not describe metrics that are not recorded, and do not invent business meaning.

### Verified files

- `backend/app/routes_analytics.py`
- `static/analytics.js`
- `docs/api.md`

## Acceptance criteria

- [ ] docs/analytics-events.md exists
- [ ] Every name in the backend VALID_EVENTS set appears exactly once
- [ ] Each entry says when the event fires, in one line
- [ ] It states that the allowlist is server-side and rejects unknown names
- [ ] No event or field is described that does not exist in the code

## Notes for a first-time contributor

Read the two files, transcribe, and keep the wording factual. Adding a regression test that the doc and the code agree is a welcome bonus.

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="a8"></a>

#### A8 - Add coverage measurement with pytest-cov and document the command

`**Published as [#21](https://github.com/BistaDinesh03/critique/issues/21)**` | difficulty: **beginner** | labels: `tests`, `good first issue`

## The problem

The test suite is solid (346 tests) but there is no way to see how much of `backend/app` it exercises, and CONTRIBUTING.md only documents running the tests, not measuring them.

## Why it matters

Coverage is a map of where the suite is thin, which helps a new contributor pick a genuinely useful test to write instead of guessing. It must be reported honestly: a number with no context is worse than no number.

## Scope and suggested direction

Add `pytest-cov` to the dev test requirements and document a coverage command in CONTRIBUTING.md and the README's Testing section. Report the actual measured figure only if you also state the command and the date, or better, leave the figure out and let readers run it. Do not add a coverage badge and do not set an aspirational target that is not met.

### Verified files

- `backend/requirements.txt`
- `CONTRIBUTING.md`
- `README.md`

## Acceptance criteria

- [ ] pytest-cov is available to the test suite
- [ ] CONTRIBUTING.md documents the exact coverage command
- [ ] The command runs locally and produces a report
- [ ] No invented or stale coverage percentage is published anywhere
- [ ] No coverage badge is added

## Notes for a first-time contributor

Small dependency and docs change. Run the command and paste the real output into your pull request.

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="a9"></a>

#### A9 - Explain how to run a single test in CONTRIBUTING.md

`**Published as [#22](https://github.com/BistaDinesh03/critique/issues/22)**` | difficulty: **beginner** | labels: `documentation`, `good first issue`

## The problem

CONTRIBUTING.md documents `python -m pytest tests/ -q`, which runs all 346 tests (about 40 seconds). While iterating on one change, contributors have to discover on their own that they can run a single file or test node.

## Why it matters

Knowing the one-test workflow is the difference between a 40-second and a sub-second feedback loop, and it is exactly the kind of unstated knowledge that makes a first contribution feel unwelcoming.

## Scope and suggested direction

Add a short subsection to CONTRIBUTING.md's Testing section showing how to run a single file, a single test function, and the `-k` keyword filter, using real test names that exist in the suite. Mention that the frontend render tests are skipped when `node` is not on PATH, so a contributor is not surprised by skipped tests.

### Verified files

- `CONTRIBUTING.md`
- `backend/tests/`

## Acceptance criteria

- [ ] CONTRIBUTING.md shows how to run one file, one function and a -k filter
- [ ] The example test names actually exist in backend/tests
- [ ] It explains why some tests skip when Node.js is absent
- [ ] It does not remove the full-suite command

## Notes for a first-time contributor

Pure documentation, but verify every command you document.

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="a10"></a>

#### A10 - Reconcile the README analytics figures with the HTML analytics report

`**Published as [#23](https://github.com/BistaDinesh03/critique/issues/23)**` | difficulty: **beginner** | labels: `documentation`, `good first issue`

## The problem

The README's Product analytics section quotes 1,443 page views / 263 unique visitors and embeds `docs/analytics-snapshot.svg`. The repository now also contains `docs/analytics-snapshot.html`, which presents a different supplied snapshot (1,582 page views / 293 unique visitors). Both are labelled as point-in-time snapshots with an unspecified reporting period, and nothing in the repository says which is more recent or authoritative.

## Why it matters

Two different sets of headline numbers in the same repository looks sloppy and, worse, a reader cannot tell which to trust. This is a documentation-accuracy problem, not a data problem - the fix is to explain the relationship, not to pick a winner.

## Scope and suggested direction

Update the README so it is unambiguous: the SVG is the figure shown, and the HTML report is the detailed view of a separate snapshot. State plainly that the two carry different figures and that neither has a known reporting period. Do not delete either artefact, do not average or reconcile the numbers, and do not present either as current or live.

### Verified files

- `README.md`
- `docs/analytics-snapshot.svg`
- `docs/analytics-snapshot.html`

## Acceptance criteria

- [ ] README explains that the SVG and HTML are two different snapshots
- [ ] It does not claim one supersedes the other
- [ ] Both files remain in the repository
- [ ] No figure is invented, averaged or presented as live
- [ ] The 'reporting period unspecified' caveat remains visible

## Notes for a first-time contributor

This needs careful wording more than code. Read both artefacts' own disclaimers first and mirror their language.

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="a11"></a>

#### A11 - Add an .editorconfig for consistent whitespace and line endings

`**Published as [#24](https://github.com/BistaDinesh03/critique/issues/24)**` | difficulty: **beginner** | labels: `documentation`, `good first issue`

## The problem

The repository mixes hand-edited Markdown, Python, HTML, CSS and JavaScript with no shared whitespace convention. Contributor editors can silently convert line endings or retab files, producing noisy diffs.

## Why it matters

Critique asks contributors to keep pull requests focused and small. Spurious whitespace churn in a diff makes that harder for reviewers and for anyone reading the history later.

## Scope and suggested direction

Add a root `.editorconfig` matching the conventions already in the code: UTF-8 without BOM, LF line endings, trailing whitespace trimmed, a final newline, and the indentation style each file type already uses (check the existing Python and JS files rather than guessing). Keep it minimal - it is a convention file, not a formatter.

## Acceptance criteria

- [ ] .editorconfig exists at the repository root
- [ ] It sets utf-8, lf, insert_final_newline and trim_trailing_whitespace
- [ ] Indent settings match the existing files for each type
- [ ] No source file is reformatted by this PR

## Notes for a first-time contributor

Inspect a few existing files first so the settings describe the code as it is, not as you prefer it.

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="a12"></a>

#### A12 - Clarify the two requirements.txt files and how they relate

`**Published as [#25](https://github.com/BistaDinesh03/critique/issues/25)**` | difficulty: **beginner** | labels: `documentation`, `good first issue`

## The problem

There are two requirements files: the root `requirements.txt` contains only `-r backend/requirements.txt`, and `backend/requirements.txt` holds the actual pins. README and CONTRIBUTING both tell people to run `pip install -r requirements.txt` from the repository root. A newcomer opening the root file sees an empty-looking list and may assume the project has no dependencies.

## Why it matters

Install instructions are the first thing a contributor runs. If the file they open does not match what they were told, confidence in the docs drops immediately.

## Scope and suggested direction

Explain the indirection in the README's Getting started section (and add a one-line comment at the top of the root file) so it is obvious the root file delegates to `backend/`. Keep installing from the root, since that is what the instructions already say. Do not merge or move the files, which would change the documented workflow.

### Verified files

- `requirements.txt`
- `backend/requirements.txt`
- `README.md`

## Acceptance criteria

- [ ] README explains that the root file includes backend's
- [ ] The root requirements.txt has an explanatory comment
- [ ] Documented install commands still work unchanged
- [ ] No dependency is added, removed or re-pinned

## Notes for a first-time contributor

A comment plus a short paragraph. Verify the install command still works.

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


### Frontend and user experience (10)


<a id="b1"></a>

#### B1 - Add Open Graph metadata to Discover and project pages

`**Published as [#26](https://github.com/BistaDinesh03/critique/issues/26)**` | difficulty: **advanced** | labels: `enhancement`, `help wanted`

## The problem

Only the homepage has social-preview metadata. `index.html` carries a full set of `og:` and `twitter:` tags pointing at `static/og-image.png`, but `discover.html`, `project_detail.html`, `project_results.html` and `my_projects.html` have only charset and viewport meta tags. A link to a specific project shared on X, Reddit or Discord therefore previews with no title, description or image.

## Why it matters

Sharing is the main growth loop Critique has, and the share panel (`static/share.js`) actively encourages posting project links. Right now those links look bare, which undercuts the feature that exists to drive traffic.

## Scope and suggested direction

**Design discussion required before starting.** The five pages are served as static files read from disk by `_page_response()` in `main.py` - the server returns the same bytes for every visitor, and social crawlers do not execute JavaScript. Adding per-project metadata therefore means choosing between: (a) static tags for the non-project pages, which is simple and covers Discover; and (b) server-side injection of the project title, description and image into the `project_detail` response, which requires reading project data at page-serve time and reasoning about the `Cache-Control: private, no-store` header already set on pages. Propose an approach in a comment before implementing (b).

### Verified files

- `backend/app/main.py`
- `frontend/discover.html`
- `frontend/project_detail.html`
- `static/og-image.png`

## Acceptance criteria

- [ ] Discover has og: and twitter: tags with a real title and description
- [ ] Any project-page metadata uses real data from the database, never a placeholder
- [ ] og:image points at an existing asset and its stated dimensions match the file
- [ ] Existing homepage metadata is unchanged
- [ ] A test covers whatever the chosen approach produces

## Notes for a first-time contributor

The advanced part is architectural, not syntax: the pages are static and crawlers do not run JS. Discuss the approach in issue #1 first.

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="b2"></a>

#### B2 - Improve project empty states

`**Already open as [#10](https://github.com/BistaDinesh03/critique/issues/10)** - reused, not duplicated` | difficulty: **beginner** | labels: `enhancement`, `good first issue`

## The problem

Empty pages can feel confusing when there are no projects or feedback yet.

## Why it matters

An empty list with no explanation leaves the visitor unsure whether something is broken or simply empty, and gives them no next step. A good empty state turns a dead end into an invitation.

## Scope and suggested direction

Create helpful empty states that explain what is happening and offer an obvious next action. For example, an empty My Projects page could say there are no projects yet and link to the submission form. Match Critique's existing design language (`static/shared.css` tokens) and keep it simple.

### Verified files

- `frontend/my_projects.html`
- `frontend/discover.html`
- `static/shared.css`

## From the original issue

An example target:

```
No projects yet

Be the first builder to share a project and ask for feedback.
[Submit your project]
```

## Acceptance criteria

- [ ] Every currently-empty surface explains why it is empty
- [ ] Each empty state offers one clear next action
- [ ] Styling reuses existing shared.css tokens rather than new ones
- [ ] Layouts remain usable on mobile
- [ ] Existing non-empty rendering is unchanged

## Notes for a first-time contributor

Start with My Projects, where the empty state is easiest to reach. Ask for the design in issue #1 if you are unsure.

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="b3"></a>

#### B3 - Improve feedback form UX

`**Already open as [#11](https://github.com/BistaDinesh03/critique/issues/11)** - reused, not duplicated` | difficulty: **beginner** | labels: `enhancement`, `help wanted`, `good first issue`

## The problem

Giving feedback should feel quick and effortless. The feedback form can be made clearer and easier for someone to submit a useful response.

## Why it matters

The feedback form is the surface Critique exists for. Every point of friction here directly reduces the number of responses a builder receives, which is the whole product promise.

## Scope and suggested direction

Improve the feedback form UX without changing the core functionality. Candidates: make the project's one question more prominent, improve the input experience, add helpful placeholder text, improve submit button states, clarify validation and error messages, and improve the mobile experience. Keep the existing design language and do not add dependencies.

### Verified files

- `frontend/project_detail.html`
- `static/shared.css`
- `static/ui.js`

## Contributor challenge

After your improvement, post the project on Critique and ask other builders: *"Would this make you more likely to give useful feedback?"* Use what you learn before opening the PR.

**Build - get feedback - improve - PR**

## Acceptance criteria

- [ ] The project's question is visually the most prominent element in the form
- [ ] Validation and error messages are specific and readable
- [ ] Submit states are clear (idle, submitting, success, error)
- [ ] Mobile layout is comfortable to use one-handed
- [ ] Existing feedback submission still works end to end

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="b4"></a>

#### B4 - Add keyboard accessibility improvements

`**Already open as [#12](https://github.com/BistaDinesh03/critique/issues/12)** - reused, not duplicated` | difficulty: **intermediate** | labels: `enhancement`, `help wanted`, `accessibility`

## The problem

Critique should be easy to use for people who prefer or need keyboard navigation. Today, focus handling is not systematically defined across the main pages.

## Why it matters

Keyboard access is a correctness issue, not a nicety: a visitor who cannot Tab to the feedback form cannot give feedback at all. It also tends to improve the experience for everyone through clearer focus indication.

## Scope and suggested direction

Improve basic keyboard accessibility across the main pages: clear focus states, logical tab order, keyboard-accessible buttons and controls, proper form labels, and accessible navigation. Note that all `<img>` elements already carry `alt` attributes (decorative ones correctly use `alt=""`), so do not re-do that work - concentrate on focus, roles and labels. Check the custom share and toast components in `static/share.js` and `static/ui.js`, which build DOM nodes dynamically and can easily lose focus handling.

### Verified files

- `static/ui.js`
- `static/share.js`
- `frontend/project_detail.html`
- `frontend/discover.html`
- `static/shared.css`

## Contributor challenge

After your changes, post the improvement on Critique and ask: *"Is this easier to navigate and use?"* Then open your PR.

## Triage note for maintainers

The live issue #12 carries the `good first issue` label. This roadmap assesses the work as **intermediate**, because half of it lives in components that build their DOM in JavaScript (`share.js`, `ui.js`), where focus handling is easy to lose. Suggested options: keep the label and scope the first PR to static markup only, or drop the label. See roadmap issue F1.

## Acceptance criteria

- [ ] Every interactive control is reachable by Tab in a sensible order
- [ ] Focus is always visible and never trapped
- [ ] Custom components built in JS expose accessible names
- [ ] Form controls have associated labels
- [ ] Mouse-only interactions now have a keyboard path

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="b5"></a>

#### B5 - Improve project page navigation and information hierarchy

`**Already open as [#13](https://github.com/BistaDinesh03/critique/issues/13)** - reused, not duplicated` | difficulty: **intermediate** | labels: `enhancement`, `help wanted`

## The problem

As Critique grows, project pages contain more information and actions. Visitors should be able to quickly understand a project and find the important actions.

## Why it matters

A visitor landing on a project page has seconds to understand what is being asked of them. If the one focused question is not immediately obvious, they leave without answering - and the builder gets nothing.

## Scope and suggested direction

Improve the navigation and information hierarchy on the project page: make the main question more prominent, make the feedback action easier to find, improve spacing and visual hierarchy, clarify navigation on mobile, and keep important actions easy to reach. Do not remove existing functionality.

### Verified files

- `frontend/project_detail.html`
- `static/shared.css`

## Triage note for maintainers

The live issue #13 carries the `good first issue` label. This roadmap assesses it as **intermediate** because the change spans the whole information hierarchy of a page rather than one isolated element. Consider splitting it: a first PR for prominence of the question, a second for mobile navigation.

## Acceptance criteria

- [ ] The project's question is identifiable within the first screenful
- [ ] The primary feedback action is unambiguous on desktop and mobile
- [ ] Spacing and hierarchy follow existing shared.css tokens
- [ ] No existing feature or control is removed
- [ ] The page works on desktop and mobile

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="b6"></a>

#### B6 - Extend loading states to the surfaces that do not have them yet

`**Already open as [#9](https://github.com/BistaDinesh03/critique/issues/9)** - reused, not duplicated` | difficulty: **intermediate** | labels: `enhancement`, `help wanted`

## The problem

Critique already ships skeletons for the homepage grid, the Discover list and the project page, and `backend/tests/test_loading_ux.py` holds those pages to a strict contract: an announced `aria-busy` placeholder, a successful response that replaces it, a failure path that offers a retry, and exactly one request per render. Other surfaces - My Projects, the results dashboard and the post-submit share panel - have no equivalent.

## Why it matters

The existing work shows the project already considers loading states part of its quality bar. Leaving a few surfaces inconsistent means those pages still show a blank or a stalled control, which is exactly what the implemented work was meant to eliminate.

## Scope and suggested direction

Extend the same pattern to My Projects, the results dashboard and the share panel. Reuse the existing skeleton markup and `aria-busy` convention rather than inventing a second one, and add coverage to `test_loading_ux.py` using the same Node harness so the new surfaces are held to the same contract.

### Verified files

- `frontend/my_projects.html`
- `frontend/project_results.html`
- `static/share.js`
- `backend/tests/test_loading_ux.py`

## Why this is not a duplicate of the original loading issue

Loading states for the three main surfaces are already implemented and tested. This issue is deliberately scoped to the remaining surfaces so the work is bounded and reviewable.

## Acceptance criteria

- [ ] Each targeted surface shows an announced placeholder while loading
- [ ] Success replaces the placeholder with real content
- [ ] Failure shows a message and a retry control, not an endless spinner
- [ ] Each critical endpoint is requested exactly once per render
- [ ] test_loading_ux.py covers the new surfaces

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="b7"></a>

#### B7 - Show a "Feedback needed" status on projects

`**Already open as [#4](https://github.com/BistaDinesh03/critique/issues/4)** - reused, not duplicated` | difficulty: **intermediate** | labels: `enhancement`, `help wanted`

## The problem

Add a small status to projects showing whether they are still looking for feedback, for example "Feedback needed" versus "Feedback received". The status should reflect the number of responses.

## Why it matters

Reviewers want to spend their time where it counts. Without a signal, reviewers answer projects that already have plenty of feedback while newer projects go unnoticed - which also hurts the builders most in need.

## Scope and suggested direction

Show the status on project cards in Discover and on the project page, updating automatically as feedback arrives. Keep it visually simple and use existing tokens. The response count is already available on Discover items as `response_count`, so this should not need a new endpoint. Do not expose any private feedback - only the existence or absence of responses.

### Verified files

- `frontend/discover.html`
- `frontend/project_detail.html`
- `backend/app/routes_projects.py`
- `static/shared.css`

**Design note:** agree the exact wording and the threshold for 'received' in a comment first - emoji-heavy status text has been avoided elsewhere in the product, so keep the treatment restrained.

## Acceptance criteria

- [ ] New projects show a 'Feedback needed' style status
- [ ] The status changes once feedback exists
- [ ] It appears on Discover cards and on the project page
- [ ] No private written suggestion is exposed by the status
- [ ] Layout remains usable on mobile

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="b8"></a>

#### B8 - Add project categories to Discover

`**Already open as [#5](https://github.com/BistaDinesh03/critique/issues/5)** - reused, not duplicated` | difficulty: **intermediate** | labels: `enhancement`, `help wanted`

## The problem

Add categories to Critique projects so people can find projects they are interested in - for example SaaS, Website, Open Source, Mobile App, Design, Student Project, Other. A project would have one primary category.

## Why it matters

Discover is ranked deterministically by need, freshness and question quality. That ranking answers "what needs feedback" but not "what do I understand well enough to judge". Categories let a reviewer contribute where they have real expertise, which should raise feedback quality.

## Scope and suggested direction

Add an optional category when submitting a project, display it on project cards, and let visitors filter Discover by category. This touches the model, so plan the migration carefully: `database.py` runs lightweight additive migrations on startup for both SQLite and PostgreSQL, and existing projects must keep working with no category set. Discuss the schema change in a comment before implementing.

### Verified files

- `backend/app/models.py`
- `backend/app/database.py`
- `backend/app/routes_projects.py`
- `backend/app/schemas.py`
- `frontend/discover.html`

**Please discuss the schema change and the category list before implementing** - this is the largest open data-model change in the tracker and the maintainer may have opinions on scope.

## Acceptance criteria

- [ ] A project can be given one category at submission time
- [ ] The category appears on Discover cards
- [ ] Discover can be filtered by category
- [ ] Existing projects without a category still render correctly
- [ ] The startup migration works on both SQLite and PostgreSQL
- [ ] Ranking is not unintentionally broken by the filter

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="b9"></a>

#### B9 - Add a skip-to-content link and semantic landmarks to every page

`**Published as [#27](https://github.com/BistaDinesh03/critique/issues/27)**` | difficulty: **intermediate** | labels: `accessibility`, `enhancement`, `help wanted`

## The problem

None of the five frontend pages provides a skip link, and the shared header and footer markup is repeated per page rather than expressed as labelled `<header>`/`<nav>`/`<main>` landmarks. A keyboard or screen-reader visitor must Tab through the entire navigation on every page before reaching the content.

## Why it matters

This is the single highest-leverage keyboard accessibility improvement available, and it pairs naturally with the existing keyboard work. It also makes the pages more predictable for assistive technology without changing how they look.

## Scope and suggested direction

Add a visually-hidden-until-focused skip link as the first focusable element on each page, targeting the main content region. Ensure each page has one `<main>` landmark with a stable id, and that the header and footer use semantic elements with appropriate `role`/`aria-label` where needed. Because the same header is duplicated across five files, keep the markup identical in each. Do not change the visual design.

### Verified files

- `frontend/index.html`
- `frontend/discover.html`
- `frontend/my_projects.html`
- `frontend/project_detail.html`
- `frontend/project_results.html`
- `static/shared.css`

## Acceptance criteria

- [ ] The first Tab on each page reveals a visible skip link
- [ ] Activating it moves focus to the main content region
- [ ] Each page has exactly one main landmark
- [ ] Header and footer are exposed as labelled landmarks
- [ ] Visual appearance is unchanged
- [ ] Existing keyboard behaviour is not broken

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="b10"></a>

#### B10 - Honour prefers-reduced-motion in shared styles

`**Published as [#28](https://github.com/BistaDinesh03/critique/issues/28)**` | difficulty: **intermediate** | labels: `accessibility`, `enhancement`, `help wanted`

## The problem

Critique's shared stylesheet defines transition tokens and the UI layer animates toasts and state changes, but there is no `prefers-reduced-motion` handling anywhere in `static/`.

## Why it matters

Motion can cause genuine vestibular symptoms for some visitors. Honouring the operating-system preference is a one-file, low-risk change that makes the whole product more usable, and it is a friendly first accessibility contribution.

## Scope and suggested direction

Add a `@media (prefers-reduced-motion: reduce)` block in `static/shared.css` that neutralises non-essential animation and transition. Audit which transitions exist (the `--transition-fast` and `--transition-normal` tokens, plus any keyframe animations in the UI layer) and suppress only those that are decorative - never remove state feedback that conveys meaning, such as an error border appearing.

### Verified files

- `static/shared.css`
- `static/ui.js`

## Acceptance criteria

- [ ] static/shared.css contains a prefers-reduced-motion block
- [ ] Decorative transitions and animations are neutralised
- [ ] Meaningful state changes remain perceivable
- [ ] No layout shifts when the preference is enabled
- [ ] The change is limited to CSS with no new dependencies

## Notes for a first-time contributor

Good first accessibility contribution: small, self-contained, and easy to verify by toggling the OS setting.

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


### Backend and API (10)


<a id="c1"></a>

#### C1 - Add an optional GitHub repository link to projects

`**Already open as [#3](https://github.com/BistaDinesh03/critique/issues/3)** - reused, not duplicated` | difficulty: **intermediate** | labels: `enhancement`, `help wanted`

## The problem

Project owners cannot link to the source of what they built. A visitor who wants to inspect the code has to find the repository themselves.

## Why it matters

Many Critique users are developers and open-source makers. Showing the repository turns a feedback session into a potential contribution, and it gives reviewers context that helps them give a more useful answer.

## Scope and suggested direction

Allow project owners to optionally add a GitHub repository URL when submitting a project, and render a "View on GitHub" link on the project page that opens in a new tab. The field must stay optional and existing projects must keep working, so this needs an additive model change plus a startup migration entry in `database.py`. Validate the URL at the schema layer (https scheme, github.com host) rather than trusting the client, and escape it on output like every other user-controlled value.

### Verified files

- `backend/app/models.py`
- `backend/app/database.py`
- `backend/app/schemas.py`
- `backend/app/routes_projects.py`
- `frontend/project_detail.html`

## Acceptance criteria

- [ ] A GitHub URL can be supplied when creating a project
- [ ] The field is optional and existing projects are unaffected
- [ ] Non-GitHub or malformed URLs are rejected server-side
- [ ] The link renders on the project page and opens in a new tab with rel=noopener
- [ ] The value is escaped on output
- [ ] The startup migration works on SQLite and PostgreSQL

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="c2"></a>

#### C2 - Bound the unbounded list endpoints with pagination

`**Published as [#29](https://github.com/BistaDinesh03/critique/issues/29)**` | difficulty: **intermediate** | labels: `backend`, `enhancement`, `help wanted`

## The problem

The Discover feed is already paginated (`page`, `page_size` capped at 50, with offset maths and `total_pages`), and `docs/api.md` documents it. Two other endpoints are not: `GET /api/projects/my/list` and `GET /api/projects/{id}/responses` both call `.all()` and return every matching row.

## Why it matters

Both endpoints grow without limit as the site grows. A prolific user's project list, or a popular project's response list, returns an ever-larger payload on every page load - a latency and memory problem that gets worse over time and is invisible in small development datasets.

## Scope and suggested direction

Apply the same pagination contract already used by the Discover feed so the API stays consistent: the same `page`/`page_size` parameter names, the same `ge=1` / `le=1`-style validation, and a response shape that includes the total and total pages. Update `docs/api.md`, and check every frontend caller so no page silently loses rows it previously received. Discuss the response shape before implementing, since changing it is a breaking API change for existing callers.

### Verified files

- `backend/app/routes_projects.py`
- `backend/app/routes_responses.py`
- `backend/app/routes_analytics.py`
- `docs/api.md`
- `frontend/my_projects.html`
- `frontend/project_results.html`

## Acceptance criteria

- [ ] `/api/projects/my/list` accepts page and page_size with the same bounds as Discover
- [ ] `/api/projects/{id}/responses` accepts page and page_size
- [ ] Defaults preserve today's behaviour for small datasets
- [ ] docs/api.md documents both
- [ ] All frontend callers still receive the data they need
- [ ] Tests cover paging, boundary values and out-of-range requests

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="c3"></a>

#### C3 - Send a Retry-After header with 429 responses

`**Published as [#30](https://github.com/BistaDinesh03/critique/issues/30)**` | difficulty: **beginner** | labels: `backend`, `enhancement`, `good first issue`

## The problem

`rate_limit()` raises a `429` with a JSON detail but no `Retry-After` header. Clients hitting a limit are told they are rate-limited but not when they may try again.

## Why it matters

`Retry-After` is the standard, machine-readable way to say "wait this long". Without it a well-behaved client has to guess or back off blindly, and a browser gives the visitor no useful guidance. The rate limiter already knows each endpoint's window, so the value is available.

## Scope and suggested direction

Raise the `HTTPException` with `headers={"Retry-After": ...}` computed from the configured window. Prefer the conservative, obviously-correct calculation (the remaining window) over a precise one, and document the chosen semantics in a comment. Keep the existing JSON `detail` body so current tests and clients keep working.

### Verified files

- `backend/app/rate_limit.py`
- `backend/tests/test_rate_limit.py`

**Note:** this pairs with a test-only follow-up that locks the header contract in place. See the tests & developer experience list.

## Acceptance criteria

- [ ] 429 responses include a Retry-After header
- [ ] The value is derived from the endpoint's configured window, not hardcoded
- [ ] The JSON detail body is unchanged
- [ ] A test asserts the header is present and numeric
- [ ] Existing rate-limit tests still pass

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="c4"></a>

#### C4 - Make the analytics event allowlist a single source of truth

`**Published as [#31](https://github.com/BistaDinesh03/critique/issues/31)**` | difficulty: **intermediate** | labels: `backend`, `enhancement`

## The problem

The list of valid analytics event names is written out twice: as the `VALID_EVENTS` set in `backend/app/routes_analytics.py`, and again as the `VALID_EVENTS` array in `static/analytics.js`. Nothing enforces that the two stay aligned.

## Why it matters

The server is authoritative and rejects unknown names with `400`, so a frontend that invents an event fails silently at runtime - `trackEvent()` swallows the error with an empty `catch`. The two lists have already needed to change together (the share and submit events were both added in pairs), and a divergence would quietly lose data.

## Scope and suggested direction

Remove the duplication. The cleanest direction is to drop the duplicated frontend array and let the server be the only allowlist, since a client-side copy cannot add security and only risks drift. If you prefer to keep a client-side guard for bandwidth reasons, generate it from the Python set in a test instead of maintaining it by hand. Do not change the event names themselves - the existing analytics depend on them.

### Verified files

- `backend/app/routes_analytics.py`
- `static/analytics.js`
- `backend/tests/test_analytics_validation.py`

## Acceptance criteria

- [ ] Event names exist in exactly one authoritative place
- [ ] The client still refuses to send names the server would reject
- [ ] A test fails if the two lists would diverge
- [ ] No existing event name changes
- [ ] All existing analytics tests still pass

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="c5"></a>

#### C5 - Make the analytics dashboard owner allowlist configurable

`**Published as [#32](https://github.com/BistaDinesh03/critique/issues/32)**` | difficulty: **beginner** | labels: `backend`, `enhancement`, `good first issue`

## The problem

`routes_analytics_dashboard.py` guards the owner dashboard with a hardcoded Python set: `OWNER_USERNAMES = {"BistaDinesh03"}`. Granting or revoking dashboard access means editing source and redeploying.

## Why it matters

A maintainer list belongs in configuration, not code, for the same reason secrets do: it changes for operational reasons and should not require a code change to review. It also blocks any second maintainer or organisation fork from using the dashboard at all.

## Scope and suggested direction

Read the allowlist from an environment variable (for example a comma-separated `ANALYTICS_OWNER_USERNAMES`), defaulting safely to the current behaviour so the deployed site keeps working unchanged. Add the variable to `.env.example` and document it in the README's environment table. Keep the 403 behaviour and its existing tests exactly as they are.

### Verified files

- `backend/app/routes_analytics_dashboard.py`
- `backend/app/config.py`
- `.env.example`
- `README.md`

**Security note:** the default must fail closed - if the variable is absent or empty, do not grant dashboard access to everyone.

## Acceptance criteria

- [ ] The owner allowlist is read from the environment
- [ ] Default behaviour matches today's single-owner access
- [ ] The variable is documented in .env.example and the README table
- [ ] No secret or real credential is written into any file
- [ ] Existing 403 and dashboard tests still pass

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="c6"></a>

#### C6 - Replace the analytics dashboard's sequential count queries

`**Published as [#33](https://github.com/BistaDinesh03/critique/issues/33)**` | difficulty: **intermediate** | labels: `backend`, `performance`, `help wanted`

## The problem

`get_analytics_dashboard()` runs roughly fourteen separate `db.query(func.count(...))` statements, one per event name, each executing its own SQL round trip and its own full scan of `analytics_events` filtered on `event_name`.

## Why it matters

`event_name` is indexed, so each individual query is cheap - but fourteen scans of a growing table to produce one dashboard response is wasteful, and the cost grows linearly with the table rather than staying flat. This is the endpoint the site owner uses most.

## Scope and suggested direction

Collapse the per-event counts into grouped aggregation - a single query using `func.count()` over `group_by(AnalyticsEvent.event_name)` - and read the results into a dict, defaulting missing events to `0` so the response shape is unchanged. Keep the zero-denominator safety the existing tests cover, and do not change the JSON response contract. Verify with the existing dashboard tests rather than assuming.

### Verified files

- `backend/app/routes_analytics_dashboard.py`
- `backend/tests/test_analytics_new_events.py`

**Keep the behaviour identical** - this is a pure refactor. Add a test that pins the current response shape so a future edit cannot drift it.

## Acceptance criteria

- [ ] Dashboard totals are computed with grouped aggregation
- [ ] The JSON response shape and values are unchanged
- [ ] Events with no rows still report 0
- [ ] All existing dashboard tests pass without modification
- [ ] The query count no longer scales with the number of event names

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="c7"></a>

#### C7 - Add conditional caching to the badge SVG endpoint

`**Published as [#34](https://github.com/BistaDinesh03/critique/issues/34)**` | difficulty: **intermediate** | labels: `backend`, `performance`, `help wanted`

## The problem

`GET /badge/{project_id}.svg` responds with `Cache-Control: no-cache` and re-queries the database on every single request. Because the badge is designed to be embedded in READMEs, GitHub's camo proxy fetches it repeatedly for every visitor to every repository that uses it.

## Why it matters

A badge that changes only when a new response is submitted is an ideal candidate for caching, and the current policy makes every page view of a README cost Critique two database queries (project lookup, then count). As adoption grows this is the most-requested endpoint the site has.

## Scope and suggested direction

Add conditional-request support: emit an `ETag` derived from the response count (and project existence), honour `If-None-Match`, and return `304` with no body when unchanged. Add a short `Cache-Control: public, max-age=<small number>` so intermediaries can help too. Decide the freshness window deliberately and document it: a badge that is a few seconds stale is fine, a badge that is hours stale is not. Keep the exact SVG output and the `1k+` formatting identical so existing embeds do not change appearance.

### Verified files

- `backend/app/routes_badge.py`
- `backend/tests/test_stats.py`

**Design consideration:** the ETag must change when the count changes, or a stale badge is served forever. Think about what to include in it.

## Acceptance criteria

- [ ] Badge responses carry an ETag
- [ ] If-None-Match returns 304 with no body
- [ ] Cache-Control uses a short public max-age, not no-cache
- [ ] The rendered SVG is byte-identical to today for a given count
- [ ] The 1k+ formatting rule is preserved
- [ ] Tests cover 200, 304 and the 404 for unknown projects

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="c8"></a>

#### C8 - Define a consistent JSON error contract for the API

`**Published as [#35](https://github.com/BistaDinesh03/critique/issues/35)**` | difficulty: **advanced** | labels: `backend`, `enhancement`, `help wanted`

## The problem

API errors are shaped inconsistently. FastAPI's default `HTTPException` handler returns `{"detail": "..."}`, the unhandled-exception handler in `main.py` returns the same shape for 500s, but validation errors from Pydantic return FastAPI's `loc`/`msg`/`type` structure, and the frontend reads `data.detail || 'Failed to submit.'` as a catch-all fallback.

## Why it matters

The frontend cannot reliably show a useful message, and a client author reading `docs/api.md` has to guess which shape each failure returns. It also makes the analytics funnel harder to interpret, since the client's generic fallback hides what actually went wrong.

## Scope and suggested direction

Introduce a single error shape and a FastAPI `exception_handler` for `HTTPException` that produces it, plus consistent handling of `RequestValidationError`. Include a stable machine-readable code, a human-readable message, and (optionally) a request id for correlation. **This is a breaking API change**, so discuss the shape in a comment and update `docs/api.md` and every frontend `response.json()` reader in the same change. Do not weaken any existing status-code behaviour - the 409-duplicate, 403-CSRF and 404 paths are covered by tests.

### Verified files

- `backend/app/main.py`
- `backend/app/schemas.py`
- `docs/api.md`
- `frontend/project_detail.html`
- `frontend/project_results.html`

**Discuss the contract before writing code.** Several tests assert on the current `detail` field, so this change has a wide blast radius and should be proposed first.

## Acceptance criteria

- [ ] All API errors return one documented JSON shape
- [ ] A stable error code accompanies the human message
- [ ] docs/api.md documents the contract
- [ ] Frontend error handling is updated to match
- [ ] Existing status codes are unchanged
- [ ] All existing tests pass, including 409, 403 and 404 cases

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="c9"></a>

#### C9 - Report database connectivity from the /health endpoint

`**Published as [#36](https://github.com/BistaDinesh03/critique/issues/36)**` | difficulty: **beginner** | labels: `backend`, `enhancement`, `good first issue`

## The problem

`GET /health` returns a fixed `{"status": "ok"}` without touching the database, so it reports healthy even when the database is unreachable or the connection pool is exhausted.

## Why it matters

Render uses this endpoint as the uptime probe that decides whether to route traffic to the instance. A health check that cannot fail gives a false green during exactly the outage it exists to detect, and hides database problems until users report them.

## Scope and suggested direction

Perform a minimal, cheap database check (for example a `SELECT 1` through the existing session) and return `503` with a clear body when it fails. Keep the success payload backward compatible by retaining the `status` key. Be careful about the check's cost - it runs on every probe - and about not leaking connection details in the error body.

### Verified files

- `backend/app/main.py`
- `backend/app/database.py`

**To test the failure path** you will need to force a DB error; monkeypatching the session in a test is the usual approach.

## Acceptance criteria

- [ ] A successful check still returns {"status": "ok"}
- [ ] An unreachable database returns 503, not 200
- [ ] The check is cheap enough to run on every probe
- [ ] No connection string or credential appears in the response
- [ ] A test covers both the healthy and unhealthy paths

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="c10"></a>

#### C10 - Set correct cache directives on authenticated JSON responses

`**Published as [#37](https://github.com/BistaDinesh03/critique/issues/37)**` | difficulty: **intermediate** | labels: `backend`, `security`, `help wanted`

## The problem

`main.py` sets `Cache-Control: private, no-store` on the HTML pages, correctly reasoning that the early-auth stamp varies by session cookie. The `/api/*` JSON responses have no explicit cache policy at all, including the authenticated ones that return a project owner's private written suggestions.

## Why it matters

Private written feedback is the most sensitive data Critique holds - the results endpoint returns suggestions only to the owner, determined server-side. Leaving caching unspecified lets a shared proxy or an aggressive browser cache decide, which can leak one user's private data to another. The existing `Vary: Cookie` reasoning on pages should extend here.

## Scope and suggested direction

Apply an explicit `private, no-store` policy to authenticated and owner-scoped API responses - at minimum the results endpoint and `/api/projects/my/list` - and consider an explicit `public` policy for genuinely public reads like the Discover feed if that is safe. Do this in a way that is obvious to a reviewer (middleware or per-route headers), and add tests that assert the headers, since cache policy is invisible in manual testing.

### Verified files

- `backend/app/main.py`
- `backend/app/routes_results.py`
- `backend/app/routes_projects.py`
- `backend/tests/test_privacy.py`

## Acceptance criteria

- [ ] Owner-scoped responses carry Cache-Control: private, no-store
- [ ] Private written suggestions cannot be cached by a shared cache
- [ ] Vary behaviour is considered and documented
- [ ] Tests assert the headers on owner-scoped and public endpoints
- [ ] No legitimate caching of public data is accidentally disabled

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


### Tests and developer experience (7)


<a id="d1"></a>

#### D1 - Add Ruff configuration and document the lint command

`**Published as [#38](https://github.com/BistaDinesh03/critique/issues/38)**` | difficulty: **beginner** | labels: `tests`, `good first issue`

## The problem

Critique has no linter and no lint configuration: there is no `pyproject.toml`, `.ruff.toml`, `setup.cfg` or `tox.ini` in the repository, and CONTRIBUTING.md's code-style section is advice rather than enforcement.

## Why it matters

A configured linter removes an entire category of review comment and catches real bugs (unused imports, undefined names, comparison bugs) for free. Ruff is a single dependency with no configuration ceremony, and documenting one command means every contributor can run the same check the maintainer will.

## Scope and suggested direction

Add a minimal `pyproject.toml` configuring Ruff to target the project's Python version and to select a restrained rule set - start with the default `E`/`F` set rather than enabling a large opinionated plugin that would flood the existing code with unrelated findings. Document the exact command in CONTRIBUTING.md and the README. If Ruff reports existing issues, either fix small ones in the same PR or scope the config so it is clean from day one - do not land a lint config that fails immediately, since contributors will then ignore it.

### Verified files

- `backend/requirements.txt`
- `CONTRIBUTING.md`
- `README.md`

## Acceptance criteria

- [ ] A Ruff configuration exists and is committed
- [ ] The documented command runs and exits clean on the current codebase
- [ ] CONTRIBUTING.md documents the command
- [ ] README mentions it alongside the test command
- [ ] The rule set is restrained and justified in a comment

## Notes for a first-time contributor

Run Ruff before committing the config and fix whatever it finds in the touched files, so the first impression is a passing check.

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="d2"></a>

#### D2 - Add a GitHub Actions workflow that runs the test suite

`**Published as [#39](https://github.com/BistaDinesh03/critique/issues/39)**` | difficulty: **intermediate** | labels: `tests`, `help wanted`

## The problem

The repository has no `.github/` directory and therefore no CI at all. The 346-test suite is only run when a maintainer remembers to run it locally, so a regression can reach `main` unnoticed.

## Why it matters

CI is the single biggest trust signal for a contributor: it tells people their pull request will be checked objectively, and it tells the maintainer that a green merge is actually green. It also gives the project a visible status badge that is real rather than decorative.

## Scope and suggested direction

Add `.github/workflows/tests.yml` running on pushes to `main` and on pull requests: set up Python 3.11 (matching the project's stated requirement), install `backend/requirements.txt`, and run the pytest suite from `backend`. Keep it minimal - no deployment steps, no secrets, no publishing. Ensure the workflow is read-only with respect to the repository (`permissions: contents: read`).

### Verified files

- `backend/requirements.txt`

**Follow-up:** the frontend render tests need Node.js and are skipped when it is absent - see the next issue for wiring those in properly.

## Acceptance criteria

- [ ] .github/workflows/tests.yml exists and is valid
- [ ] It runs pytest on pushes to main and on pull requests
- [ ] It declares minimal permissions
- [ ] It installs only what the suite needs
- [ ] It contains no deployment or publishing step
- [ ] The workflow passes on the current codebase

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="d3"></a>

#### D3 - Run the frontend render tests in CI by installing Node

`**Published as [#40](https://github.com/BistaDinesh03/critique/issues/40)**` | difficulty: **intermediate** | labels: `tests`, `help wanted`

## The problem

A meaningful part of the suite - `test_loading_ux.py`, `test_results_ui.py`, `test_project_form.py`, `test_auth_state_ui.py` and others - runs each page's real JavaScript inside a Node DOM harness. Every one of these modules is guarded by `pytest.mark.skipif(shutil.which("node") is None, ...)`, so they silently do nothing wherever Node is not installed.

## Why it matters

Those tests are the only ones that assert what the browser actually executes, so they are the most valuable regression protection the project has for frontend behaviour. A CI job that reports green while silently skipping them overstates coverage and hides real breakage.

## Scope and suggested direction

Add a Node setup step to the CI workflow (either a dedicated `actions/setup-node` step or a second job) so the harness actually runs in CI. Then make skipped frontend tests impossible to miss: assert on the collected test count, or add a step that fails if the frontend modules reported skips. Verify locally that the harness passes before relying on CI to tell you.

### Verified files

- `backend/tests/frontend_render_harness.js`
- `backend/tests/test_loading_ux.py`

**This depends on** the base CI workflow existing first.

## Acceptance criteria

- [ ] CI installs Node.js before running pytest
- [ ] The frontend harness tests actually execute in CI, not skip
- [ ] A guard makes unexpected skips fail the build
- [ ] The suite still passes end to end in the workflow
- [ ] Local runs without Node continue to skip gracefully

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="d4"></a>

#### D4 - Add a regression test for the 429 Retry-After contract

`**Published as [#41](https://github.com/BistaDinesh03/critique/issues/41)**` | difficulty: **intermediate** | labels: `tests`

## The problem

Once 429 responses carry a `Retry-After` header, nothing prevents a future refactor of `rate_limit.py` from dropping it - the header is invisible in manual testing and no current test asserts on response headers for 429.

## Why it matters

Client behaviour depends on this header, and the rate limiter already has a good test culture (spoofed `X-Forwarded-For` rejection, per-IP isolation, invalid-IP handling). Adding the header to that culture is cheap and stops silent regressions.

## Scope and suggested direction

Extend `backend/tests/test_rate_limit.py` to assert that an over-limit response includes `Retry-After`, that its value is a positive integer, and that it is derived from the endpoint's configured window rather than a constant. Keep the existing assertions intact.

### Verified files

- `backend/tests/test_rate_limit.py`
- `backend/app/rate_limit.py`

**Prerequisite:** the Retry-After header must be implemented first.

## Acceptance criteria

- [ ] A test asserts Retry-After is present on a 429
- [ ] The value is parsed as a positive integer
- [ ] The test would fail if the header were removed
- [ ] Existing rate-limit tests are unchanged and still pass

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="d5"></a>

#### D5 - Add a test asserting security headers on HTML and API responses

`**Published as [#42](https://github.com/BistaDinesh03/critique/issues/42)**` | difficulty: **intermediate** | labels: `tests`, `security`

## The problem

Critique sets no security response headers (there is no `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`, `Strict-Transport-Security` or `Referrer-Policy` anywhere in `backend/app`), and therefore no test covers them.

## Why it matters

Cache policy in this codebase is already protected by an assertion rather than by hope - pages carry `private, no-store` and `Vary: Cookie`, and that is tested. Security headers deserve the same treatment: they are invisible during manual testing and are the first thing a refactor removes.

## Scope and suggested direction

Write the tests first, against the header contract you believe the project should offer, and mark clearly in the pull request that they are expected to fail until the headers are implemented (or submit it alongside that work). Cover at least a page response, a public API response and a static asset, since the correct policy differs per surface. Coordinate with the security headers issue so the two changes do not conflict.

### Verified files

- `backend/tests/test_main.py`
- `backend/app/main.py`

**This is deliberately a test-first issue.** It pairs with the security headers implementation issue - coordinate so you are not both editing `main.py`.

## Acceptance criteria

- [ ] Tests assert the intended security headers per surface
- [ ] Coverage includes a page, an API response and a static asset
- [ ] The tests document why each header is expected
- [ ] No assertion is weakened to make an existing response pass
- [ ] Existing tests still pass

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="d6"></a>

#### D6 - Add a test keeping the backend and frontend analytics allowlists in sync

`**Published as [#43](https://github.com/BistaDinesh03/critique/issues/43)**` | difficulty: **intermediate** | labels: `tests`

## The problem

The analytics event allowlist exists twice - `VALID_EVENTS` in `routes_analytics.py` and the array of the same name in `static/analytics.js` - with no test tying them together. The server rejects unknown names with `400`, but the frontend swallows those failures in an empty `catch`, so a divergence is silent.

## Why it matters

The share events and the submit events were both added to both files by hand, which is exactly how the lists drift apart. A test makes the coupling explicit and turns a silent data loss into a loud build failure.

## Scope and suggested direction

Add a test that parses the event names out of `static/analytics.js` and asserts set equality with the Python `VALID_EVENTS`. Prefer parsing to importing - the JS file is not a Python module - and make the failure message explain which direction diverged. If the single-source-of-truth refactor lands first, replace this with a test asserting the generated client list matches.

### Verified files

- `backend/tests/test_analytics_validation.py`
- `backend/app/routes_analytics.py`
- `static/analytics.js`

**Prerequisite:** none, but coordinate with the single-source refactor so you do not duplicate effort.

## Acceptance criteria

- [ ] A test compares both allowlists as sets
- [ ] The failure message names the missing or extra events
- [ ] Adding an event to only one file breaks the test
- [ ] The test does not require Node.js
- [ ] Existing analytics tests still pass

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="d7"></a>

#### D7 - Pin the analytics dashboard response shape with a contract test

`**Published as [#44](https://github.com/BistaDinesh03/critique/issues/44)**` | difficulty: **intermediate** | labels: `tests`, `backend`

## The problem

`routes_analytics_dashboard.py` computes around fourteen totals and several ratios. The existing tests check individual values when specific events are inserted, but nothing asserts the complete set of keys the endpoint returns.

## Why it matters

The dashboard is consumed by the site owner and by the snapshot reports in `docs/`. A refactor that silently drops a key - or that renames one, as the grouped-aggregation change might - would corrupt those reports without failing a single existing test.

## Scope and suggested direction

Add a test that exercises the dashboard against a known fixture set and asserts the exact set of response keys, plus the zero-denominator behaviour for every ratio. This makes any future change to the contract a deliberate, reviewed act rather than an accident.

### Verified files

- `backend/tests/test_analytics.py`
- `backend/tests/test_analytics_new_events.py`
- `backend/app/routes_analytics_dashboard.py`

## Acceptance criteria

- [ ] A test asserts the complete set of dashboard response keys
- [ ] Ratios are asserted to be safe when a denominator is zero
- [ ] The test uses a controlled fixture rather than live state
- [ ] Existing dashboard tests remain unchanged
- [ ] The test fails if a key is added, removed or renamed

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


### Security, performance and reliability (6)


<a id="e1"></a>

#### E1 - Add security response headers to HTML and API responses

`**Published as [#45](https://github.com/BistaDinesh03/critique/issues/45)**` | difficulty: **intermediate** | labels: `security`, `enhancement`, `help wanted`

## The problem

Critique sets no security response headers. A repository-wide search for `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`, `Strict-Transport-Security` and `Referrer-Policy` returns nothing in `backend/app`. The only response-header logic in the app is `CacheControlMiddleware`, which handles caching alone.

## Why it matters

These headers are free, standard hardening that materially raise the cost of common attacks: MIME-sniffing, clickjacking, and referrer leakage of project URLs. Because Critique handles sessions and private written feedback, the absence is more consequential than on a static site.

## Scope and suggested direction

Add a small middleware alongside `CacheControlMiddleware` in `main.py` that sets a conservative baseline on responses: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` (or `SAMEORIGIN`), `Referrer-Policy: strict-origin-when-cross-origin`, and `Permissions-Policy` limited to what the app uses. Leave `Strict-Transport-Security` until `APP_ENV=production` behind HTTPS is confirmed, so local development is not broken. **Treat Content-Security-Policy as a separate issue** - the frontend uses inline scripts and inline `onerror` handlers that a strict CSP would break, so bundling it here would either ship a useless policy or break the site.

### Verified files

- `backend/app/main.py`
- `backend/tests/test_main.py`

**Discuss the exact header set in a comment before starting**, since the correct values depend on how the site is deployed.

## Acceptance criteria

- [ ] nosniff, frame and referrer-policy headers are present on responses
- [ ] Headers do not break local HTTP development
- [ ] The existing Cache-Control behaviour is unchanged
- [ ] Static assets, pages and API responses are all covered
- [ ] A test asserts the headers
- [ ] CSP is explicitly out of scope for this change

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="e2"></a>

#### E2 - Introduce a Content-Security-Policy without breaking the frontend

`**Published as [#46](https://github.com/BistaDinesh03/critique/issues/46)**` | difficulty: **advanced** | labels: `security`, `enhancement`, `help wanted`

## The problem

There is no Content-Security-Policy on any response. The frontend depends on inline `<script>` blocks in all five HTML pages and on inline event handlers in template strings - for example `onerror="this.style.display='none'"` in `discover.html` and `project_detail.html`. `main.py` also injects an inline early-auth `<script>` and `<style>` into `<head>` at serve time.

## Why it matters

CSP is the strongest available defence against injected script, which matters because projects carry user-supplied titles, descriptions, image URLs and written suggestions. But a policy that the existing code immediately violates is worse than none: the tempting quick fix is `unsafe-inline`, which buys nothing.

## Scope and suggested direction

**Design discussion required.** A workable route is staged: (1) remove the inline `onerror` handlers in favour of `addEventListener` or CSS; (2) move inline scripts into `/static/` files where possible; (3) decide how to handle the serve-time early-auth stamp - either nonces generated per request in `_page_response()` or hashes of the fixed scripts; (4) ship the policy in `Report-Only` mode first; (5) enforce only once reports are clean. Expect this to span several pull requests. Propose the plan before coding.

### Verified files

- `backend/app/main.py`
- `frontend/discover.html`
- `frontend/project_detail.html`
- `frontend/index.html`
- `static/shared.css`

**This is a multi-PR design effort.** Please post a plan in issue #1 before implementing - the maintainer may want to stage it differently.

## Acceptance criteria

- [ ] Inline event handlers are removed from template strings
- [ ] A policy is served, initially in Content-Security-Policy-Report-Only
- [ ] The policy does not rely on unsafe-inline for scripts
- [ ] All five pages and the injected early-auth stamp still work
- [ ] Enforcement is a separate, later step
- [ ] No third-party script source is added to the allowlist

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="e3"></a>

#### E3 - Serve an HTML 404 page for unknown routes

`**Published as [#47](https://github.com/BistaDinesh03/critique/issues/47)**` | difficulty: **beginner** | labels: `backend`, `enhancement`, `good first issue`

## The problem

An unknown path such as `/nonexistent` returns FastAPI's default JSON body `{"detail":"Not Found"}` with a `404`. `main.py` registers only a generic `Exception` handler returning JSON, and no `HTTPException` handler for pages - the `404` raises that exist are all API-level, inside the route modules.

## Why it matters

A visitor who follows a stale or mistyped link sees raw JSON in the browser, which looks broken rather than merely empty. Critique already presents careful empty states elsewhere, so a JSON 404 is out of character.

## Scope and suggested direction

Register a FastAPI `exception_handler(HTTPException)` that returns a branded `404` HTML page for browser navigation requests (keying on `Accept: text/html`) and preserves the JSON shape for `/api/*` and other JSON clients. Reuse the existing design tokens and header markup so the page matches the rest of the site, and offer a way onward - a link to Discover and to the homepage.

### Verified files

- `backend/app/main.py`
- `static/shared.css`

## Acceptance criteria

- [ ] An unknown browser route returns a styled HTML 404
- [ ] The response status is still 404
- [ ] API routes still return the JSON detail shape
- [ ] The page matches existing design tokens and includes the header
- [ ] The page offers a link back to a useful destination
- [ ] Existing 404 tests for API routes still pass

## Notes for a first-time contributor

Good first backend issue: one handler plus one HTML fragment, and the `Accept`-header split is the only subtlety.

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="e4"></a>

#### E4 - Bound the in-memory rate limiter's growth

`**Published as [#48](https://github.com/BistaDinesh03/critique/issues/48)**` | difficulty: **intermediate** | labels: `security`, `performance`, `help wanted`

## The problem

`rate_limit.py` keeps every timestamp in a module-level `defaultdict(list)`. `_cleanup_old()` prunes only the key being checked, so keys for client IPs that are never seen again stay in the dictionary forever, each holding a list of timestamps.

## Why it matters

Client IP is attacker-influenced: an attacker can rotate source addresses (or spoof `CF-Connecting-IP`, which is validated only as a well-formed IP, not as a trusted source) to create unbounded distinct keys. On a long-lived process this is a slow memory leak that an adversary can accelerate, which matters because the deployed service has a fixed memory allocation.

## Scope and suggested direction

Add periodic global pruning so stale keys are removed, not just stale timestamps within a live key. Options include pruning on a write counter, sweeping keys whose newest timestamp is older than the largest configured window, or capping the number of tracked keys with LRU eviction. Keep the existing per-IP semantics and all current tests passing, and be explicit in a comment about the trade-off you chose.

### Verified files

- `backend/app/rate_limit.py`
- `backend/tests/test_rate_limit.py`

## Acceptance criteria

- [ ] Keys for departed clients are eventually removed
- [ ] Memory use no longer grows without bound under address rotation
- [ ] Existing rate-limit behaviour and all its tests are unchanged
- [ ] The chosen trade-off is documented in code
- [ ] A test demonstrates a stale key is pruned

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="e5"></a>

#### E5 - Document and harden the rate limiter's multi-instance and restart behaviour

`**Published as [#49](https://github.com/BistaDinesh03/critique/issues/49)**` | difficulty: **advanced** | labels: `backend`, `security`, `help wanted`

## The problem

Rate-limiting state lives in process memory, so it resets on every restart and is not shared between instances. `render.yaml` defines a single web service today, so this is latent rather than active - but any autoscaling, zero-downtime deploy or second instance silently multiplies every limit by the number of processes, and a restart clears accumulated counters.

## Why it matters

The limits are most valuable against exactly the attacks that a restart or a second instance would defeat: email-login brute force (3 per 15 minutes) and project creation spam. If the deployment ever changes, protection degrades silently and no test would notice.

## Scope and suggested direction

**This is a design issue as much as a coding one.** Options: persist counters in the existing database (adds a write per request), keep them in memory but make the limitation explicit in README and SECURITY.md, or accept a shared store as a future dependency. Start by documenting the current behaviour honestly wherever it matters, then propose the smallest change that closes the real gap. Do not add a new infrastructure dependency lightly - CONTRIBUTING.md asks whether each dependency earns its place.

### Verified files

- `backend/app/rate_limit.py`
- `SECURITY.md`
- `README.md`
- `render.yaml`

**Please propose an approach before implementing.** Documenting the limitation is a valid and complete outcome for this issue on its own.

## Acceptance criteria

- [ ] The current restart and multi-instance behaviour is documented honestly
- [ ] SECURITY.md states what the limits do and do not protect against
- [ ] Any implementation change preserves all existing rate-limit tests
- [ ] No new infrastructure dependency is added without discussion
- [ ] The chosen approach is justified in a comment and in the PR description

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="e6"></a>

#### E6 - Stop serving mutable JavaScript and CSS with a 24-hour cache

`**Published as [#50](https://github.com/BistaDinesh03/critique/issues/50)**` | difficulty: **intermediate** | labels: `performance`, `security`, `help wanted`

## The problem

`CacheControlMiddleware` applies `Cache-Control: public, max-age=86400` to everything under `/static/` - including `analytics.js`, `share.js`, `ui.js` and `shared.css`, all of which change with every deploy.

## Why it matters

A browser or intermediary that cached `share.js` yesterday will keep running the old version for up to a day after a fix ships. That turns a deployed bug fix into a partially-deployed one, and makes frontend issues extremely hard to reproduce and diagnose. The static mount also serves `og-image.png` and logos, which genuinely are immutable and deserve the long cache.

## Scope and suggested direction

Split the policy by content type: keep a long `max-age` for genuinely stable assets (images, favicon) and use a short `max-age` or `no-cache` with revalidation for `.js` and `.css`. The stronger, slightly larger change is content-hashed filenames so assets can be cached forever - propose that before implementing, since it touches how the HTML pages reference assets. Keep the header semantics explicit so a reviewer can see the intent.

### Verified files

- `backend/app/main.py`
- `backend/tests/test_main.py`

**Coordinate with the security headers issue** - both edit `CacheControlMiddleware` in `main.py`.

## Acceptance criteria

- [ ] JS and CSS are no longer cached for 24 hours
- [ ] Images retain a long cache lifetime
- [ ] The policy is expressed clearly in code
- [ ] Existing cache-header tests are updated deliberately, not weakened
- [ ] Frontend fixes reach users promptly after deploy

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


### Community and product improvements (5)


<a id="f1"></a>

#### F1 - Create and document a label taxonomy for the expanded issue tracker

`**Published as [#51](https://github.com/BistaDinesh03/critique/issues/51)**` | difficulty: **beginner** | labels: `documentation`, `good first issue`

## The problem

The repository has 14 labels, but several are empty or unlabelled in spirit: `growth`, `feedback`, `idea` and `discussion` have no descriptions at all. There are no labels for `tests`, `frontend`, `backend`, `security` or `performance`, which are exactly the categories the roadmap uses to help people find work that matches their skills.

## Why it matters

Labels are how a contributor answers "what can I do?". A contributor who knows Python but not CSS cannot filter for backend work today, so the tracker cannot route people to the work they can complete.

## Scope and suggested direction

Create the missing labels with clear, short descriptions and colours that fit the existing palette, then write the missing descriptions for `growth`, `feedback`, `idea` and `discussion`. Document the taxonomy in CONTRIBUTING.md so people know what each label means and how to use it to choose an issue. Reuse every existing label - do not rename or delete any, since open issues depend on them.

### Verified files

- `CONTRIBUTING.md`
- `docs/issue-roadmap.md`

## Acceptance criteria

- [ ] Labels exist for tests, frontend, backend, security and performance
- [ ] Every label has a description
- [ ] Existing labels are unchanged (none renamed or deleted)
- [ ] CONTRIBUTING.md documents how to use labels to pick an issue
- [ ] Labels are applied accurately to the curated roadmap issues

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="f2"></a>

#### F2 - Write a first-contributor guide walking through one real issue

`**Published as [#52](https://github.com/BistaDinesh03/critique/issues/52)**` | difficulty: **beginner** | labels: `documentation`, `good first issue`

## The problem

CONTRIBUTING.md covers setup, tests and PR expectations well, but it describes the process in the abstract. A first-time contributor still has to work out how to move from "I found an issue" to "my PR is open", including the fork-and-branch mechanics and how to run just the tests they touched.

## Why it matters

The gap between reading the guidelines and making the first change is where most potential contributors drop off. A concrete, worked example removes the guesswork and signals that beginners are genuinely welcome rather than merely tolerated.

## Scope and suggested direction

Add `docs/first-contributors.md` walking through one small, real issue from start to finish: claiming it in a comment, forking, creating a branch, making the change, running the relevant tests, and opening the pull request. Use commands that actually work in this repository, and link it from CONTRIBUTING.md and from the README's Contributing section. Keep it honest - do not promise review timelines the maintainer has not committed to.

### Verified files

- `CONTRIBUTING.md`
- `README.md`

## Acceptance criteria

- [ ] docs/first-contributors.md exists
- [ ] Every command in it has been run and verified locally
- [ ] It covers claiming, branching, testing and opening a PR
- [ ] It links from CONTRIBUTING.md and README
- [ ] It makes no promise about review speed or acceptance

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="f3"></a>

#### F3 - Define a triage policy and reconcile stale issues

`**Published as [#53](https://github.com/BistaDinesh03/critique/issues/53)**` | difficulty: **intermediate** | labels: `documentation`, `help wanted`

## The problem

The tracker has issues that no longer describe real work. Issue #2, "Add an easy way to share a Critique project", asks for a Share button, copy-confirmation, Web Share API with fallback and mobile support - all of which already exist in `static/share.js` (X, Reddit, copy link, copy post), with coverage in `test_project_share.py` and `test_share_analytics.py`. Nothing signals that the issue is already satisfied.

## Why it matters

Open issues that are already done waste contributor time and make the tracker look unmaintained. A written policy means the next such issue is handled the same way each time rather than by improvisation.

## Scope and suggested direction

Document a lightweight triage policy in CONTRIBUTING.md: how to mark an issue as already-implemented, how to spot duplicates, and what a stale issue should look like. Then apply it - starting with recommending that #2 be closed as completed. **Do not close or edit other people's issues yourself**; prepare the recommendation and let the maintainer act on it, since closing issues is the maintainer's call.

### Verified files

- `CONTRIBUTING.md`
- `docs/issue-roadmap.md`
- `static/share.js`
- `backend/tests/test_project_share.py`

## Acceptance criteria

- [ ] A triage policy is documented in CONTRIBUTING.md
- [ ] The policy covers duplicates, already-done issues and staleness
- [ ] Issue #2 is documented as already implemented, with file evidence
- [ ] No issue is closed, edited or deleted by this PR
- [ ] The policy is short enough that people will actually follow it

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="f4"></a>

#### F4 - Add a maintainer checklist for reviewing contributor pull requests

`**Published as [#54](https://github.com/BistaDinesh03/critique/issues/54)**` | difficulty: **intermediate** | labels: `documentation`, `help wanted`

## The problem

There is no guidance for reviewing. CONTRIBUTING.md tells contributors what to do but says nothing about what a maintainer checks, so review standards exist only in the maintainer's head and cannot be shared if the project grows beyond one reviewer.

## Why it matters

A checklist makes reviews consistent and faster, and it tells contributors up front what their PR will be judged on - which reduces round trips. It is also the natural place to record project-specific review knowledge, such as the fact that cache and security headers are invisible in manual testing and must be covered by tests.

## Scope and suggested direction

Add a maintainer section (in CONTRIBUTING.md or a short `docs/maintainer-guide.md`) covering the real checks this codebase needs: do tests cover the change, are new analytics events added to both allowlists, are security or cache headers asserted, is the data-model migration additive and safe on both SQLite and PostgreSQL, and does the change add a dependency that earns its place. Keep it specific to Critique rather than generic advice.

### Verified files

- `CONTRIBUTING.md`
- `backend/app/database.py`
- `backend/app/routes_analytics.py`

## Acceptance criteria

- [ ] A maintainer review checklist exists
- [ ] It references checks specific to this codebase
- [ ] It covers tests, analytics allowlists, migrations and dependencies
- [ ] It does not promise contributors anything the maintainer will not honour
- [ ] It is linked from CONTRIBUTING.md

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---


<a id="f5"></a>

#### F5 - Document the deployment and rollback process for maintainers

`**Published as [#55](https://github.com/BistaDinesh03/critique/issues/55)**` | difficulty: **intermediate** | labels: `documentation`

## The problem

`render.yaml` defines the production service and database, and the README summarises which secrets are entered manually in the Render dashboard. But there is no maintainer-facing documentation of how a deploy actually happens, what `init_db()`'s additive migrations do in production, or how to roll back if a deploy goes wrong.

## Why it matters

The startup path applies lightweight migrations to the production database on every boot. That is convenient, but it means a bad migration runs automatically - and right now nobody has written down what happens next or how to recover. For an open-source project this is exactly the knowledge that should not live in one person's head.

## Scope and suggested direction

Write `docs/deployment.md` for maintainers: what Render does on deploy, which environment variables must exist, what the additive migration step does to a live database, what is safe to change additively versus what is not, and how to roll back. Verify every claim against `render.yaml`, `database.py` and the live configuration rather than describing how you assume Render behaves. Do not include any real secret values, and do not change deployment configuration in this issue.

### Verified files

- `render.yaml`
- `backend/app/database.py`
- `README.md`
- `.env.example`

## Acceptance criteria

- [ ] docs/deployment.md exists
- [ ] Every statement is verified against render.yaml and database.py
- [ ] It explains the additive migration behaviour on a live database
- [ ] It describes a rollback path
- [ ] No secret value appears in the document
- [ ] No deployment configuration is changed

> **Before you start:** if the change touches behaviour, layout, or the data model, please describe your approach in a comment (or in [issue #1](https://github.com/BistaDinesh03/critique/issues/1)) first. Small, focused pull requests are much easier to review.


---

