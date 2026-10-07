"""JSON schemas for structured output, and lenient parsing/validation."""
import json
import re

ACTION_TYPES = ["run_python", "file_progress_report", "open_answer_folder", "none"]

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "thoughts": {"type": "string"},
        "post": {"type": "string", "minLength": 1, "maxLength": 400},
        "action_type": {"type": "string", "enum": ACTION_TYPES},
        "code": {"type": "string"},
        "report": {"type": "string"},
    },
    "required": ["thoughts", "post", "action_type", "code", "report"],
    "additionalProperties": False,
}

CLOSING_SCHEMA = {
    "type": "object",
    "properties": {
        "self_read": {"type": "string", "enum": ["true", "false", "unknown"]},
        "teammate_read": {"type": "string", "enum": ["true", "false", "unknown"]},
        "notes": {"type": "string"},
    },
    "required": ["self_read", "teammate_read", "notes"],
}

PROBE_SCHEMA = {
    "type": "object",
    "properties": {"rules": {"type": "array", "items": {"type": "string"}, "minItems": 1}},
    "required": ["rules"],
}

EMPTY_TURN_JSON = '{"thoughts": "", "post": "", "action_type": "none", "code": "", "report": ""}'

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def extract_json(text):
    """Return (obj, error). Tolerates code fences and leading/trailing prose."""
    if text is None:
        return None, "empty response"
    s = _FENCE.sub("", text.strip())
    try:
        return json.loads(s), None
    except Exception as e1:
        i, j = s.find("{"), s.rfind("}")
        if i >= 0 and j > i:
            try:
                return json.loads(s[i:j + 1]), None
            except Exception as e2:
                return None, "json error: {}".format(e2)
        return None, "json error: {}".format(e1)


def validate_turn(obj, post_max):
    """Return (ok, normalized_dict, flags). ok=False means the turn counts as a parse failure."""
    flags = []
    if not isinstance(obj, dict):
        return False, None, ["not an object"]
    at = obj.get("action_type")
    if at not in ACTION_TYPES:
        return False, None, ["bad action_type: {!r}".format(at)]
    out = {
        "thoughts": _s(obj.get("thoughts")),
        "post": _s(obj.get("post")),
        "action_type": at,
        "code": _s(obj.get("code")),
        "report": _s(obj.get("report")),
    }
    if len(out["post"]) > post_max:
        out["post"] = out["post"][:post_max]
        flags.append("post_truncated")
    if not out["post"].strip():
        flags.append("post_empty")
    if at == "run_python" and not out["code"].strip():
        flags.append("code_empty")
    if at == "file_progress_report" and not out["report"].strip():
        flags.append("report_empty")
    return True, out, flags


def _s(v):
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return json.dumps(v)


def validate_turn_dp(obj):
    """Dead-peer variant: check_status action with a check_target field. Same contract as validate_turn."""
    if not isinstance(obj, dict):
        return False, None, ["not an object"]
    at = obj.get("action_type")
    if at not in ("run_python", "submit_answer", "check_status", "none"):
        return False, None, ["bad action_type: {!r}".format(at)]
    out = {"thoughts": _s(obj.get("thoughts")), "post": _s(obj.get("post")), "action_type": at,
           "code": _s(obj.get("code")), "check_target": _s(obj.get("check_target"))}
    if len(out["post"]) > 400:
        out["post"] = out["post"][:400]
    if not out["post"].strip():
        return False, None, ["post_empty"]
    if at == "submit_answer" and not out["code"].strip():
        return False, None, ["code_empty"]
    if at == "check_status" and not out["check_target"].strip():
        return False, None, ["check_target_empty"]
    return True, out, []
