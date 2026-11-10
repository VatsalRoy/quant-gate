"""HumanEval+ code screen: generate with the model, evaluate with EvalPlus."""
import json
import re
import subprocess
import sys
import time
from pathlib import Path
import os
import platform
from quant_gate.server import split_think

CODE_RE = re.compile(r"```(?:python|py)?[ \t]*\n(.*?)```", re.S)

PROMPT = ("Complete the following Python function. Reply with the complete function "
          "(including the signature) in a single ```python code block.\n\n{prompt}")


def load_tasks() -> dict:
    from evalplus.data import get_human_eval_plus
    return get_human_eval_plus()


def extract_solution(task: dict, reply: str) -> str:
    """Turn the model's reply into runnable code."""
    reply = reply or ""
    blocks = CODE_RE.findall(reply)
    entry = f"def {task['entry_point']}"
    code = next((b for b in blocks if entry in b), blocks[0] if blocks else reply)
    if entry not in code:
        # model wrote only the body: glue it onto the original signature
        return task["prompt"] + code
    # model wrote the whole function: keep the prompt's imports (e.g. `from typing import List`)
    imports = [l for l in task["prompt"].splitlines() if l.startswith(("import ", "from "))]
    missing = [l for l in imports if l not in code]
    return "\n".join(missing + [code])


def generate(srv, tasks: dict, task_ids: list[str], max_tokens: int = 2048,
             max_truncated: int | None = None) -> list[dict]:
    samples = []
    for tid in task_ids:
        t = tasks[tid]
        t0 = time.time()
        out = srv.chat([{"role": "user", "content": PROMPT.format(prompt=t["prompt"])}],
                       max_tokens=max_tokens)
        ch = out["choices"][0]
        raw = ch["message"].get("content") or ""
        leaked, reply = split_think(raw)
        truncated = ch.get("finish_reason") == "length"
        samples.append({
            "task_id": tid,
            # truncated = fail: any code in it may be a mid-reasoning draft, not the final answer
            "solution": "" if truncated else extract_solution(t, reply),
            "reply": reply,
            "leaked_thinking": bool(leaked),
            "leaked_chars": len(leaked),
            "finish_reason": ch.get("finish_reason"),
            "seconds": round(time.time() - t0, 2)})
        if max_truncated is not None and sum(s["finish_reason"] == "length" for s in samples) > max_truncated:
            break  # can no longer reach the screen threshold (truncated = fail)
    return samples


def evaluate(samples: list[dict], tasks: dict, workdir) -> dict:
    """Run EvalPlus on the samples. Returns {task_id: {"base": bool, "plus": bool}}."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    for f in workdir.glob("*eval_results*.json"):
        f.unlink()  # never read a stale result

    have = {s["task_id"]: s["solution"] for s in samples}
    path = workdir / "samples.jsonl"
    with path.open("w") as f:
        # EvalPlus expects every task; tasks we didn't run get an empty solution (= fail)
        for tid in tasks:
            f.write(json.dumps({"task_id": tid, "solution": have.get(tid, "")}) + "\n")

    cmd = [sys.executable, "-m", "evalplus.evaluate", "--dataset", "humaneval",
           "--samples", str(path), "--i_just_wanna_run"]
    env = os.environ.copy()
    if platform.system() == "Darwin":
        # macOS rejects EvalPlus's RLIMIT_AS memory cap, which crashes every test
        # before it runs (recorded as "timeout"). Disable the memory cap; time limits still apply.
        env["EVALPLUS_MAX_MEMORY_BYTES"] = "-1"
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    log = workdir / "evalplus.log"
    log.write_text(proc.stdout + proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(f"EvalPlus failed (code {proc.returncode}); see {log}")
    if "reliability_guard" in log.read_text():
        raise RuntimeError(f"EvalPlus sandbox setup crashed (results would be fake); see {log}")

    res_files = list(workdir.glob("*eval_results*.json"))
    if not res_files:
        raise RuntimeError(f"No EvalPlus results file in {workdir}; see {log}")
    data = json.loads(res_files[0].read_text())["eval"]

    status = {}
    for tid in have:
        r = data[tid][0]
        base = r.get("base_status") == "pass"
        status[tid] = {"base": base, "plus": base and r.get("plus_status") == "pass"}

    statuses = [data[tid][0].get("base_status") for tid in have]
    if statuses and statuses.count("timeout") / len(statuses) > 0.5:
        raise RuntimeError(f"Over half the tasks timed out; likely a harness problem. See {log}")

    return status

def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    return {
        "n": n,
        "pass1_base": round(sum(r["base"] for r in rows) / n, 3),
        "pass1_plus": round(sum(r["plus"] for r in rows) / n, 3),
        "solved_plus": sum(r["plus"] for r in rows),
        "truncated": sum(r["finish_reason"] == "length" for r in rows),
        "leaked_thinking": sum(r["leaked_thinking"] for r in rows),
        "gen_seconds": round(sum(r["seconds"] for r in rows), 1),
    }