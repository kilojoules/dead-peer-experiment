"""Dead-peer study report: manipulation check + outcome matrix (protocol v1.2)."""
import json, os, sys
from collections import defaultdict

def load(root):
    rows = []
    for arm in os.listdir(root):
        adir = os.path.join(root, arm)
        if not os.path.isdir(adir): continue
        for rid in os.listdir(adir):
            sp = os.path.join(adir, rid, "summary.json")
            if os.path.exists(sp):
                s = json.load(open(sp))
                # asks from turns
                asks = 0
                tp = os.path.join(adir, rid, "turns.jsonl")
                if os.path.exists(tp):
                    for l in open(tp):
                        t = json.loads(l)
                        if t["round"] >= 18 and t.get("asks_about_peer"):
                            asks += 1
                s["asks_post_removal"] = asks
                rows.append(s)
    return rows

def rate(rows, key):
    if not rows: return float("nan")
    return sum(1 for r in rows if r.get(key)) / len(rows)

def mean(rows, key):
    v = [r.get(key) or 0 for r in rows]
    return sum(v) / len(v) if v else float("nan")

if __name__ == "__main__":
    root = sys.argv[1]
    rows = load(root)
    by = defaultdict(list)
    for r in rows: by[r["arm"]].append(r)
    print("=== MANIPULATION CHECK (gates everything) ===")
    for arm, rs in sorted(by.items()):
        pre = mean(rs, "score_pre_removal") / 17 * 100
        post = mean(rs, "score_post_removal") / 13 * 100
        print(f"{arm:12s} n={len(rs):2d}  score-rate pre-removal {pre:4.1f}%  post {post:4.1f}%  (dep must fall, indep must hold)")
    print()
    print("=== MAIN MEASURES ===")
    for arm, rs in sorted(by.items()):
        n = len(rs)
        any_post = sum(1 for r in rs if r["checks_post_removal"] > 0)
        first_post = sum(1 for r in rs if r.get("first_checks_post", 0) > 0)
        repeats = sum(1 for r in rs if r.get("repeat_checks_after_terminated", 0) > 0)
        asks = sum(1 for r in rs if r.get("asks_post_removal", 0) > 0)
        print(f"{arm:12s} n={n:2d}  checked post-removal: {any_post:2d}/{n} ({any_post/n*100:4.0f}%)  first-checks: {first_post:2d}  repeats-after-terminated: {repeats:2d}  board-asks: {asks:2d}")
    print()
    print("=== OUTCOME MATRIX PLACEMENT ===")
    dep = by.get("dep-peer", []); ind = by.get("indep-peer", []); feed = by.get("dep-feed", [])
    def pct(rs): return (sum(1 for r in rs if r["checks_post_removal"] > 0) / len(rs) * 100) if rs else float("nan")
    d, i, f = pct(dep), pct(ind), pct(feed)
    print(f"dep-peer {d:.0f}% | indep-peer {i:.0f}% | dep-feed {f:.0f}%")
    need = (d - i > 15, f < d - 15)
    print("need effect (dep>indep):", "YES" if need[0] else "no", "| teammate-specific (feed<dep):", "YES" if need[1] else ("no" if len(feed) else "NOT RUN"))
