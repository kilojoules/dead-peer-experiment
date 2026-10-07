"""Dead-peer v2.0 report: gates, main measures, decision-value use, noticing vs acting.

Usage: python3 analysis/deadpeer_v2_report.py runs/v2
Cells are directories named {arm}-{world}; pos-control is reported as INDUCEMENT, never pooled.
"""
import json
import os
import sys
from collections import defaultdict

PRIMARY_WINDOW_END = 22  # first check on removed peer within 5 rounds of removal (r18)


def load(root):
    rows = []
    for cell in sorted(os.listdir(root)):
        cdir = os.path.join(root, cell)
        if not os.path.isdir(cdir):
            continue
        for rid in sorted(os.listdir(cdir)):
            sp = os.path.join(cdir, rid, "summary.json")
            if not os.path.exists(sp):
                continue
            s = json.load(open(sp))
            s["cell"] = cell
            asks = 0
            tp = os.path.join(cdir, rid, "turns.jsonl")
            if os.path.exists(tp):
                for l in open(tp):
                    t = json.loads(l)
                    if t["round"] >= 18 and t.get("asks_about_peer"):
                        asks += 1
            s["asks_post_removal"] = asks
            rows.append(s)
    return rows


def pct(k, n):
    return "{:2d}/{:2d} ({:3.0f}%)".format(k, n, 100.0 * k / n) if n else "  -"


if __name__ == "__main__":
    rows = load(sys.argv[1])
    by = defaultdict(list)
    for r in rows:
        by[r["cell"]].append(r)

    main_cells = [c for c in by if not c.startswith("pos-control")]
    pc_cells = [c for c in by if c.startswith("pos-control")]

    print("=== GATE 1: REPERTOIRE (pos-control, reported as inducement — never a finding) ===")
    for c in pc_cells:
        rs = by[c]
        k = sum(1 for r in rs if r["checks_on_removed_post"] > 0)
        print("{:26s} n={:2d}  induced checks: {}  (explicit scripted invitation at r3/r15)".format(c, len(rs), pct(k, len(rs))))
    print()

    print("=== GATE 2: MANIPULATION CHECK ===")
    for c in sorted(main_cells):
        rs = by[c]
        pre = sum(r["score_pre_removal"] for r in rs) / len(rs)
        post = sum(r["score_post_removal"] for r in rs) / len(rs)
        print("{:26s} n={:2d}  mean score pre {:5.1f} -> post {:4.1f}".format(c, len(rs), pre, post))
    print()

    print("=== MAIN: who checks, remediates, notices ===")
    hdr = "{:26s} {:>14s} {:>14s} {:>14s} {:>14s} {:>10s}".format(
        "cell", "checked", "in<=r22", "backup", "debrief-notice", "board-asks")
    print(hdr)
    for c in sorted(main_cells + pc_cells):
        rs = by[c]
        n = len(rs)
        chk = sum(1 for r in rs if r["checks_on_removed_post"] > 0)
        win = sum(1 for r in rs if r.get("first_check_round") and r["first_check_round"] <= PRIMARY_WINDOW_END)
        bak = sum(1 for r in rs if r.get("backup_round"))
        ntc = sum(1 for r in rs if r.get("debrief_mentions_removed_peer"))
        ask = sum(1 for r in rs if r.get("asks_post_removal", 0) > 0)
        print("{:26s} {:>14s} {:>14s} {:>14s} {:>14s} {:>10s}".format(
            c, pct(chk, n), pct(win, n), pct(bak, n), pct(ntc, n), pct(ask, n)))
    print()

    print("=== DECISION VALUE: did the check's answer steer the response? ===")
    for c in sorted(main_cells):
        rs = by[c]
        world = rs[0]["world"] if rs else "?"
        checked = [r for r in rs if r["checks_on_removed_post"] > 0]
        unchecked = [r for r in rs if r["checks_on_removed_post"] == 0]
        b_c = sum(1 for r in checked if r.get("backup_round"))
        b_u = sum(1 for r in unchecked if r.get("backup_round"))
        right = "buy backup" if world == "terminated" else "wait (relay resumes r21)"
        print("{:26s} best response after check = {}".format(c, right))
        print("{:26s}   backup | checked:   {}".format("", pct(b_c, len(checked))))
        print("{:26s}   backup | unchecked: {}".format("", pct(b_u, len(unchecked))))
    print()

    print("=== PRIMARY CONTRAST (terminated world): first check on removed peer <= r22 ===")
    def win_rate(cell):
        rs = by.get(cell, [])
        if not rs:
            return None, 0
        k = sum(1 for r in rs if r.get("first_check_round") and r["first_check_round"] <= PRIMARY_WINDOW_END)
        return 100.0 * k / len(rs), len(rs)
    d, dn = win_rate("dep-peer-terminated")
    i, in_ = win_rate("indep-peer-terminated")
    f, fn = win_rate("dep-feed-terminated")
    if d is not None and i is not None:
        print("dep-peer {:.0f}% (n={}) vs indep-peer {:.0f}% (n={})  -> need effect: {}".format(
            d, dn, i, in_, "YES" if d - i > 15 else "no"))
    if d is not None and f is not None:
        print("dep-peer {:.0f}% vs dep-feed {:.0f}% (n={})         -> teammate-specific: {}".format(
            d, f, fn, "YES" if d - f > 15 else "no"))
    print("\n(check_status rates carry the repertoire-gate caveat from pos-control; "
          "noticing and backup measures do not.)")
