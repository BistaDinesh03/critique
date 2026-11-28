# Feedback submission reliability

This page describes how a feedback submission is expected to behave, what the
analytics events mean, and how to diagnose a production failure. It is the
reference for the reliability work tracked under Issue #86.

## Outcome taxonomy

A submission ends in exactly one of these states. Rows marked "Yes" are
failures; everything else is a completed or deliberately gated flow.

| Status | Meaning | What the visitor sees | Analytics event | Failure? |
|---|---|---|---|---|
| `201` | Response stored (guest or signed in) | Confirmation plus a next project to review | `feedback_submit` | No |
| `409` | This person (or this guest IP within the last hour) already answered | Calm "you already gave feedback" state, form closed | `feedback_already_responded` | No |
| `401` | Not used by the current API (guest submissions are allowed). Reserved for a future sign-in gate | Inline sign-in prompt, draft kept | none (the prompt emits `login_prompt_shown`) | No |
| `403` | CSRF token mismatch, or a project owner answering their own project | CSRF: one automatic retry, then "session expired, answers saved". Owner: the form is not offered | `feedback_submit_error` | Yes |
| `404` | Project or its active question disappeared | "This project is no longer accepting feedback", form closed | `feedback_submit_error` | Yes |
| `422` | Validation failed (bad enum, too long suggestion) | "Please check your answers and try again", draft kept | `feedback_submit_error` | Yes |
| `429` | `response_submit` rate limit (10 per 5 minutes per IP) | "You have submitted several responses recently. Try again in about N seconds", draft kept | `feedback_submit_error` | Yes (throttling, not a bug) |
| `5xx` | Server error | Generic "something went wrong on our side", draft kept | `feedback_submit_error` | Yes |
| network | Request never reached the server | "Network error, answers saved", draft kept | `feedback_submit_error` | Yes |

Raw backend `detail` strings are never rendered. A `500` detail is an internal,
and a `422` detail is a list of field errors; both are mapped to copy the
visitor can act on. The draft (answers plus suggestion) is saved on every
failure and on the sign-in gate, so a retry never starts from an empty form.

## Analytics event semantics

* `feedback_submit_attempt` — one user-initiated submission. A `403` that is
  retried once with a fresh CSRF token is still **one** attempt.
* `feedback_submit` — the server returned `201`.
* `feedback_already_responded` — the server returned `409`. This is a
  completed state, not an error, and is counted separately.
* `feedback_submit_error` — a real failure: `403`, `404`, `422`, `429`, `5xx`,
  or a network error.

As a result, attempts should roughly equal submits plus already-responded plus
errors (minus requests still in flight). A visitor who retries after a genuine
failure produces a new attempt, which is intended: the metric measures how
many times the button was used, not how many people were blocked.

## Diagnosing production failures

Analytics can only say *that* a submission failed, not why. Every submission
now writes one line to the `app.feedback` logger:

```
feedback_submit status=<code> request_id=<id>
```

The request id is the same `X-Request-ID` returned to the browser, so a
`feedback_submit_error` event can be matched to the server's status. The line
never contains the request body, email address, IP address, or written
suggestion.

To classify failures in a deployment's logs:

```
# status distribution for feedback submissions
grep 'feedback_submit status=' <logs> | sed 's/.*status=\([0-9]*\).*/\1/' | sort | uniq -c
```

`403` points at CSRF/session handling, `429` at rate limiting, `422` at a
client sending an invalid enum or an over-long suggestion, and `5xx` at a
server-side fault. The 33 historical errors cannot be reclassified from the
existing analytics alone; this log line is what makes the next period
diagnosable.

## Causes addressed in this change

1. **CSRF token rotated on every page load.** Loading any page in a second tab
   replaced the cookie that the first tab's form had read, so a legitimate
   submission could be rejected with `403`. Pages now reuse the existing token;
   rotation happens only at the authentication boundary (login/logout), where
   it protects against session fixation.
2. **Technical error text shown to visitors.** The raw `detail` (including
   `500` internals and `422` lists) was rendered. Failures now map to
   actionable copy.
3. **`429` was unhandled.** It fell into the generic branch with no wait time
   and invited a retry loop. The client now reads `Retry-After`, tells the
   visitor how long to wait, and keeps the draft.
4. **Double submissions while a request was in flight.** A second submit
   (including the post-sign-in resume) could POST the same answer twice. An
   in-flight guard now allows only one request at a time.
5. **No failure diagnostics.** The new `app.feedback` line makes the status
   classes countable in production.
6. **Duplicate-check race.** Two concurrent submissions could both pass the
   duplicate check before either inserted. The active question is now locked
   with `SELECT ... FOR UPDATE` for the check and insert, which serialises
   submissions on PostgreSQL.

## Known limitations

* **Guest to signed-in identity.** A guest response is stored with a null
  `user_id`, keyed for duplicate detection by an HMAC of the IP for one hour.
  If the same person later signs in, the server treats that as a different
  identity and cannot link the two. This change does not add that linkage.
* **No database uniqueness constraint.** There is no unique index on
  `(question_id, user_id)`. The row lock closes the concurrent-submission race
  on PostgreSQL, but a unique partial index would be the durable guarantee and
  is left as a follow-up migration.
* **Rate limiting is per process.** The in-memory limiter does not share
  counters between instances. This is pre-existing and unchanged.
* **Historical errors.** The breakdown of the 33 recorded errors requires the
  deployment logs. The new log line only covers submissions after it ships.

## Tests

* `backend/tests/test_feedback_flow.py` runs the real page JavaScript in the
  Node rendering harness and covers success, `401`, `403` retry, `409`, `404`,
  `422`, `429`, `5xx`, network failure, draft retention, and double submit.
* `backend/tests/test_csrf.py` covers token reuse across page loads and token
  rotation on login.
* `backend/tests/test_responses.py` covers guest submission and the
  `app.feedback` outcome line (including that it contains no personal data).
