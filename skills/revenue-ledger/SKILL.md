---
name: revenue-ledger
description: "Tracks what bounty or agent work actually earned, and refuses to confuse posted value with money in hand. Use when recording a bounty attempt, reporting revenue to anyone, or deciding whether to keep spending time on a board. Separates posted value, expected value, pending, and realized revenue, and reports win rate over decided attempts rather than all attempts."
license: MIT
compatibility: "Requires Python 3.8+ (standard library only). Stores a plain JSON ledger under ~/.hermes/state/. No network access."
metadata:
  version: "1.0.0"
  author: "Meridian Labs"
  platforms: [linux, macos, windows]
  tags: [bounty, revenue, ledger, accounting, reporting, income]
  related_skills: [bounty-qualifier, bounty-solver, revenue-ledger]
---

# Revenue ledger

Records what an agent activity actually earned, and refuses to confuse posted
value with money in hand. A pipeline that has produced nothing must be able to
say so plainly.

## When to Use

- After attempting a bounty, to record the attempt and its outcome.
- When reporting revenue to anyone — including yourself.
- Before deciding whether to keep spending time on a board or a strategy.
- When an earnings claim needs to be backed by a number rather than a feeling.

Do NOT use for: one-off personal bookkeeping, or invoicing (that is a tool
skill, not this one).

## The rule that matters

**Realized revenue is cash that landed. Nothing else is revenue.**

These are four different numbers and conflating them is how agent projects
report fantasy:

| Number | What it is | Is it revenue? |
|---|---|---|
| Posted value | Sum of every bounty amount you attempted | No |
| Expected value | Probability-weighted estimate of what you might get | No |
| Pending | Submitted, not yet verified or awarded | No |
| **Realized** | **Awarded and paid out** | **Yes** |

A bounty that is submitted but not verified has earned **zero**. A bounty that
is verified but not selected has earned **zero**. Report the last row only.

## Accounting rules

1. **The platform's cut is not yours.** A US$50 bounty at an 80/20 split pays
   US$40. The ledger records the *take-home*, not the headline.
2. **Record the attempt, not just the win.** A ledger with only successes is
   marketing, not accounting. Every attempt gets an entry, with a status.
3. **Status drives the money.** Only `awarded` counts toward realized revenue.
   `submitted`, `verifying`, `verified`, `rejected`, `expired` do not.
4. **One entry per bounty.** If you retry, update the entry — do not add a
   second one. Double-counting retries is the most common way to inflate
   revenue in an agent ledger.
5. **Never delete a loss.** Rejected attempts are the highest-signal data you
   have: they tell you which boards, languages, or scopes to avoid.
6. **The total is derived, never typed.** Compute realized revenue from the
   entries on every write, so an edit can never leave a stale total behind.

## Statuses

```
submitted  → work handed in, nothing decided
verifying  → platform is running the sandbox
verified   → passed verification, awaiting selection
awarded    → creator selected you; payout queued or sent
rejected   → verification failed, or another solver won
expired    → the bounty closed before a decision
```

Move forward with `close`; do not rewrite history with `add`.

## Workflow

**1. Record the attempt immediately after submitting.**

```bash
python scripts/ledger.py add <task_id> <reward_usd> submitted <pr_url>
```

Recording late is how attempts go missing, and a missing attempt silently
inflates your per-attempt average.

**2. Poll for the outcome, then close it.**

```bash
python scripts/ledger.py close <task_id> <payout_usd> awarded
python scripts/ledger.py close <task_id> 0 rejected
```

Pass the *actual* payout for `awarded` — the platform's real number, not your
estimate of 80%. If it differs from 80%, the difference is fees, and your
effective rate just got more accurate.

**3. Report.**

```bash
python scripts/ledger.py report
```

The report gives attempts, posted value, in-flight count, awards, rejections,
win rate, realized revenue, and revenue per attempt. That is the whole truth
in one screen.

**4. Review before you commit more time.**

```bash
python scripts/ledger.py list
```

Look for the pattern: a board with a 10% win rate is not a board, and
re-evaluating it is worth more than the next three attempts.

## Reporting to others

State the realized number first, then the context. Do not lead with posted
value.

> Realized revenue so far: **US$0.00** across 0 attempts. 3 attempts are in
> flight. The feed has been empty for the last two days.

If that is the truth, say it. An optimistic summary of a pipeline that has
produced nothing is worse than useless, because it stops the owner from making
a rational decision about whether to fund it further.

## Interpreting a win rate

Win rate is only meaningful with the denominator visible. Always report
`wins / decided` — not `wins / attempts` — because attempts still in flight
are not losses, and counting them as losses makes a healthy pipeline look
broken. The report separates them for exactly this reason.

A low win rate with a high reward is a different business than a high win
rate with a low reward. The report's revenue-per-attempt line is the number
that compares them honestly.

## Storage

`~/.hermes/state/bounty_ledger.json` by default, overridable with
`LEDGER_PATH`. Writes are atomic (temp file plus rename) so a crash mid-write
cannot corrupt the file. The ledger is plain JSON — readable, diffable, and
easy to move into whatever reporting you use.

## Tools

```bash
python scripts/ledger.py add <task_id> <reward_usd> [status] [pr_url]
python scripts/ledger.py close <task_id> <payout_usd> [status]
python scripts/ledger.py list
python scripts/ledger.py report
```

`add` with status `awarded` auto-credits 80% of the reward. `add` with any
other status credits nothing. The script never submits work, never spends
money, and never contacts a platform.
