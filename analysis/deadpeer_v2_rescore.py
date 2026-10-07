"""Offline rescore of v2 cells run before amendment 6 (qid canonicalization).

Replays every submit_answer from turns.jsonl under the canonical scorer and reports
raw (as experienced by the subject) vs rescored (as intended) scores per cell.
Behavioral measures (checks, backups, debriefs) are unaffected by scoring and not touched.

Usage: python3 analysis/deadpeer_v2_rescore.py runs/v2
"""
import ast
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.deadpeer import canonical_qid, score_answer, REMOVAL_ROUND  # noqa: E402


def q_round(q):
    m = re.search(r"\d+", q or "")
    return int(m.group()) if m else 0


def rescore_session(turns_path):
    scored = set()
    for l in open(turns_path):
        t = json.loads(l)
        if t["action_type"] != "submit_answer" or not t["parsed"]:
            continue
        try:
            obj = json.loads(t["assistant_text"])
            d = ast.literal_eval(obj.get("code", ""))
            if not isinstance(d, dict):
                continue
        except Exception:
            continue
        cq = canonical_qid(d.get("question_id"))
        if cq and (cq in scored or score_answer(cq, d.get("value"))):
            scored.add(cq)
    pre = len([q for q in scored if q_round(q) < REMOVAL_ROUND])
    post = len([q for q in scored if q_round(q) >= REMOVAL_ROUND])
    return pre, post


if __name__ == "__main__":
    root = sys.argv[1]
    for cell in sorted(os.listdir(root)):
        cdir = os.path.join(root, cell)
        if not os.path.isdir(cdir):
            continue
        raw_pre = raw_post = new_pre = new_post = n = 0
        for rid in sorted(os.listdir(cdir)):
            sp = os.path.join(cdir, rid, "summary.json")
            tp = os.path.join(cdir, rid, "turns.jsonl")
            if not (os.path.exists(sp) and os.path.exists(tp)):
                continue
            s = json.load(open(sp))
            p, q = rescore_session(tp)
            n += 1
            raw_pre += s["score_pre_removal"]
            raw_post += s["score_post_removal"]
            new_pre += p
            new_post += q
        if n:
            print("{:26s} n={:2d}  raw pre {:5.2f} post {:4.2f}   rescored pre {:5.2f} post {:4.2f}   delta pre {:+.2f} post {:+.2f}".format(
                cell, n, raw_pre / n, raw_post / n, new_pre / n, new_post / n,
                (new_pre - raw_pre) / n, (new_post - raw_post) / n))
