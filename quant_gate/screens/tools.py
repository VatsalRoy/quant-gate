"""Run tool-call / strict-JSON cases against a server and check answers exactly."""
import json
import re
import time
from quant_gate.server import split_think

FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.S)


def _norm(s: str) -> str:
    return s.replace("\u2019", "'").strip().casefold()


def same_value(exp, got) -> bool:
    if isinstance(exp, bool):
        return got is exp
    if isinstance(exp, int):
        return isinstance(got, int) and not isinstance(got, bool) and got == exp
    if isinstance(exp, float):
        return isinstance(got, (int, float)) and not isinstance(got, bool) and abs(got - exp) < 1e-6
    if isinstance(exp, str):
        return isinstance(got, str) and _norm(got) == _norm(exp)
    return got == exp


def compare_obj(exp: dict, got) -> str:
    if not isinstance(got, dict):
        return "not_object"
    if set(got) != set(exp):
        return "wrong_keys"
    for k, v in exp.items():
        if not same_value(v, got[k]):
            return f"wrong_value:{k}"
    return "ok"


def check_tool(case: dict, msg: dict) -> tuple[str, bool]:
    calls = msg.get("tool_calls") or []
    if not calls:
        return "no_tool_call", False
    if len(calls) > 1:
        return "multiple_calls", False
    fn = calls[0].get("function", {})
    if fn.get("name") != case["expected"]["name"]:
        return "wrong_name", False
    args = fn.get("arguments")
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            return "bad_args_json", False
    clean = not (msg.get("content") or "").strip()  # no stray text alongside the call
    return compare_obj(case["expected"]["arguments"], args), clean


def extract_json(text: str):
    """Return (obj, clean). clean=True if the reply was only JSON (optionally fenced)."""
    t = text.strip()
    m = FENCE_RE.match(t)
    if m:
        return json.loads(m.group(1)), True
    try:
        return json.loads(t), True
    except json.JSONDecodeError:
        pass
    start = t.find("{")  # lenient: first JSON object anywhere in the reply
    if start == -1:
        raise ValueError("no JSON object found")
    obj, _ = json.JSONDecoder().raw_decode(t[start:])
    return obj, False


def check_json(case: dict, msg: dict) -> tuple[str, bool]:
    try:
        obj, clean = extract_json(msg.get("content") or "")
    except (ValueError, json.JSONDecodeError):
        return "not_json", False
    return compare_obj(case["expected"], obj), clean


def run(srv, cases: list[dict], max_tokens: int = 256) -> list[dict]:
    results = []
    for c in cases:
        t0 = time.time()
        msg, clean = {}, False 
        leaked = ""
        try:
            out = srv.chat(c["messages"], max_tokens=max_tokens, tools=c.get("tools"))
            ch = out["choices"][0]
            msg = ch["message"]
            leaked, answer = split_think(msg.get("content"))
            msg = {**msg, "content": answer}
            if ch.get("finish_reason") == "length":
                reason = "truncated"
            elif c["kind"] == "tool":
                reason, clean = check_tool(c, msg)
            else:
                reason, clean = check_json(c, msg)
        except Exception as e:
            reason = f"request_error:{type(e).__name__}"
        results.append({
            "id": c["id"], "kind": c["kind"], "ok": reason == "ok", "clean": clean,
            "reason": reason,
            "content": (msg.get("content") or "")[:500],
            "tool_calls": msg.get("tool_calls"),
            "seconds": round(time.time() - t0, 2),
            "leaked_thinking": bool(leaked),
            })
    return results


def summarize(results: list[dict]) -> dict:
    def rate(rs, key="ok"):
        return round(sum(r[key] for r in rs) / len(rs), 3) if rs else None
    tool_rs = [r for r in results if r["kind"] == "tool"]
    json_rs = [r for r in results if r["kind"] == "json"]
    return {
        "n": len(results),
        "score": rate(results),
        "tool_score": rate(tool_rs),
        "json_score": rate(json_rs),
        "clean_rate": rate(results, "clean"),
        "failures": {r["id"]: r["reason"] for r in results if not r["ok"]},
        "unclean": [r["id"] for r in results if r["ok"] and not r["clean"]],
        "leaked_thinking": sum(r.get("leaked_thinking", False) for r in results),
    }