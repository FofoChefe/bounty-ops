# Bounty Ops — a skill pack for AI agents that earn money on code bounties

Three skills that turn "I found a bounty online" into "money verified in the
ledger", with the bad decisions blocked before they cost time.

Open `agentskills.io` format — installable in Hermes, Claude Code, Codex,
Cursor, OpenClaw, and any runtime that supports the standard.

Python 3.8+ standard library only. No dependencies, no API keys, nothing to
pip install. 44 tests pass.

---

## The problem this pack solves

Bounty agents fail in predictable ways, and almost always through process
error rather than missing capability:

1. **They work bounties without computing expected value.** A US$42 bounty
   contested by four solvers yields US$8 — less than an hour of anything
   else. The agent only discovers this after spending two hours.
2. **They learn "no test suite means no payout" too late.** Platforms require a
   new regression test. A repo with no test suite is unpayable, no matter how
   good the fix.
3. **They lose attempts to plumbing.** A branch name that collides with a
   directory, a push that hangs on an invisible credential prompt, a
   `gh pr create` that opens the wrong branch. Each one costs the whole
   attempt.
4. **They report posted value as if it were revenue.** A submitted bounty has
   paid nothing. Conflating the two is how agent pipelines turn into fiction —
   and it is exactly what stops the owner from deciding whether to fund it
   further.

This pack attacks all four, in order: qualify before acting, execute without
losing an attempt, and report the truth.

---

## The skills

### `bounty-qualifier` — decides what is worth doing

Turns a feed of bounties into a ranked shortlist with the arithmetic visible.

```
EV = (net_reward x win_probability) - effort_cost
win_probability ~= 1 / (1 + competitors)
```

Configurable floors: minimum reward, minimum EV, effort ceiling, hourly-value
floor, and the filter that matters most — **a repository with no test suite is
discarded**, because there is no way to prove the fix.

What it teaches that no script can:

- **A contested bounty is a race, not a queue.** "First passing submission
  wins" means second place is worth zero. Speed beats quality on the payout;
  quality protects the win rate. Those are different things.
- **You usually get one attempt.** A retry is typically allowed only after a
  *failed verification verdict*, and only once. A sloppy first attempt burns
  the retry.
- **Registration is not eligibility.** A saved payout address is not a
  transfer. A board can be entirely honest and still be a bad investment if
  the payout route is unconfirmed.
- **Breadth versus depth.** Breadth (many cheap bounties) scales linearly and
  only works if submissions are free. Depth (few, expensive ones) has higher
  EV but depends on winning contests. Most agents should start with breadth to
  build a win rate, then shift to depth. Grinding hard contests from a cold
  profile is the most common way to end up with a portfolio of failures and no
  reputation.

### `bounty-solver` — executes without losing an attempt

The full workflow, from reading the bounty to submitting the claim, with the
pitfalls that only show up in practice:

- The **patch route** (`POST /submissions/patch`) is preferable to the PR
  route — it removes the entire fork/branch/push failure surface.
- When the platform expects a pull request: a branch that collides with a
  directory in the repo is **rejected at push time** ("directory file
  conflict"). `gh pr create` against an upstream repo needs explicit `--repo`
  and `--head`. `gh repo create` does not push. `git push` hangs silently on a
  credential prompt if the helper is not wired to your CLI.
- **The regression test is mandatory and must fail before the fix.**
- **The existing suite must keep passing.** A PR that breaks CI is worth zero.
- Read the rubric before you start. If it is not satisfiable by a code change,
  skip it.
- Never submit twice carelessly — the retry is your only safety net.

### `revenue-ledger` — report the truth

Four numbers, and only one of them is revenue:

| Number | What it is | Revenue? |
|---|---|---|
| Posted value | Sum of every bounty amount attempted | No |
| Expected value | Probability-weighted estimate | No |
| Pending | Submitted, not verified or awarded | No |
| **Realized** | **Awarded and paid out** | **Yes** |

Accounting rules: only `awarded` counts; the platform's cut is deducted; one
entry per bounty (a retry updates the entry, it does not duplicate it); losses
are never deleted; the total is always derived from the entries, never typed.

The report gives attempts, posted value, in-flight count, awards, rejections,
win rate over **decided** attempts, realized revenue, and revenue per attempt.

---

## Installation

**Hermes (or any agentskills.io-compatible runtime):**

```bash
hermes skills tap add FofoChefe/bounty-ops
hermes skills install FofoChefe/bounty-ops/bounty-qualifier
hermes skills install FofoChefe/bounty-ops/bounty-solver
hermes skills install FofoChefe/bounty-ops/revenue-ledger
```

**Claude Code / Codex / Cursor / Aider:**

```bash
npx skills add FofoChefe/bounty-ops
```

**No install, straight from source:** copy `skills/<name>/` into your runtime's
skills directory. Each skill is a `SKILL.md` plus scripts, with no external
dependencies — Python 3 standard library only.

---

## Requirements

- Python 3.8+ (standard library only — nothing to install)
- For `bounty-solver`: `gh` authenticated, and a GitHub client with `repo`
  scope. The account that opens the pull request must be the same account
  signed in to the bounty platform, or the payout will not be released.
- No skill submits work, spends money, or touches an account without explicit
  approval.

---

## Tests

```bash
python test_pack.py
```

44 tests covering: normalization of feeds with differing field names, the EV
arithmetic, every disqualification gate, and the ledger's accounting (80%
payout, retries without duplication, recomputed totals, atomic writes).

---

## License

Two layers, deliberately:

- **Code** (the Python scripts, `test_pack.py`, `normalize_frontmatter.py`) —
  MIT. See [`LICENSE`](LICENSE). Use it however you like, including inside a
  product you sell.
- **Skill content** (the `SKILL.md` files — the workflows, the pitfalls, the
  accounting rules) — CC BY-NC 4.0. See [`skills/LICENSE`](skills/LICENSE).
  Free for personal use, study, and redistribution. **Non-commercial.**

**Commercial use of the skill content** — running these skills inside an agent
operation you sell to clients, or shipping them inside a product or service —
requires a commercial license (US$29, includes 12 months of updates). Contact:
bozohitzz@gmail.com

**Buy the commercial license:** https://buy.stripe.com/fZucMXgKEaPf6V5bx9efC01

Checkout is processed by Stripe. After payment, email the address you used and
the commercial license plus 12 months of updates are sent over. The public
repository stays free for personal use — what you are buying is the commercial
right and the support.

Managed agent operations (US$490/month equivalent, R$490/month in BRL):
https://buy.stripe.com/9B6cMXeCw5uV6V50SvefC02

---

## Why this pack exists

Every instruction here came from running the pipeline on a real machine: fork
→ branch → commit → push → PR → close, with three bugs that only appeared on
the way. The pitfalls are documented because someone has already paid for them.
