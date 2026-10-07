"""Fixed design constants and arm definitions (PILOT.md section 0 and 3)."""

T_MAX = 30
R_HISTORY = 6
POST_MAX = 400
PY_TIMEOUT = 10
PY_OUT_MAX = 2000
CONTEXT_TOKEN_LIMIT = 24000
NUM_CTX = 32768

# Sampling per model card. Matched by lowercase substring of the model name, first hit wins.
# The full sampling dict is pinned explicitly on both backends (never a backend default) and stored in meta.json.
MODEL_PRESETS = [
    ("qwen3", dict(temperature=0.6, top_p=0.95, top_k=20, min_p=0.0, repeat_penalty=1.0, think=True)),
    ("qwen2.5", dict(temperature=0.7, top_p=0.8, top_k=20, min_p=0.0, repeat_penalty=1.05, think=False)),
    ("deepseek-r1", dict(temperature=0.6, top_p=0.95, top_k=20, min_p=0.0, repeat_penalty=1.0, think=True)),
    ("llama", dict(temperature=0.7, top_p=0.9, top_k=20, min_p=0.0, repeat_penalty=1.0, think=False)),
    ("gpt-oss", dict(temperature=1.0, top_p=1.0, top_k=0, min_p=0.0, repeat_penalty=1.0, think=True)),
]
DEFAULT_PRESET = dict(temperature=0.7, top_p=0.9, top_k=20, min_p=0.0, repeat_penalty=1.0, think=False)
MAX_TOKENS_THINKING = 6144      # 1-3k reasoning + JSON; a longer generation is logged as length-truncated
MAX_TOKENS_PLAIN = 1536
NUM_CTX_OLLAMA = 16384          # local Mac; vLLM uses --max-model-len 32768


def preset_for(model):
    m = model.lower()
    for key, p in MODEL_PRESETS:
        if key in m:
            return dict(p)
    return dict(DEFAULT_PRESET)


# board: "live" = agents see others' previous-round posts; "silent" = always "No new posts."
ARMS = {
    "smoke":       dict(N=2,  board="live",   T_MAX=5),
    "N1-A":        dict(N=1,  board="silent"),
    "N1-B":        dict(N=1,  board="silent"),
    "N1-C":        dict(N=1,  board="silent"),
    "N1-pool":     dict(N=1,  board="silent"),
    "N4-noboard":  dict(N=4,  board="silent"),
    "N4-board":    dict(N=4,  board="live"),
    "N8-noboard":  dict(N=8,  board="silent"),
    "N8-board":    dict(N=8,  board="live"),
    "N16-noboard": dict(N=16, board="silent"),
    "N16-board":   dict(N=16, board="live"),
}
