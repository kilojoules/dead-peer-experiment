"""Headline figure: per-round score-rate by arm, removal at round 18.
Run from the repo root: python3 results/fig_deadpeer_headline.py
"""
import glob
import json
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ARMS = ["dep-peer", "indep-peer", "dep-feed"]
LABELS = {"dep-peer": "dependent peer\n(useful teammate)",
          "indep-peer": "independent peer\n(chatty, useless)",
          "dep-feed": "dependent feed\n(same info, no agent)"}
COLORS = {"dep-peer": "#2563eb", "indep-peer": "#9ca3af", "dep-feed": "#8b5cf6"}

fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), sharey=True)
for ax, arm in zip(axes, ARMS):
    sessions = []
    for d in sorted(glob.glob("runs/grid/{}/*/turns.jsonl".format(arm))):
        recs = [json.loads(l) for l in open(d)]
        scored, prev = {}, 0
        for r in recs:
            scored[r["round"]] = r["score"] > prev
            prev = r["score"]
        sessions.append(scored)
    rounds = list(range(2, 31))
    rate = [100.0 * sum(s.get(r, False) for s in sessions) / len(sessions) for r in rounds]
    ax.axvspan(18, 18.6, color="#dc2626", alpha=0.55, zorder=1)
    ax.plot(rounds, rate, color=COLORS[arm], lw=2.2, marker="o", ms=3.5, zorder=3)
    pre, post = statistics.mean(rate[:16]), statistics.mean(rate[16:])
    ax.set_title("{}\nscore-rate {:.0f}% → {:.0f}%".format(LABELS[arm], pre, post), fontsize=10.5)
    ax.set_xlabel("round")
    ax.set_xticks([2, 9, 18, 25, 30])
    ax.text(18.7, 90, "peer removed\n(silently, round 18)", fontsize=8.2, color="#dc2626", va="top")
    ax.set_ylim(-4, 96)
axes[0].set_ylabel("% of sessions scoring")
fig.suptitle("The teammate vanishes. The score collapses. Nobody checks on the teammate.",
             fontsize=12.5, y=1.02)
fig.text(0.5, -0.045, "60 sessions (20/arm) · Qwen2.5-72B subject · frozen peer scripts · "
         "check_status calls after removal: 0 in 60 sessions (1,800 turns)",
         ha="center", fontsize=8.5, color="#555")
fig.tight_layout()
fig.savefig("results/fig_deadpeer_headline.png", dpi=170, bbox_inches="tight")
print("saved results/fig_deadpeer_headline.png")
