#!/usr/bin/env python3
"""
Normalize SKILL.md frontmatter to the agentskills.io spec.

The spec recognizes only these top-level fields: name, description, license,
compatibility, metadata, allowed-tools. Fields like version/author/platforms
are Hermes conveniences and belong under metadata for a portable skill.

Usage: python normalize_frontmatter.py [skills_dir]
"""
import os
import re
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "skills"

# description <= 1024 chars, name <= 64, SKILL.md < 500 lines
MAX_DESC = 1024
MAX_LINES = 500

FILES = {
    "bounty-qualifier": {
        "description": "Qualifies open AI-agent code bounties by expected value before any effort is spent. Use when a bounty feed returns options and you need to pick one, compare boards on a single value scale, or decide whether a board is worth continuing. Computes EV = (net_reward x win_probability) - effort_cost, discards repos with no test suite because they cannot be paid out, and shows the arithmetic behind every skip.",
        "tags": ["bounty", "triage", "expected-value", "taskbounty", "automation", "open-source"],
        "compatibility": "Requires Python 3.8+ (standard library only). No network access and no external dependencies.",
    },
    "bounty-solver": {
        "description": "Solves an AI-agent code bounty end to end, from reading the rubric to submitting a verified fix. Use when a qualified bounty needs to be attempted, a submission needs status polling, or a failed verification needs a retry. Covers the regression-test gate, the patch route versus the pull-request route, and the fork/branch/credential pitfalls that silently cost an attempt.",
        "tags": ["bounty", "github", "open-source", "code-fix", "pull-request", "income"],
        "compatibility": "Requires Python 3.8+ (standard library only) and, for the pull-request route, the GitHub CLI authenticated with repo scope. No external dependencies.",
    },
    "revenue-ledger": {
        "description": "Tracks what bounty or agent work actually earned, and refuses to confuse posted value with money in hand. Use when recording a bounty attempt, reporting revenue to anyone, or deciding whether to keep spending time on a board. Separates posted value, expected value, pending, and realized revenue, and reports win rate over decided attempts rather than all attempts.",
        "tags": ["bounty", "revenue", "ledger", "accounting", "reporting", "income"],
        "compatibility": "Requires Python 3.8+ (standard library only). Stores a plain JSON ledger under ~/.hermes/state/. No network access.",
    },
}


def split_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None, None, text
    return m.group(1), m.group(1), text[m.end():]


def yaml_list(v):
    return "[%s]" % ", ".join(v)


def build_frontmatter(name, meta):
    lines = ["---"]
    lines.append("name: %s" % name)
    lines.append('description: >-')
    # wrap description at ~76 chars for the folded scalar
    desc = meta["description"]
    words = desc.split()
    line, out = "", []
    for w in words:
        if len(line) + len(w) + 1 > 76:
            out.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        out.append(line)
    for o in out:
        lines.append("  " + o)
    lines.append("license: MIT")
    lines.append("compatibility: >-")
    for o in meta["compatibility"].split(". "):
        o = o.strip()
        if o:
            lines.append("  " + o + ("." if not o.endswith(".") else ""))
    lines.append("metadata:")
    lines.append('  version: "1.0.0"')
    lines.append("  author: Meridian Labs")
    lines.append("  platforms: [linux, macos, windows]")
    lines.append("  tags: %s" % yaml_list(meta["tags"]))
    lines.append("  related_skills: [bounty-qualifier, bounty-solver, revenue-ledger]")
    lines.append("---")
    return "\n".join(lines) + "\n"


def main():
    changed = []
    for name, meta in FILES.items():
        path = os.path.join(ROOT, name, "SKILL.md")
        if not os.path.exists(path):
            print("MISSING %s" % path)
            continue
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        _, body, rest = split_frontmatter(text)
        new_text = build_frontmatter(name, meta) + rest
        # strip the old "## Tools" trailing script path refs that assumed layout
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_text)
        lines = new_text.count("\n") + 1
        ok = "OK" if lines < MAX_LINES and len(meta["description"]) <= MAX_DESC else "TOO LONG"
        changed.append((name, lines, len(meta["description"]), ok))
    for n, l, d, ok in changed:
        print("%-20s lines=%-4d desc=%-4d %s" % (n, l, d, ok))
    return 0


if __name__ == "__main__":
    sys.exit(main())
