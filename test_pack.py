"""Tests for the bounty pack: qualifier scoring and ledger accounting.

Run: python test_pack.py
Covers both scripts via import, with isolated state.
"""
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FAIL = []


def check(name, cond, detail=""):
    if cond:
        print("PASS  %s" % name)
    else:
        print("FAIL  %s  %s" % (name, detail))
        FAIL.append(name)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


Q = load(os.path.join(HERE, "skills", "bounty-qualifier", "scripts", "qualify.py"), "qualify")
L = load(os.path.join(HERE, "skills", "revenue-ledger", "scripts", "ledger.py"), "ledger")
L.PATH = os.path.join(tempfile.mkdtemp(), "bounty_ledger.json")


# ===========================================================================
# QUALIFIER
# ===========================================================================
print("--- qualifier ---")

# field normalization across the shapes different feeds use
b = Q.normalize({"id": "t1", "title": "Fix pagination", "language": "typescript",
                 "reward_usd": 50, "entrants": 2, "has_tests": True})
check("normalize: standard shape", b["id"] == "t1" and b["reward"] == 50.0
      and b["competitors"] == 2 and b["lang"] == "typescript", repr(b))

b = Q.normalize({"task_id": "t2", "summary": "s", "lang": "python",
                 "reward": 30, "submissions": 1, "test_suite": True})
check("normalize: alternate names", b["id"] == "t2" and b["reward"] == 30.0
      and b["competitors"] == 1, repr(b))

b = Q.normalize({"id": "t3", "bounty_cents": 5000, "title": "x"})
check("normalize: cents converted", b["reward"] == 50.0, repr(b))

b = Q.normalize({"id": "t4", "title": "x", "reward_usd": 50})
check("normalize: competitors default None", b["competitors"] is None, repr(b))

# EV math
b = Q.normalize({"id": "t5", "reward_usd": 50, "entrants": 0, "has_tests": True,
                 "complexity_tag": "small"})
net, ev, wp, reasons, comps, assumed, hourly = Q.score(b)
check("EV: no competitors -> win_prob 1.0", abs(wp - 1.0) < 1e-9, repr(wp))
check("EV: net is 80%", abs(net - 40.0) < 1e-9, repr(net))
check("EV: equals net when uncontested", abs(ev - 40.0) < 1e-9, repr(ev))
check("EV: no disqualifiers for a good bounty", reasons == [], repr(reasons))

b = Q.normalize({"id": "t6", "reward_usd": 50, "entrants": 4, "has_tests": True,
                 "complexity_tag": "small"})
net, ev, wp, reasons, comps, assumed, hourly = Q.score(b)
check("EV: 4 competitors -> win_prob 0.2", abs(wp - 0.2) < 1e-9, repr(wp))
check("EV: contested EV is 8", abs(ev - 8.0) < 1e-9, repr(ev))
check("EV: contested bounty is skipped", any("EV below floor" in r for r in reasons),
      repr(reasons))

# disqualifiers
b = Q.normalize({"id": "t7", "reward_usd": 5, "entrants": 0, "has_tests": True})
_, _, _, reasons, _, _, _ = Q.score(b)
check("gate: tiny reward skipped", len(reasons) > 0, repr(reasons))

b = Q.normalize({"id": "t8", "reward_usd": 100, "entrants": 0, "has_tests": False})
_, _, _, reasons, _, _, _ = Q.score(b)
check("gate: no test suite skipped",
      any("no test suite" in r for r in reasons), repr(reasons))

b = Q.normalize({"id": "t9", "reward_usd": 100, "entrants": 0, "has_tests": True,
                 "complexity_tag": "xl"})
_, _, _, reasons, _, _, _ = Q.score(b)
check("gate: oversized effort skipped", len(reasons) > 0, repr(reasons))

# assumed competitors applied when unknown
b = Q.normalize({"id": "t10", "reward_usd": 50, "has_tests": True,
                 "complexity_tag": "small"})
net, ev, wp, reasons, comps, assumed, hourly = Q.score(b)
check("assumed competitors flagged", assumed is True and comps == Q.ASSUMED_COMPETITORS,
      repr((comps, assumed)))

# feed shapes
check("feed: plain list", len(Q.items_of([{"id": "a"}])) == 1)
check("feed: data key", len(Q.items_of({"data": [{"id": "a"}, {"id": "b"}]})) == 2)
check("feed: items key", len(Q.items_of({"items": [{"id": "a"}]})) == 1)
check("feed: single object", len(Q.items_of({"id": "a", "title": "t"})) == 1)

# end-to-end output
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = Q.main(["qualify.py"])
out = buf.getvalue()
check("qualifier: empty feed handled", "No bounties in feed" in out, out[:120])
check("qualifier: empty feed exits 0", rc == 0)

feed = {"data": [
    {"id": "good", "title": "Good bounty", "reward_usd": 200, "entrants": 0,
     "has_tests": True, "complexity_tag": "small", "language": "typescript"},
    {"id": "bad", "title": "Bad bounty", "reward_usd": 3, "entrants": 0,
     "has_tests": True},
]}
feed_path = os.path.join(tempfile.mkdtemp(), "feed.json")
with open(feed_path, "w", encoding="utf-8") as f:
    json.dump(feed, f)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = Q.main(["qualify.py", feed_path])
out = buf.getvalue()
check("qualifier: ranks and recommends", "RECOMMENDED" in out and "good" in out,
      out[-400:])
check("qualifier: skips the low-value one",
      "SKIP" in out and "bad" in out, out[:400])

# ===========================================================================
# LEDGER
# ===========================================================================
print("--- ledger ---")


def run(fn, args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fn(args)
    return rc, buf.getvalue()


rc, out = run(L.cmd_report, [])
check("ledger: empty report states zero", "US$0.00" in out, out[:200])
check("ledger: empty report exits 0", rc == 0)

rc, out = run(L.cmd_add, ["tb_1", "50", "submitted", "https://gh/pr/1"])
d = L.load()
check("ledger: attempt recorded", len(d["entries"]) == 1, repr(d))
check("ledger: submitted credits nothing", d["entries"][0]["payout_usd"] == 0.0)
check("ledger: total still zero", d["realized_usd"] == 0.0)

rc, out = run(L.cmd_add, ["tb_1", "50", "submitted"])
check("ledger: duplicate rejected", rc == 1 and "already exists" in out, out[:120])

rc, out = run(L.cmd_add, ["tb_2", "50", "awarded"])
d = L.load()
check("ledger: awarded credits 80%", d["entries"][1]["payout_usd"] == 40.0,
      repr(d["entries"][1]))
check("ledger: total reflects award", d["realized_usd"] == 40.0, repr(d["realized_usd"]))

rc, out = run(L.cmd_add, ["tb_3", "50", "rejected"])
d = L.load()
check("ledger: rejected credits nothing", d["realized_usd"] == 40.0)

rc, out = run(L.cmd_add, ["tb_4", "50", "bogus"])
check("ledger: invalid status rejected", rc == 2 and "invalid status" in out)

rc, out = run(L.cmd_close, ["tb_1", "33.60", "awarded"])
d = L.load()
e1 = [e for e in d["entries"] if e["task_id"] == "tb_1"][0]
check("ledger: close sets actual payout", e1["payout_usd"] == 33.60, repr(e1))
check("ledger: close sets status", e1["status"] == "awarded")
check("ledger: total after close", d["realized_usd"] == 73.60, repr(d["realized_usd"]))

rc, out = run(L.cmd_close, ["nope", "1", "awarded"])
check("ledger: close unknown fails", rc == 1)

rc, out = run(L.cmd_report, [])
check("ledger: report shows attempts", "attempts            3" in out, out)
check("ledger: report separates posted value",
      "posted value" in out and "NOT revenue" in out, out)
check("ledger: report shows in flight", "in flight" in out, out)
check("ledger: report shows realized", "REALIZED REVENUE    US$73.60" in out, out)
check("ledger: report shows win rate", "win rate" in out, out)

# recalc excludes non-awarded
d = L.load()
d["entries"][0]["status"] = "rejected"
L.save(d)
check("ledger: recalc excludes non-awarded", L.load()["realized_usd"] == 40.0)

# atomic write leaves no temp file
check("ledger: no temp file left", not os.path.exists(L.PATH + ".tmp"))

print()
if FAIL:
    print("%d FAILED: %s" % (len(FAIL), FAIL))
    sys.exit(1)
print("ALL PASS")
