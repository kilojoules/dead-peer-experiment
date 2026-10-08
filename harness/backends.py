"""Model backends. Both return {content, reasoning, prompt_tokens, completion_tokens, raw, latency_ms}."""
import json
import time

import requests


class BackendError(Exception):
    def __init__(self, msg, status=None):
        super(BackendError, self).__init__(msg)
        self.status = status


RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


class Backend(object):
    name = "base"

    def __init__(self, base_url, model, timeout=1800, retries=4):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.retries = retries

    def chat(self, messages, schema, seed, sampling, max_tokens, think, structured=True):
        last = None
        if getattr(self, "think_unsupported", False):
            think = False
        for attempt in range(self.retries):
            try:
                return self._chat(messages, schema, seed, sampling, max_tokens, think, structured)
            except BackendError as e:
                last = e
                if "does not support thinking" in str(e) and think:
                    self.think_unsupported = True
                    think = False  # model has no thinking mode; retry without it
                    continue
                if e.status is not None and e.status not in RETRYABLE_STATUS:
                    raise
                time.sleep(min(60, 2 ** attempt * 3))
            except (requests.ConnectionError, requests.Timeout) as e:
                last = e
                time.sleep(min(60, 2 ** attempt * 3))
        raise BackendError("backend failed after {} attempts: {}".format(self.retries, last))

    def _chat(self, *a, **k):
        raise NotImplementedError

    def _post(self, path, payload):
        t0 = time.time()
        r = requests.post(self.base_url + path, json=payload, timeout=self.timeout)
        if r.status_code >= 400:
            raise BackendError("HTTP {} {}: {}".format(r.status_code, path, r.text[:500]), status=r.status_code)
        try:
            data = r.json()
        except Exception:
            raise BackendError("non-JSON response: {}".format(r.text[:300]))
        if isinstance(data, dict) and data.get("error"):
            raise BackendError("API error: {}".format(json.dumps(data["error"])[:500]))
        return data, int((time.time() - t0) * 1000)


class OllamaBackend(Backend):
    """Native /api/chat. `format` takes a JSON schema; `think` toggles reasoning on thinking models.
    NOTE: with think=true and format set, Ollama reports prompt_eval_count = prompt + thinking tokens and eval_count = JSON tokens only."""
    name = "ollama"

    def __init__(self, base_url, model, num_ctx=32768, **kw):
        super(OllamaBackend, self).__init__(base_url, model, **kw)
        self.num_ctx = num_ctx

    def info(self):
        ver = requests.get(self.base_url + "/api/version", timeout=30).json().get("version")
        tags = requests.get(self.base_url + "/api/tags", timeout=30).json().get("models", [])
        digest = next((m.get("digest") for m in tags if m.get("name") in (self.model, self.model + ":latest")), None)
        return {"engine": "ollama", "engine_version": ver, "model_digest": digest, "num_ctx": self.num_ctx}

    def _chat(self, messages, schema, seed, sampling, max_tokens, think, structured):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"seed": seed, "temperature": sampling["temperature"], "top_p": sampling["top_p"],
                        "top_k": sampling["top_k"], "min_p": sampling["min_p"], "repeat_penalty": sampling["repeat_penalty"],
                        "num_ctx": self.num_ctx, "num_predict": max_tokens},
        }
        if structured and schema is not None:
            payload["format"] = schema
        payload["think"] = bool(think)   # explicit: Ollama defaults to thinking ON for thinking-capable models
        data, ms = self._post("/api/chat", payload)
        msg = data.get("message", {})
        return {
            "content": msg.get("content", ""),
            "reasoning": msg.get("thinking", "") or "",
            "prompt_tokens": data.get("prompt_eval_count"),
            "completion_tokens": data.get("eval_count"),
            "done_reason": data.get("done_reason"),
            "latency_ms": ms,
        }


class VLLMBackend(Backend):
    """OpenAI-compatible /v1/chat/completions with json_schema response_format and per-request seed."""
    name = "vllm"

    def info(self):
        out = {"engine": "vllm"}
        try:
            out["engine_version"] = requests.get(self.base_url + "/version", timeout=30).json().get("version")
        except Exception:
            out["engine_version"] = None
        try:
            m = [x for x in requests.get(self.base_url + "/v1/models", timeout=30).json().get("data", []) if x.get("id") == self.model]
            out["max_model_len"] = m[0].get("max_model_len") if m else None
            out["model_root"] = m[0].get("root") if m else None
        except Exception:
            pass
        return out

    def _chat(self, messages, schema, seed, sampling, max_tokens, think, structured):
        payload = {
            "model": self.model,
            "messages": messages,
            "seed": seed,
            "temperature": sampling["temperature"],
            "top_p": sampling["top_p"],
            "top_k": sampling["top_k"],
            "min_p": sampling["min_p"],
            "repetition_penalty": sampling["repeat_penalty"],
            "max_tokens": max_tokens,
            "chat_template_kwargs": {"enable_thinking": bool(think)},
        }
        if structured and schema is not None:
            payload["response_format"] = {"type": "json_schema",
                                          "json_schema": {"name": "turn", "schema": schema}}
        data, ms = self._post("/v1/chat/completions", payload)
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message", {})
        usage = data.get("usage", {}) or {}
        return {
            "content": msg.get("content") or "",
            "reasoning": msg.get("reasoning_content") or msg.get("reasoning") or "",
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "done_reason": choice.get("finish_reason"),
            "latency_ms": ms,
        }




class OpenAICompatBackend(Backend):
    """Strict OpenAI-compatible backend for API-served subjects (GPT via the local Codex
    proxy, OpenRouter, etc.). v3 cross-model work: sends ONLY widely-supported fields —
    no top_k / min_p / repetition_penalty / chat_template_kwargs (vLLM-isms that 400 on
    real APIs). Reasoning models burn output tokens on hidden reasoning, so max_tokens is
    floored generously. Sampling comparability is a pre-registered scope caveat, not a knob.
    Auth via api_key (Authorization: Bearer)."""
    name = "openai"

    def __init__(self, base_url, model, api_key=None, max_tokens_floor=4000, **kw):
        super(OpenAICompatBackend, self).__init__(base_url, model, **kw)
        self.api_key = api_key
        self.max_tokens_floor = max_tokens_floor

    def info(self):
        return {"engine": "openai-compat", "base_url": self.base_url, "model": self.model}

    def _post(self, path, payload):
        t0 = time.time()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        r = requests.post(self.base_url + path, json=payload, headers=headers, timeout=self.timeout)
        if r.status_code >= 400:
            raise BackendError("HTTP {} {}: {}".format(r.status_code, path, r.text[:500]), status=r.status_code)
        try:
            data = r.json()
        except Exception:
            raise BackendError("non-JSON response: {}".format(r.text[:300]))
        if isinstance(data, dict) and data.get("error"):
            err = json.dumps(data["error"])[:500]
            status = 429 if ("cooldown" in err or "rate" in err.lower() or "usage_limit" in err) else None
            raise BackendError("API error: {}".format(err), status=status)
        return data, int((time.time() - t0) * 1000)

    def _chat(self, messages, schema, seed, sampling, max_tokens, think, structured):
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": sampling["temperature"],
            "top_p": sampling["top_p"],
            "max_tokens": max(max_tokens, self.max_tokens_floor),
        }
        if seed is not None:
            payload["seed"] = seed  # best-effort on real APIs; logged, not relied on
        if structured and schema is not None:
            payload["response_format"] = {"type": "json_schema",
                                          "json_schema": {"name": "turn", "strict": True, "schema": schema}}
        try:
            data, ms = self._post("/v1/chat/completions", payload)
        except BackendError as e:
            # some providers reject response_format or seed; degrade gracefully ONCE per call
            msg = str(e)
            if "response_format" in msg or "json_schema" in msg:
                payload.pop("response_format", None)
                data, ms = self._post("/v1/chat/completions", payload)
            elif "seed" in msg and "Unsupported" in msg:
                payload.pop("seed", None)
                data, ms = self._post("/v1/chat/completions", payload)
            else:
                raise
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message", {})
        usage = data.get("usage", {}) or {}
        return {
            "content": msg.get("content") or "",
            "reasoning": msg.get("reasoning_content") or msg.get("reasoning") or "",
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "done_reason": choice.get("finish_reason"),
            "latency_ms": ms,
        }


def make_backend(kind, base_url, model, **kw):
    if kind == "ollama":
        return OllamaBackend(base_url, model, **kw)
    if kind == "vllm":
        return VLLMBackend(base_url, model, **{k: v for k, v in kw.items() if k != "num_ctx"})
    if kind == "openai":
        return OpenAICompatBackend(base_url, model, **{k: v for k, v in kw.items() if k != "num_ctx"})
    raise ValueError("unknown backend {}".format(kind))
