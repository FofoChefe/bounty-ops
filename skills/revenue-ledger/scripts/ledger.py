#!/usr/bin/env python3
"""
Revenue ledger for agent bounty work.

Records attempts and payouts, and reports realized revenue honestly.
Read/write to a local JSON file. Never submits work, never spends money,
never contacts a platform.

Usage:
  python ledger.py add <task_id> <reward_usd> [status] [pr_url]
  python ledger.py close <task_id> <payout_usd> [status]
  python ledger.py list
  python ledger.py report

Environment:
  LEDGER_PATH   override the storage path
                (default: ~/.hermes/state/bounty_ledger.json)
"""
import json
import os
import sys
from datetime import date

WINNER_SHARE = 0.80
VALID_STATUS = ("submitted", "verifying", "verified", "awarded",
                "rejected", "expired")


def default_path():
    env = os.environ.get("LEDGER_PATH")
    if env:
        return env
    home = os.path.expanduser("~")
    for base in (os.path.join(home, ".hermes", "state"),
                 os.path.join(home, "AppData", "Local", "hermes", "state")):
        return os.path.join(base, "bounty_ledger.json")
    return os.path.join(home, ".bounty_ledger.json")


PATH = default_path()


def load():
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        d.setdefault("entries", [])
        d.setdefault("realized_usd", 0.0)
        return d
    except Exception:
        return {"entries": [], "realized_usd": 0.0}


def recalc(d):
    """Realized revenue is derived from awarded entries only. Never typed."""
    d["realized_usd"] = round(
        sum(float(e.get("payout_usd", 0.0)) for e in d["entries"]
            if e.get("status") == "awarded"), 2)
    return d


def save(d):
    recalc(d)
    parent = os.path.dirname(PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    os.replace(tmp, PATH)


def cmd_add(args):
    if len(args) < 2:
        print("add requires <task_id> <reward_usd> [status] [pr_url]")
        return 2
    task_id = args[0]
    try:
        reward = float(args[1])
    except ValueError:
        print("reward_usd must be a number")
        return 2
    status = args[2] if len(args) > 2 else "submitted"
    pr_url = args[3] if len(args) > 3 else ""
    if status not in VALID_STATUS:
        print("invalid status '%s' (valid: %s)" % (status, ", ".join(VALID_STATUS)))
        return 2

    d = load()
    if any(e.get("task_id") == task_id for e in d["entries"]):
        print("entry already exists for %s — use 'close' to update it, "
              "or 'close' with a new status to reclassify" % task_id)
        return 1

    payout = round(reward * WINNER_SHARE, 2) if status == "awarded" else 0.0
    d["entries"].append({
        "date": date.today().isoformat(),
        "task_id": task_id,
        "reward_usd": reward,
        "payout_usd": payout,
        "status": status,
        "pr_url": pr_url,
        "note": "",
    })
    save(d)
    print("recorded %s: reward US$%.2f -> payout US$%.2f (%s)"
          % (task_id, reward, payout, status))
    return 0


def cmd_close(args):
    if len(args) < 2:
        print("close requires <task_id> <payout_usd> [status]")
        return 2
    task_id = args[0]
    try:
        payout = float(args[1])
    except ValueError:
        print("payout_usd must be a number")
        return 2
    status = args[2] if len(args) > 2 else "awarded"
    if status not in VALID_STATUS:
        print("invalid status '%s' (valid: %s)" % (status, ", ".join(VALID_STATUS)))
        return 2

    d = load()
    hit = None
    for e in d["entries"]:
        if e.get("task_id") == task_id:
            hit = e
            break
    if not hit:
        print("no entry for %s" % task_id)
        return 1
    hit["payout_usd"] = payout
    hit["status"] = status
    hit["date"] = date.today().isoformat()
    save(d)
    print("closed %s: US$%.2f (%s)" % (task_id, payout, status))
    return 0


def cmd_list(_args):
    d = load()
    entries = d["entries"]
    if not entries:
        print("(no entries)")
        return 0
    for e in entries:
        print("%s  %-14s reward US$%-8.2f payout US$%-8.2f %-10s %s" % (
            e.get("date", "?"), e.get("task_id", "?"),
            e.get("reward_usd", 0), e.get("payout_usd", 0),
            e.get("status", "?"), e.get("pr_url", "")))
    return 0


def cmd_report(_args):
    d = load()
    entries = d["entries"]
    print("REVENUE REPORT")
    print("=" * 48)
    if not entries:
        print("  No attempts recorded yet.")
        print("  REALIZED REVENUE   US$0.00")
        print("=" * 48)
        print("  Zero realized revenue is the normal state before the first")
        print("  attempt. Report it plainly; do not substitute posted value.")
        return 0

    by = {}
    for e in entries:
        by.setdefault(e.get("status", "?"), []).append(e)

    for st in VALID_STATUS:
        if st in by:
            amt = sum(x.get("payout_usd", 0) for x in by[st])
            print("  %-10s %3d   US$%8.2f" % (st, len(by[st]), amt))

    awarded = by.get("awarded", [])
    rejected = len(by.get("rejected", [])) + len(by.get("expired", []))
    inflight = sum(len(v) for k, v in by.items()
                   if k in ("submitted", "verifying", "verified"))
    posted = round(sum(e.get("reward_usd", 0) for e in entries), 2)
    realized = round(sum(e.get("payout_usd", 0) for e in awarded), 2)
    decided = len(awarded) + rejected
    rate = (len(awarded) / decided * 100) if decided else 0.0

    print("-" * 48)
    print("  attempts            %d" % len(entries))
    print("  posted value        US$%.2f   (NOT revenue)" % posted)
    print("  in flight           %d   (NOT revenue)" % inflight)
    print("  awarded             %d" % len(awarded))
    print("  rejected/expired    %d" % rejected)
    print("  win rate            %.0f%%   (%d decided)" % (rate, decided))
    print("  REALIZED REVENUE    US$%.2f" % realized)
    if entries:
        print("  per attempt         US$%.2f" % (realized / len(entries)))
        if awarded:
            print("  per win             US$%.2f" % (realized / len(awarded)))
    print("=" * 48)
    if not awarded:
        print("  Nothing has paid out yet. A submitted bounty is worth zero")
        print("  until it is awarded AND settled. Say that plainly.")
    return 0


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd, args = argv[1], argv[2:]
    table = {"add": cmd_add, "close": cmd_close, "list": cmd_list,
             "report": cmd_report}
    fn = table.get(cmd)
    if not fn:
        print(__doc__)
        return 2
    return fn(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
