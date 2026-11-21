# Maintainer Welcome Guide

This guide explains how to welcome new contributors to Critique in a
constructive, friendly, and effective way. The goal is to make first-time
contributors feel valued, supported, and motivated to contribute again.

## When Someone Expresses Interest

### 1. Acknowledge their comment promptly
When a commentator writes "I'd like to work on this" or "I plan to..." on an
issue, respond within 24–48 hours. A simple acknowledgment goes a long way.

**Example response:**

```
Hi @contributor-name, thank you for saying you'd like to work on this! I'm
excited to have your help. Before you get started, could you briefly outline
your approach so I can take a look and offer any early feedback? No pressure
to have a perfect plan — just a rough idea helps avoid duplicated effort.
```

### 2. Help clarify the issue if needed
If the issue is vague or large, guide the contributor toward a scoped first
contribution.

**Example response:**

```
Thanks for volunteering! This issue is quite broad — would you like to
split it into a smaller, well-defined first contribution? For example, we
could start with just the [first acceptance criterion] and iterate from
there. Many contributors find a small, mergeable first PR is the fastest
way to get comfortable with the codebase.
```

## Reviewing a First Pull Request

### 3. Assume good intentions
Read the contributor's code and comments with the benefit of the doubt.
Remember that this is likely their first contribution to the project.

### 4. Be constructive with feedback
Frame changes as improvements rather than flaws. Use "you" sparingly and
focus on the code, not the contributor.

**Example feedback style:**

```
Thanks for the PR! I love the overall approach. One suggestion: the error
message could be more specific about what format is expected. Would you
consider updating the message to say "Expected a 4-digit year, got: {value}"?
This way, users immediately know what went wrong.

If you'd like, I can walk through how to add the message — no worry if this
is your first time touching this part of the code.
```

### 5. Explain requested changes clearly
When requesting changes, explain *why* the change matters and provide
guidance on how to implement it.

**Example:**

```
The PR touches the form validation, which is a great area for a first
contribution. However, the current change doesn't persist the error message
after page reload. To make the feedback permanent, you'll need to save the
error to localStorage (or the backend). Here's a quick pattern:

```javascript
// Save to localStorage on blur
input.addEventListener('blur', () => {
  localStorage.setItem('formError', errorMsg);
});
```

This way, the error survives a page refresh, which is one of the acceptance
criteria.
```

### 6. Thank contributors before the merge is confirmed
Never thank a contributor before `finalize --merge` confirms the merge.
However, you can express appreciation for their effort regardless of the
outcome.

**Example:**

```
This is a wonderful first contribution — thank you for taking the time to
submit your first PR! Even if we need some adjustments, your effort is
genuinely appreciated and valued.
```

## Encouraging Another Contribution Without Pressuring

### 7. Close the loop
Once a PR is merged, close the associated issue and post a thank-you comment.

**Example thank-you comment (post-merge):**

```
PR merged! 🎉 Thank you @contributor-name for your first contribution to
Critique. Your change [summary] is now live. We appreciate your help making
the project better, and we'd love to have you back for another contribution
whenever you're ready — no pressure at all.
```

### 8. Invite future contributions gently
If the first contribution went well, invite the contributor to look for
another issue. If it didn't go well, still thank them for their time and
leave the door open.

**Example invitation (after a PR with changes requested):**

```
Thanks for your work on this! We've requested a few adjustments to match
the project's style. No worry at all — take your time, and when you're
ready, we'll review the updates. We'd love to have you contribute again
in the future.

In the meantime, feel free to browse other [good first issue] labels or
ask any questions in [issue #1].
```

### 9. Never pressure for a second contribution
Always leave the door open without expectation. Some contributors make one
great contribution and move on — that's perfectly fine.

## Maintainer Tips

- **Reply to every first-timer:** Even a short "thanks for trying!" matters.
- **Use welcoming language:** "Welcome!", "Thanks for!", "Your contribution
  is appreciated!" — these phrases reinforce that the community is glad they
  are here.
- **Pair new contributors with experienced ones:** If available, assign a
  mentor or ask a long-time contributor to briefly review the PR alongside
  the maintainer.
- **Track contributor sentiment:** If a first-timer expresses frustration
  or confusion, flag it so the onboarding documentation can be improved.
- **Celebrate milestones:** When a contributor hits their second or third
  merge, acknowledge it publicly (with their permission) to reinforce the
  welcome cycle.