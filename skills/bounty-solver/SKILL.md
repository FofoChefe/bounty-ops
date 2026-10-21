---
name: bounty-solver
description: >-
  Solves an AI-agent code bounty end to end, from reading the rubric to
  submitting a verified fix. Use when a qualified bounty needs to be
  attempted, a submission needs status polling, or a failed verification needs
  a retry. Covers the regression-test gate, the patch route versus the
  pull-request route, and the fork/branch/credential pitfalls that silently
  cost an attempt.
license: MIT
compatibility: >-
  Requires Python 3.8+ (standard library only) and, for the pull-request route, the GitHub CLI authenticated with repo scope.
  No external dependencies.
metadata:
  version: "1.0.0"
  author: Meridian Labs
  platforms: [linux, macos, windows]
  tags: [bounty, github, open-source, code-fix, pull-request, income]
  related_skills: [bounty-qualifier, bounty-solver, revenue-ledger]
---

# Bounty solver

Turns a funded GitHub issue into a submitted, verified fix that can be paid out.

## When to Use

- A qualified bounty needs to be attempted (see `bounty-qualifier` first).
- A submission needs status polling or a rejection-reason review.
- A retry is allowed and the previous attempt failed verification.

Do NOT use for: bounties whose repo has no test suite, docs/design bounties, or
any bounty whose rubric is not satisfiable by a code change.

## The gate that decides everything

Most platforms verify a submission by running the repo's own test suite plus a
**new regression test** that must fail before the fix and pass after. Three
consequences:

1. **No test suite means no payout.** If the repo has no tests, the platform
   cannot verify anything, and your fix — however correct — earns zero.
2. **The regression test is not optional.** Write it yourself, in the repo's
   own test style, asserting the exact behaviour the issue describes.
3. **The upstream suite must still pass.** A fix that breaks existing tests is
   worth zero. Run the full suite before you submit.

## Workflow

**1. Read the bounty and the rubric before any code.**

Fetch the detail, then read: the issue body, the acceptance criteria, the
evaluation rubric, the reward, the language, and the retry rules. If the
rubric asks for something a code change cannot deliver, **skip**. Do not
"attempt and see".

**2. Get the code.**

Platforms that mint clone URLs give you a read-only token that expires in about
an hour, and often work for private repos. Clone from the URL they give you,
not from a public fork — the private case has no public URL.

```bash
git clone <minted-clone-url> repo
```

**3. Reproduce the bug first.**

Write a failing test that captures the bug exactly as the issue describes it.
Run it. Watch it fail for the *right* reason. A fix without a reproducing test
is a guess, and a guess that "passes" the rubric by accident usually fails
sandbox verification anyway.

**4. Implement the smallest correct fix.**

- Fix the root cause, not the symptom.
- Match the repo's existing style, naming, error handling, and test conventions.
- No drive-by refactors, no formatting sweeps, no dependency bumps. Every
  unrelated line is another chance to break the suite.
- Add the regression test to the same test directory and framework the repo
  already uses.

**5. Verify locally, completely.**

Run the repo's full test suite, not just your new test. Run the linter and
type checker if the repo has them and CI runs them. A PR that breaks CI is
worth zero, and CI often runs more than your local command did.

**6. Submit.**

Two routes, in order of preference:

**Patch route (preferred).** Some platforms accept a unified diff directly and
apply it inside the same sandbox that verifies PR submissions. This removes
the entire fork/branch/PR failure surface — no fork, no branch-name collision,
no credential problems, no upstream push rights.

```bash
git diff main > fix.patch
curl -X POST <platform>/api/v1/submissions/patch \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"task_id":"...","agent_id":"...","result_text":"one-line summary","patch":"<diff>"}'
```

**PR route.** When the platform expects a pull-request URL.

```bash
gh repo fork <owner>/<repo> --clone=false
cd repo
git remote add fork https://github.com/<you>/<repo>.git
git checkout -b fix/<short-slug>
git add -A && git commit -m "fix(scope): <imperative summary>"
git push fork fix/<short-slug>
gh pr create --repo <owner>/<repo> --head <you>:<branch> \
  --title "fix(scope): <summary>" --body "<what broke, root cause, what changed, how you verified>"
```

**PR route pitfalls — each one costs a full attempt if missed:**

- **A branch name that collides with a directory in the repo is rejected at
  push time** with "directory file conflict". Git refuses to create
  `refs/heads/test/x` when `test/` is a tracked directory. Pick a prefix that
  is not a path in the repo (`fix/`, `chore/`, `smoke/`), and check the repo
  tree if unsure.
- **`gh pr create` against an upstream repo needs explicit targeting** when
  the fork is not your local origin: `--repo <owner>/<repo> --head <you>:<branch>`.
  Without `--head`, gh opens a PR from your default branch or errors.
- **A newly created remote repo is not connected to your local history** —
  `gh repo create` does not push. Push separately, and mind the default branch
  name (a fresh `git init` gives `master` while GitHub's new repos default to
  `main`).
- **`git push` hangs silently on a credential prompt** if the credential
  helper is not wired to your CLI. Set it up, and export
  `GIT_TERMINAL_PROMPT=0` in automation so a missing credential surfaces as an
  error instead of a hang.
- **Closing a PR does not delete the fork's branch.** Delete it explicitly.

**7. Poll, then record.**

Poll status at 30–60 second intervals, never tight-looped.

```
submitted → verifying → verified → creator selection → awarded
```

Record every attempt in the ledger (`revenue-ledger`), including the losses.
A rejected attempt is the highest-signal data you will get.

**8. Report honestly.**

Give the bounty id, reward, PR or patch URL, submission id, current status, and
expected payout. If a rejection comes back, quote the platform's written reason
verbatim — it tells you exactly what to fix next time.

## The competitive dynamic

Most boards award the **first passing submission**. Being second is worth zero.
So:

- **Speed beats quality on a contested bounty.** A good-enough PR that
  verifies first beats an excellent PR that lands second. Quality protects your
  *win rate*; speed protects the *payout*.
- **You usually get one attempt.** A retry is typically allowed only after a
  *failed verification verdict*, and only once. A pending result or a
  platform-side error does not consume it — but your own sloppy first attempt
  does. Test locally before submitting.
- **Neither side of the race is a guarantee.** Verify locally, submit fast, and
  keep the next candidate warm.

## Reporting a result

Realized revenue is what the ledger records as `awarded` — never the posted
value, never the expected value of anything in flight. A submitted bounty has
earned nothing until it is awarded and settled. When the feed is empty or every
attempt lost, say that plainly with the real numbers.

## Rules

- **Never open a PR without explicit user approval.** Show the diff and the PR
  body first.
- **Never spend money** (platform fees, x402 calls) without approval.
- **Never claim a bounty you did not solve.** A partial fix earns zero and
  costs a retry.
- **One submission per bounty.** Do not submit competing PRs for one issue.
- Respect platform rate limits, and their `Retry-After` header.
- If verification fails, read the failure output before resubmitting. Blind
  resubmission burns the retry and the fee.
