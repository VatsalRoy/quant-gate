"""Run tool-call / strict-JSON cases against a server and check answers exactly."""
import json
import re
import time

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


def check_tool(case: dict, msg: dict) -> str:
    calls = msg.get("tool_calls") or []
    if not calls:
        return "no_tool_call"
    if len(calls) > 1:
        return "multiple_calls"
    fn = calls[0].get("function", {})
    if fn.get("name") != case["expected"]["name"]:
        return "wrong_name"
    args = fn.get("arguments")
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            return "bad_args_json"
    return compare_obj(case["expected"]["arguments"], args)


def check_json(case: dict, msg: dict) -> str:
    text = (msg.get("content") or "").strip()
    m = FENCE_RE.match(text)  # allow ```json ... ``` fences (documented leniency)
    if m:
        text = m.group(1)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return "not_json"
    return compare_obj(case["expected"], obj)


def run(srv, cases: list[dict], max_tokens: int = 256) -> list[dict]:
    results = []
    for c in cases:
        t0 = time.time()
        msg = {}
        try:
            out = srv.chat(c["messages"], max_tokens=max_tokens, tools=c.get("tools"))
            ch = out["choices"][0]
            msg = ch["message"]
            if ch.get("finish_reason") == "length":
                reason = "truncated"
            elif c["kind"] == "tool":
                reason = check_tool(c, msg)
            else:
                reason = check_json(c, msg)
        except Exception as e:
            reason = f"request_error:{type(e).__name__}"
        results.append({
            "id": c["id"], "kind": c["kind"], "ok": reason == "ok", "reason": reason,
            "content": (msg.get("content") or "")[:500],
            "tool_calls": msg.get("tool_calls"),
            "seconds": round(time.time() - t0, 2)})
    return results


def summarize(results: list[dict]) -> dict:
    def rate(rs):
        return round(sum(r["ok"] for r in rs) / len(rs), 3) if rs else None
    return {
        "n": len(results),
        "score": rate(results),
        "tool_score": rate([r for r in results if r["kind"] == "tool"]),
        "json_score": rate([r for r in results if r["kind"] == "json"]),
        "failures": {r["id"]: r["reason"] for r in results if not r["ok"]},
    }