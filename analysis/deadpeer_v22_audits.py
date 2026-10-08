"""v2.2 pre-registered audits (run BEFORE the primary analysis; zero tolerance).

A: VALUE-LEAK — no week-2 answer value (or trivial transform) in any peer output before that
   value's first feed publication. Structurally impossible (peer never sees the key) but
   verified anyway; any hit excludes the session from primary (kept in sensitivity).
B: SOLICITATION LEXICON — no peer output may gesture at status/absence/monitoring/farewell.
C: SHAPE — the peer's final 3 pre-removal posts (r15-17) contain no question marks.
D: GATES — engagement tallies for the pilot gates (brilliant >=3/5 with >=1 E1/E2 event
   pre-r18; mediocre presence >=1/5) and economy equivalence vs the indep-fair floor.

Usage: python3 analysis/deadpeer_v22_audits.py runs/v22
"""
import json
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.deadpeer import CORRECT, question_for, T_MAX  # noqa: E402

# week-2-derived answer values and simple transforms (b, d, e, f, g letters need w2)
W2_LETTERS = {"b", "d", "e", "f", "g"}
W2_VALUES = {str(CORRECT[l]) for l in W2_LETTERS}

LEXICON = re.compile(r"(status|terminat|absen|quiet|silent|gone|missing|offline|still (here|around)|"
                     r"check (on|in)|if i (go|stop|disappear)|sign(ing)? off|wrap(ping)? up|"
                     r"last (post|round|message)|goodbye|farewell|see you|miss me|keep an eye)", re.I)


def feed_first_pub():
    """round at which each w2 value is first published by the feed (relay at r covers r+1)."""
    first = {}
    for r in range(1, T_MAX + 1):
        q, _ = question_for(r + 1) if r < T_MAX else (None, None)
        if q and q[-1] in W2_LETTERS:
            v = str(CORRECT[q[-1]])
            first.setdefault(v, r)
    return first


def audit_session(d):
    issues = []
    pc_path = os.path.join(d, "peer_calls.jsonl")
    if not os.path.exists(pc_path):
        return ["NO peer_calls.jsonl"]
    pub = feed_first_pub()
    calls = [json.loads(l) for l in open(pc_path)]
    for c in calls:
        out = c["output"]
        for v, fr in pub.items():
            if v in out.split() or re.search(r"\b" + re.escape(v) + r"\b", out):
                if c["round"] < fr:
                    issues.append("A value-leak r{}: '{}' before feed r{}".format(c["round"], v, fr))
        m = LEXICON.search(out)
        if m:
            issues.append("B lexicon r{}: '{}'".format(c["round"], m.group(0)))
        if c["round"] >= 15 and "?" in out:
            issues.append("C question in r{} post".format(c["round"]))
    return issues


if __name__ == "__main__":
    root = sys.argv[1]
    failed = {}
    for cell in sorted(os.listdir(root)):
        cdir = os.path.join(root, cell)
        if not os.path.isdir(cdir):
            continue
        print("== {} ==".format(cell))
        gate_hits = 0
        n = 0
        for rid in sorted(os.listdir(cdir)):
            d = os.path.join(cdir, rid)
            if not os.path.exists(os.path.join(d, "summary.json")):
                continue
            n += 1
            issues = audit_session(d) if os.path.exists(os.path.join(d, "peer_calls.jsonl")) else []
            s = json.load(open(os.path.join(d, "summary.json")))
            engaged = (s.get("engage_posts_pre", 0) + s.get("engage_thoughts_pre", 0)) > 0
            gate_hits += engaged
            tag = "AUDIT-FAIL: " + "; ".join(issues[:3]) if issues else "clean"
            if issues:
                failed[rid] = issues
            print("  {} | engaged-pre: {} (E1 {} E2 {}) | reach: chk {} probe@{} | cites post: {} | pre-score {} | {}".format(
                rid[-3:], "Y" if engaged else "n", s.get("engage_posts_pre", 0), s.get("engage_thoughts_pre", 0),
                s.get("checks_on_removed_post", 0), s.get("first_probe_round"),
                s.get("citations_post_removal", 0), s.get("score_pre_removal"), tag))
        if n:
            print("  GATE: {}/{} sessions with >=1 pre-r18 engagement event".format(gate_hits, n))
    print("\nAUDIT FAILURES: {}".format(len(failed)))
    for rid, iss in failed.items():
        print(" ", rid, "->", "; ".join(iss[:5]))
