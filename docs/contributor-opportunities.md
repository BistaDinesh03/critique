# Contributor Opportunities

This is a curated shortlist of work that looked available when last checked. It
is a starting point, not a reservation. Issue state changes quickly, so confirm
that an issue is open, unassigned, unclaimed in comments, and not attached to an
open pull request before you start.

**Last checked against the live tracker:** 2026-11-28.

- General guidelines: [CONTRIBUTING.md](../CONTRIBUTING.md)
- Step-by-step walkthrough: [first-contribution.md](first-contribution.md)
- Historical context only: [issue-roadmap.md](issue-roadmap.md)

## Start here

These issues are small, have a clear definition of done, and were open,
unassigned, and unclaimed when checked. Verify the live state before claiming.

| Issue | What you'll work on | Area |
|-------|---------------------|------|
| [#901](https://github.com/BistaDinesh03/critique/issues/901) | Make the feedback progress count only required questions | Frontend, feedback |
| [#903](https://github.com/BistaDinesh03/critique/issues/903) | Explain who sees written feedback in the form | Frontend, accessibility |
| [#869](https://github.com/BistaDinesh03/critique/issues/869) | Document `hide_answered` and `has_responded` in the API reference | Documentation |
| [#870](https://github.com/BistaDinesh03/critique/issues/870) | Give the generated badge SVG an accessible name | Accessibility, tests |
| [#871](https://github.com/BistaDinesh03/critique/issues/871) | Fix Discover project card heading hierarchy | Accessibility, frontend |
| [#875](https://github.com/BistaDinesh03/critique/issues/875) | Announce My Projects loading and error states | Accessibility, frontend |
| [#876](https://github.com/BistaDinesh03/critique/issues/876) | Add a copy-results-link action to the results page | Frontend |
| [#877](https://github.com/BistaDinesh03/critique/issues/877) | Explain the active `hide_answered` filter in the empty state | Frontend |

## More open work

These were also open and unassigned when checked, but they need more context or
touch more of the codebase. They are not first-task material.

| Issue | What you'll work on | Area |
|-------|---------------------|------|
| [#18](https://github.com/BistaDinesh03/critique/issues/18) | Add a question issue template that points to Discussions | GitHub templates |
| [#71](https://github.com/BistaDinesh03/critique/issues/71) | Make feedback counters consistent after project deletion | Backend |
| [#83](https://github.com/BistaDinesh03/critique/issues/83) | Use one shared client-IP helper | Backend |
| [#84](https://github.com/BistaDinesh03/critique/issues/84) | Purge expired email login tokens | Backend |
| [#104](https://github.com/BistaDinesh03/critique/issues/104) | Remove duplicated rules from `static/shared.css` | Frontend |
| [#105](https://github.com/BistaDinesh03/critique/issues/105) | Fix the orphaned native Share button | Frontend |
| [#150](https://github.com/BistaDinesh03/critique/issues/150) | Serve a branded HTML 500 page | Frontend |
| [#200](https://github.com/BistaDinesh03/critique/issues/200) | Add render coverage for Discover pagination | Tests |
| [#250](https://github.com/BistaDinesh03/critique/issues/250) | Isolate the backend test database per test | Tests |
| [#313](https://github.com/BistaDinesh03/critique/issues/313) | Share one navigation and `checkAuth()` implementation | Frontend |
| [#337](https://github.com/BistaDinesh03/critique/issues/337) | Associate validation errors with inputs via `aria-describedby` | Accessibility |
| [#524](https://github.com/BistaDinesh03/critique/issues/524) | Add Playwright smoke tests for critical flows | Tests |
| [#709](https://github.com/BistaDinesh03/critique/issues/709) | Add a cache for public project listings | Backend, performance |
| [#769](https://github.com/BistaDinesh03/critique/issues/769) | Add visual baselines for project detail and results | Tests |
| [#771](https://github.com/BistaDinesh03/critique/issues/771) | Test the footer GitHub star CTA on every page | Tests |

## Work in progress — please don't duplicate

Do not start these without asking on the issue first.

| Issue | Why it is not available |
|-------|-------------------------|
| [#909](https://github.com/BistaDinesh03/critique/issues/909) | Assigned to `henrivalle`, with open PR [#910](https://github.com/BistaDinesh03/critique/pull/910). |
| [#878](https://github.com/BistaDinesh03/critique/issues/878) | Open PR [#897](https://github.com/BistaDinesh03/critique/pull/897) addresses it. |
| [#722](https://github.com/BistaDinesh03/critique/issues/722) | Assigned, with open PR [#892](https://github.com/BistaDinesh03/critique/pull/892). |

## How to claim an issue

1. Confirm it is still open, unassigned, unclaimed, and has no open PR.
2. Comment on the issue and say you intend to work on it. That is the whole protocol.
3. Read [first-contribution.md](first-contribution.md).
4. Fork, branch, implement, and add or update tests where relevant.
5. Run the suite: `cd backend`, then
   `GITHUB_CLIENT_ID=ci-test-client-id python -m pytest tests/ -q`
   (PowerShell: set `$env:GITHUB_CLIENT_ID = "ci-test-client-id"` first).
6. Open a pull request describing what changed, why, and the exact tests you ran.

If you are unsure whether an approach is right, ask on the issue before writing code.
A short question costs a minute; a wrong-direction PR costs much longer.

## How this list is kept accurate

Use these live sources instead of trusting any frozen list:

- [`good first issue`](https://github.com/BistaDinesh03/critique/labels/good%20first%20issue)
- [`help wanted`](https://github.com/BistaDinesh03/critique/labels/help%20wanted)
- [`beginner`](https://github.com/BistaDinesh03/critique/labels/beginner)
- [all open issues](https://github.com/BistaDinesh03/critique/issues)
- [open pull requests](https://github.com/BistaDinesh03/critique/pulls)

An issue belongs in *Start here* or *More open work* only while it is open,
unassigned, not claimed in a comment, and not attached to an open pull request.
Issues are removed when they are claimed, fixed, duplicated, or blocked. If you
find a stale link here, report it in
[issue #1](https://github.com/BistaDinesh03/critique/issues/1) instead of editing
the list silently.
