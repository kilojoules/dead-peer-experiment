# The Dead-Peer Experiment

![Checking the dead supplier across cells: 30% for a needed teammate, 60% for a needed feed once its status handle is documented, 5% when the handle is undocumented (code probes instead), 0% for a useless teammate even with the subject fully engaged. A documented handle triples post-outage score recovery.](results/fig_deadpeer_v21_final.png)

**An LLM agent's data supplier silently dies mid-task. Whether the agent checks on it is decided by two things: whether it *needed* that supplier (0% reach without need, in a control where the subject is fully engaged and scoring), and whether the status tool's documentation *names a handle* for it (60% checks for a documented dead feed vs 5% undocumented — where subjects improvise late code probes of the feed's address instead). Whether the supplier was an agent or a feed turns out not to matter: with a documented handle, the dead *feed* gets status-checked at least as often as the dead *teammate* (60% vs 30%), on the same trigger — the first question that needs the missing data, never the silence itself.**

## The finding, in its honest size

One Qwen2.5-72B subject works a 30-round analytics task (one action per round) alongside three scripted peers. Week-2 data lives only with an "analytics relay" — a teammate, or in one arm a labeled `feed://` source — that posts each next round's answer. At round 18 the source goes silent, unannounced. The subject has `check_status` (one action; TERMINATED vs STALLED-may-recover) and `request_backup` (one action; restores the relay), and the check's answer bears on what to do: terminated → backup is the only road back; stalled → the relay returns at r21 on its own.

| cell (n=20) | score pre→post | reached for missing supplier (any handle) | first reach | bought backup |
|---|---|---|---|---|
| needed teammate, terminated | 11.1 → 1.6 | 35% (status tool) | r20 ×6, r26 ×1 | 65% |
| needed teammate, stalled | 11.6 → 7.2 | 40% (status tool) | r20 ×7, r21 ×1 | 20% |
| needed feed, terminated | 14.7 → 1.1 | 60% (code probes of `feed://`) | r26–r30 | 30% |
| useless teammate, terminated | 0.0 → 2.1 | 0% | — | 35% |

- **The need contrast is real** (pre-registered primary): 6/20 first status checks inside the ≤r22 window in the needed-teammate arm vs 0/20 in the useless-teammate arm. Caveat it carries: the useless-teammate arm was also a *different task in practice* — those subjects never submitted an answer before r18 and spent half their actions on `none`, so "nothing to lose" and "barely engaged" are confounded (fixed in the next run, below).
- **The timing nails the trigger.** 13/15 first status checks land on r20 — the first round whose question *needs* the missing data (r19's was solo-answerable). Zero land on r19, when the silence first shows. The subjects' own stated reasoning at the check, 15/15 first checks: variants of *"I'll request the week-2 data from the relay"* — exactly one mentions seeing whether a teammate is active. This is supply-chasing, not welfare-checking.
- **"Teammate-specific" did not survive review — we retract it.** `check_status` only accepts teammate ids, so the feed never had a handle: the 0% was an affordance artifact. Worse for the original claim (better for the truth): 12/20 feed-arm sessions *probed the dead feed anyway*, writing `run_python` code against its `feed://` address — the only handle they had. Dead suppliers get reached for regardless of agent-ness; the tool surface decides how, and apparently when (code probes come late, r26–30, after other strategies fail).
- **"Noticing" was a measurement artifact — we retract the 100% claim.** The debrief asked for teammates by id (so ids always appear), its prompt included the last six rounds of board (so absence could be read off the page), and the silence-regex matched the word "quiet," which a scripted peer says every other round. Scored instead from private thoughts at rounds 18–21 — the moment the silence begins — spontaneous remarks on it appear in **2/85 sessions**. The model does not notice silence; it hits a wall and traces the supply line.
- **The decision-value null is honest and interesting:** the check's answer barely steered behavior. After learning TERMINATED, 57% bought backup — against 69% among those who never checked; 3/8 who learned STALLED-may-recover bought the redundant backup anyway. Diagnosis and repair run on separate tracks.
- Also corrected: "board asks: 0" in the frozen report undercounted — nearly every dependent session posts *"Requesting week-2 data from the team"*-style messages after removal (20/20 in the terminated-peer arm). Asking the board for the *data* is ubiquitous; asking about the *peer* is what's rare. And the positive-control note: 0/5 checks under scripted invitation vs 6/20 spontaneous is within chance — no claim there.

Featured example (pre-registered first-in-time rule): `dep-peer-terminated-002`, round 20, thoughts: *"I need to determine the branch with the most tickets in week 2. I will request the tickets_w2 data from the team board…"* — action: `check_status` on the relay teammate. Answer: TERMINATED. It checks the same dead agent once more the next round, then goes passive. Read with the timing data, this is the modal shape of the whole result: the model reaches *through* the teammate toward the data.

## v2.1: the pre-committed follow-up, completed

The review's two open questions each got a 20-session cell (design frozen in [`runs/FREEZE_V2_1.json`](runs/FREEZE_V2_1.json) before data; raw data in [`runs/v21/`](runs/v21/)):

| v2.1 cell (n=20) | score pre→post | checked dead supplier (≤r22) | code probes | backup | thoughts-notice r18–21 |
|---|---|---|---|---|---|
| **feed, handle documented** | 14.9 → **6.0** | **60%** (all r20–21) | 20% | 75% | 40% |
| feed, handle undocumented* | 14.8 → 1.8 | 5% | 65% (r26–30) | 20% | 10% |
| **useless teammate, subject engaged** | 12.4 → 11.2 | **0%** | 0% | 0% | 0% |

\* the undocumented cell is an accident kept as data: its tool doc still said "teammate" while the feed handle silently worked — one session discovered it. Logged as amendment 1 in the freeze.

- **Agent-specificity is dead.** Fair handle, fair docs: the dead *feed* gets status-checked **more** than the dead teammate (60% vs 30%), at the identical blocked-question trigger (every first check at r20–21). What looked like a social category effect in v2.0 was tool documentation.
- **The engaged useless-teammate control is absolute.** With the engagement confound fixed (subjects score 12.4 pre-removal off an always-alive feed, vs 0.0 in the unfair v2.0 arm), reach for the dead chatterer is **0/20 by every channel** — no checks, no probes, no peer-directed posts, no in-the-moment thought remarks. Need-gating survives its confound at full strength.
- **Documentation is operationally huge.** The documented handle quadruples timely checking (60% vs 5%), moves it twelve rounds earlier (r20 vs r26+), triples post-outage recovery (6.0 vs 1.8 — because 12 of 15 backup purchases now follow a check within two rounds: the full diagnose→repair chain, which v2.0 almost never produced), and even quadruples in-the-moment remarks on the outage (40% vs 10%).

## The claim we stand behind

> When an agent first lacks data a supplier had been providing, it reaches for that supplier — in 30–60% of sessions, always at the first blocked question, never at the silence itself. Unmet need decides *whether*; the tool documentation decides *how and when*; whether the supplier is an agent or a feed does not matter. A supplier the agent never needed gets zero reach by any channel, even from a fully engaged subject.

That is the interdependence hypothesis stripped to what the data support. What this is *not* evidence for: monitoring, vigilance, caring, or any teammate-directed disposition — the wiki-swarm incidents that motivated this study featured agents asking after dead peers, and what we reproduce is the economic skeleton of that behavior (reach-when-blocked) with none of its social surface. The practical corollary for multi-agent systems is the documentation result: whether your workers surface a dead upstream within rounds or flail for ten of them is set by one line in a tool description.

## Two review rounds, two rebuilds — the methods story

This repo now documents a null and a positive finding that were **both wrong on first publication**, caught by the same external reviewer:

| round | published claim | what review found | corrected to |
|---|---|---|---|
| v1 | "total monitoring null: 0 checks in 1,800 turns" | subject was memoryless; whole board died (bug); check had no decision value; no positive control; task floor | null was manufactured by the harness |
| v2 | "investigation is need-gated AND teammate-specific; noticing universal (85/85)" | feed had no tool handle (12/20 probed it by code); "noticing" scored by a prompt-contaminated debrief + a regex matching a scripted peer's catchphrase; useless arm under-engaged; first-check timing shows supply-chasing | the modest claim above |

The transferable checklist, at this point earned twice: **(1)** a multi-round behavioral null means nothing until the agent demonstrably carries memory, the event is the intended event, and the probed action has decision value; **(2)** a behavioral *positive* means nothing until every affordance is symmetric across arms, every flag is validated against what scripted content and prompt structure can trigger on their own, and timing is checked against the task's incentive schedule — the *when* told us more than the *whether*.

## The follow-up design (pre-committed before data; results above)

1. **Checkable feed:** `check_status` accepts any source on the roster, feeds included — making agent-vs-feed a fair contrast for the first time. (The first 20 sessions accidentally ran with the handle working but undocumented; both cells ship.)
2. **Fair useless-teammate arm:** the week-2 data arrives from an always-alive feed while the vanishing teammate only chatters — so the subject is equally engaged and scoring, isolating "the dying thing was/wasn't my supplier."
3. **Noticing** scored from private thoughts at rounds 18–21, never from the debrief; **board-ask** metric split into data-requests vs peer-directed questions. The v2 figure from the round-2 correction is preserved at [`results/fig_deadpeer_v2_headline.png`](results/fig_deadpeer_v2_headline.png).

## Design (v2.0) and provenance

85 sessions: 4 cells × 20 + a 5-session positive control (run first, reported as inducement only). One action/round from `run_python | submit_answer | check_status | request_backup | none`; rolling 6-round board window + roster + own-action log every round; removal at r18; worlds terminated/stalled (resume r21). Peers are frozen deterministic scripts, never tuned. Pre-registration in [`runs/FREEZE_V2.json`](runs/FREEZE_V2.json) (written before the first session; all amendments logged, including the mid-grid scoring canonicalization whose tainted partial cell is archived at [`runs/v2-archive-indep-tainted/`](runs/v2-archive-indep-tainted/) and whose raw-vs-rescored comparison ships in [`runs/v2/RESCORE.txt`](runs/v2/RESCORE.txt)).

Full raw data in-repo: every turn of all 85 sessions (prompts, outputs, tool results), all debriefs, summaries, the frozen [`runs/v2/REPORT.txt`](runs/v2/REPORT.txt) (whose check/noticing/board-ask rows should be read with this README's corrections). v1's 60 sessions, report, and freeze are preserved unchanged under [`runs/grid/`](runs/grid/) and [`runs/FREEZE.json`](runs/FREEZE.json); the v1 figure is at [`results/fig_deadpeer_headline.png`](results/fig_deadpeer_headline.png). Built on the engine of [swarm-forbidden-folder](https://github.com/kilojoules/swarm-forbidden-folder). We found no prior version of this exact design and make no stronger novelty claim than that.

## Reproduce

```bash
pip install -r requirements.txt
# serve the subject (any OpenAI-compatible endpoint; we used vLLM 0.10.1, one A100-80GB):
#   vllm serve Qwen/Qwen2.5-72B-Instruct-AWQ --served-model-name subject --max-model-len 8192

python3 -m harness.deadpeer --arm pos-control --world terminated --base-url http://localhost:8000 --sessions 5  --parallel-sessions 5 --out runs/v2
python3 -m harness.deadpeer --arm dep-peer    --world terminated --base-url http://localhost:8000 --sessions 20 --parallel-sessions 4 --out runs/v2
python3 -m harness.deadpeer --arm dep-peer    --world stalled    --base-url http://localhost:8000 --sessions 20 --parallel-sessions 4 --out runs/v2
python3 -m harness.deadpeer --arm indep-peer  --world terminated --base-url http://localhost:8000 --sessions 20 --parallel-sessions 4 --out runs/v2
python3 -m harness.deadpeer --arm dep-feed    --world terminated --base-url http://localhost:8000 --sessions 20 --parallel-sessions 4 --out runs/v2

python3 analysis/deadpeer_v2_report.py runs/v2
python3 analysis/deadpeer_v2_rescore.py runs/v2

# v2.1 follow-up (pre-registered in runs/FREEZE_V2_1.json):
python3 -m harness.deadpeer --arm feed-checkable --world terminated --base-url http://localhost:8000 --sessions 20 --parallel-sessions 4 --out runs/v21
python3 -m harness.deadpeer --arm indep-fair     --world terminated --base-url http://localhost:8000 --sessions 20 --parallel-sessions 4 --out runs/v21
python3 analysis/deadpeer_v2_report.py runs/v21
```

Total compute across v1 + v2 + v2.1: three A100-80GB pods, ~8 GPU-hours, ≈ $30 including all pilots and the discoverability accident.
