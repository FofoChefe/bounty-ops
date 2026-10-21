---
name: bounty-qualifier
description: "Qualifies open AI-agent code bounties by expected value before any effort is spent. Use when a bounty feed returns options and you need to pick one, compare boards on a single value scale, or decide whether a board is worth continuing. Computes EV = (net_reward x win_probability) - effort_cost, discards repos with no test suite because they cannot be paid out, and shows the arithmetic behind every skip."
license: MIT
compatibility: "Requires Python 3.8+ (standard library only). No network access and no external dependencies."
metadata:
  version: "1.0.0"
  author: "Meridian Labs"
  platforms: [linux, macos, windows]
  tags: [bounty, triage, expected-value, taskbounty, automation, open-source]
  related_skills: [bounty-qualifier, bounty-solver, revenue-ledger]
---

# Bounty qualifier

Decides which open bounties are worth touching, before any effort is spent. Most
public bounty boards are mostly not worth working. A qualifier that says "skip"
saves more time than a solver that says "go".

## When to Use

- A bounty feed returns a list and you need to pick one.
- You want to compare several platforms' boards on one expected-value scale.
- A previous attempt lost, and you need to know whether the next one is better.
- Before writing any code for a bounty: qualify it first.

Do NOT use for: bounties you already claimed, or to decide pricing for a bounty
you are *funding* rather than solving.

## The three numbers that decide it

**1. Gross reward.** What the poster put up. The winner usually takes 80%; the
platform keeps the rest. Net = reward × 0.80 unless the platform says otherwise.

**2. Contest depth.** How many other solvers will attempt it. This is the number
that kills most bounties. Platforms increasingly publish a "N solvers attempting"
count — if you have it, use it. If you don't, assume **4** for a popular repo
and **2** for an obscure one. That is not a guess you can avoid: it is the number
you have to live with.

**3. Verification cost.** Whether the work is provable automatically. This is
the highest-leverage filter and the one people skip.

| Work type | Auto-verifiable? | Treat as |
|---|---|---|
| JS/TS with an existing test suite | Yes, sandboxed | Best case |
| Any language with a test suite | Usually | Good |
| Coverage-uplift task | Yes, measurable | Good |
| No test suite in the repo | No | Skip — you cannot prove the fix |
| Design / docs / content | Human judgment | Skip for automation |

A repo with **no test suite** cannot produce a passing regression test. If the
platform requires one, the bounty is unearnable by an automated agent no matter
how good the fix is. Check for this before reading the issue body.

## Expected value

```
EV = (net_reward × win_probability) − effort_cost
```

Where `win_probability ≈ 1 / (1 + competitors)`.

With 4 competitors and a US$50 bounty:
```
net = 50 × 0.80 = 40
EV = (40 × 1/5) − effort = 8 − effort
```

That is **US$8 before you spend a minute**. A two-hour job has an hourly rate
below minimum wage. This is the arithmetic that decides it, and it is why
contested bounties are not worth it.

**Skip when EV < US$10**, or when EV/hour falls below what the same hour would
earn elsewhere. Raise the bar when you are building a track record on a new
profile; lower it when you already have wins and want volume.

## Contested bounties: race, don't queue

On boards where *"the first passing submission wins"*, being second is worth
zero. Two consequences most solvers miss:

- **Speed beats quality** on a contested bounty. A mediocre PR that verifies
  first beats an excellent PR that lands second. Quality is what protects the
  *win rate*; speed protects the *payout*.
- **A single attempt is often all you get.** Most platforms allow a retry only
  after a *failed verification verdict*, and only once. A pending result or a
  platform-side infra error does not consume the retry — but your own sloppy
  first attempt does. Test locally before submitting.

Both of these mean: **parallelize your attempt, but never submit twice carelessly.**

## Qualifier checklist

Run through in order and stop at the first fail:

1. **Reward floor** — is the net (reward × 0.80) above your minimum?
2. **Language** — do you know it well enough to write a regression test?
3. **Test suite present?** — if no, skip.
4. **Scope** — is it a single localized defect, or a redesign? Redesigns lose.
5. **Competition** — how many solvers? If unknown, assume pessimistic.
6. **Submission route** — can you submit a patch instead of opening a PR?
   A patch route removes the entire fork/branch/PR failure surface.
7. **Payout route confirmed?** — a bounty you cannot be paid for is a hobby.
8. **Effort estimate** — under 2 hours for a first attempt on an unfamiliar repo.
9. **Retry rules** — read them before you start, not after you fail.

## The platform trap

Different boards publish different economics. Never assume the 80/20 split or
the $10 floor carries over. Before working a board, confirm:

- what share the winner actually receives
- the minimum reward and whether the board filters by it
- the verification method and what it requires of the PR
- whether a retry is allowed, and when
- **how a solver actually gets paid, and whether that route is confirmed** —
  registration is not eligibility, and a saved address is not a transfer

That last point is the one that quietly strands earnings. A board can be
perfectly honest and still be a bad investment if the payout path is
unconfirmed.

## Depth vs breadth

Two ways to earn on a board, with opposite economics:

- **Breadth** (many low-value bounties): works only if submissions are cheap
  and the platform charges nothing per attempt. Scales linearly, and is
  exposed to verification cost per attempt.
- **Depth** (few high-value bounties): higher EV per bounty, but slower to
  compound and dependent on your ability to win contested ones.

Most agents should start with breadth to build a win rate, then shift to depth.
Doing the opposite — grinding hard contests from a cold profile — is the most
common way to end with a portfolio of failures and no reputation.

## What to record

Qualification is worthless if you don't log it. For every bounty you consider
— including the ones you skip — record the reward, the competition, and the
reason. Over time this becomes the only honest answer to "which board is worth
my time", and it turns a hunch into a measurement.

The `revenue-ledger` companion skill records attempts and payouts.

## Tools

`scripts/qualify.py` — scores a feed against configurable floors and prints the
ranked shortlist with the arithmetic shown. Edit the constants at the top rather
than passing flags, so the thresholds live in one place.

```bash
python scripts/qualify.py feed.json
```

`scripts/qualify.py` with no arguments reads a JSON feed from stdin. It never
submits anything and never spends money — it is a decision aid only.
