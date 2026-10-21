#!/usr/bin/env python3
"""
Bounty qualifier — score a feed of open bounties and print a ranked shortlist.

Read-only. Never submits, never spends, never touches an account.

Usage:
  python qualify.py feed.json          # from a file
  cat feed.json | python qualify.py    # from stdin

Input: a JSON array of bounty objects, or an object with a `data` / `items` /
`tasks` array. Each bounty may use any of these field names (all optional):

  id / task_id, title, reward_usd / reward / bounty_usd / amount_usd,
  language / lang, platform, repo, issue_url / github_url, url,
  entrants / submissions / attempts / solver_count,  # competition depth
  has_tests / test_suite / tests                        # verification
  type / task_type / complexity_tag

Output: a ranked table with the arithmetic, then the recommended action.
"""
import json
import os
import sys

# ---------------------------------------------------------------------------
# TUNING — edit these, don't pass flags. The thresholds live in one place so
# a change is auditable and consistent across every run.
# ---------------------------------------------------------------------------
MIN_NET_USD = 10.0        # minimum take-home (reward * WINNER_SHARE)
MIN_EV_USD = 10.0         # minimum expected value after effort cost
MAX_EFFORT_HOURS = 2.0    # first-attempt ceiling on an unfamiliar repo
DEFAULT_HOURS = 1.5       # assumed effort when the feed says nothing
HOURLY_FLOOR_USD = 15.0   # below this, the hour is worth more elsewhere
WINNER_SHARE = 0.80       # platform's cut is the rest
ASSUMED_COMPETITORS = 4   # when the feed publishes no competition depth
ASSUMED_HOURS = {
    "small": 0.75, "medium": 1.5, "large": 3.0, "xl": 6.0,
}
# ---------------------------------------------------------------------------

REQUIRED_TESTS = True    # skip bounties whose repo has no test suite


def _get(d, *names, default=None):
    for n in names:
        if isinstance(d, dict) and d.get(n) is not None:
            return d[n]
    return default


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def normalize(raw):
    """Map a bounty object onto a common shape. Tolerates missing fields."""
    reward = _num(_get(raw, "reward_usd", "reward", "bounty_usd", "amount_usd",
                        "bounty", default=0), 0.0)
    # some feeds quote cents
    if reward and reward < 1000 and _get(raw, "reward_usd") is None and \
            _get(raw, "bounty_cents") is not None:
        reward = reward / 100.0
    cents = _get(raw, "bounty_cents", "reward_cents")
    if cents is not None:
        reward = _num(cents, 0.0) / 100.0

    competitors = _get(raw, "entrants", "submissions", "attempts",
                        "solver_count", "competitors", default=None)
    competitors = int(_num(competitors, 0)) if competitors is not None else None

    complexity = str(_get(raw, "complexity_tag", "complexity", "size",
                          default="") or "").lower()
    hours = ASSUMED_HOURS.get(complexity, DEFAULT_HOURS)

    has_tests = _get(raw, "has_tests", "test_suite", "tests", default=None)
    if has_tests is None:
        has_tests = True  # unknown; treat optimistically, flag in output

    return {
        "id": str(_get(raw, "id", "task_id", default="?")),
        "title": str(_get(raw, "title", "summary", "name", default="(untitled)")),
        "reward": reward,
        "lang": str(_get(raw, "language", "lang", default="") or ""),
        "platform": str(_get(raw, "platform", default="github") or "github"),
        "repo": str(_get(raw, "repo", "repository", default="")),
        "url": str(_get(raw, "issue_url", "github_url", "url", default="")),
        "competitors": competitors,
        "hours": hours,
        "has_tests": bool(has_tests),
        "type": str(_get(raw, "type", "task_type", default="") or ""),
    }


def score(b):
    """Return (net, ev, win_prob, reasons). Reasons are disqualifiers."""
    reasons = []
    net = b["reward"] * WINNER_SHARE
    comps = b["competitors"]
    assumed = comps is None
    if assumed:
        comps = ASSUMED_COMPETITORS
    win_prob = 1.0 / (1.0 + comps)
    ev = net * win_prob

    if b["reward"] < MIN_NET_USD / WINNER_SHARE:
        reasons.append("reward below floor")
    if not b["has_tests"] and REQUIRED_TESTS:
        reasons.append("no test suite -> cannot prove the fix")
    if b["hours"] > MAX_EFFORT_HOURS:
        reasons.append("effort above ceiling")
    if ev < MIN_EV_USD:
        reasons.append("EV below floor")
    hourly = ev / b["hours"] if b["hours"] else 0.0
    if hourly < HOURLY_FLOOR_USD:
        reasons.append("hourly below floor")
    return net, ev, win_prob, reasons, comps, assumed, hourly


def load_feed(argv):
    if len(argv) > 1 and argv[1] not in ("-", "stdin"):
        path = argv[1]
        if not os.path.exists(path):
            print("feed file not found: %s" % path, file=sys.stderr)
            return None
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return json.load(f)
    raw = sys.stdin.read()
    if not raw.strip():
        return []
    return json.loads(raw)


def items_of(feed):
    if isinstance(feed, list):
        return feed
    if isinstance(feed, dict):
        for k in ("data", "items", "tasks", "bounties", "results"):
            v = feed.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict) and isinstance(v.get("items"), list):
                return v["items"]
        if "title" in feed:
            return [feed]
    return []


def main(argv):
    feed = load_feed(argv)
    if feed is None:
        return 2
    raw_items = items_of(feed)
    if not raw_items:
        print("No bounties in feed.")
        print("An empty board is normal, not an error. Nothing to qualify.")
        return 0

    scored = []
    for raw in raw_items:
        b = normalize(raw)
        net, ev, wp, reasons, comps, assumed, hourly = score(b)
        scored.append((len(reasons), -ev, b, net, ev, wp, reasons, comps,
                       assumed, hourly))

    scored.sort(key=lambda x: (x[0], x[1]))

    print("BOUNTY QUALIFIER")
    print("=" * 72)
    print("  %d bounty/bounties in feed" % len(scored))
    print("  floors: net >= US$%.0f | EV >= US$%.0f | effort <= %.1fh | "
          "hourly >= US$%.0f"
          % (MIN_NET_USD, MIN_EV_USD, MAX_EFFORT_HOURS, HOURLY_FLOOR_USD))
    print("=" * 72)

    recommended = []
    for i, (nreason, _negev, b, net, ev, wp, reasons, comps, assumed,
            hourly) in enumerate(scored, 1):
        tag = "GO" if not reasons else "SKIP"
        print()
        print("[%d] %-4s %s" % (i, tag, b["title"]))
        print("    id=%s  reward=US$%.2f  net=US$%.2f  lang=%s  type=%s"
              % (b["id"], b["reward"], net, b["lang"] or "?", b["type"] or "?"))
        ctxt = ("%d (assumed)" % comps) if assumed else str(comps)
        print("    competitors=%s  win_prob=%.0f%%  EV=US$%.2f  effort=%.1fh  "
              "hourly=US$%.2f" % (ctxt, wp * 100, ev, b["hours"], hourly))
        if b["repo"]:
            print("    repo=%s" % b["repo"])
        if b["url"]:
            print("    issue=%s" % b["url"])
        if reasons:
            print("    reasons: %s" % "; ".join(reasons))
        if not reasons:
            recommended.append((b, ev))

    print()
    print("=" * 72)
    if recommended:
        print("  RECOMMENDED: %d of %d" % (len(recommended), len(scored)))
        for b, ev in recommended:
            print("    %s  EV=US$%.2f  (%s)" % (b["id"], ev, b["title"][:50]))
        best = recommended[0]
        print()
        print("  Start with: %s" % best[0]["id"])
        print("  Then read the rubric before writing any code. If the rubric is")
        print("  not satisfiable by a code change, skip it anyway.")
    else:
        print("  RECOMMENDED: none. Every bounty in this feed fails a floor.")
        print("  That is a valid answer - the feed is not worth your time right now.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
