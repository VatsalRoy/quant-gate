"""quant-gate: functional acceptance test for a quantized GGUF file."""
import argparse
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path

from quant_gate import thresholds as T
from quant_gate.config import binary_version
from quant_gate.metadata import read_metadata
from quant_gate.screens import code, kl, tools
from quant_gate.server import LlamaServer

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
EXIT = {"pass": 0, "functional": 0,
        "suspect": 1, "degraded": 1, "non_functional": 1, "packaging": 1,
        "load_error": 2}


def sha256(path, chunk=1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def decide(rep: dict, full: bool) -> tuple[str, list[str]]:
    reasons = []
    t, c = rep["tool"], rep.get("code")
    tool_ok = round(t["score"] * t["n"])

    if not rep["metadata"].get("chat_template_present"):
        return "packaging", ["no chat template in GGUF metadata"]
    if c is None:
        return "suspect", [f"tool screen {tool_ok}/{t['n']} < {T.SCREEN_TOOL_MIN} "
                           f"(fail-fast: code screen skipped)"]
    code_ok = c["solved_plus"]
    code_n = c.get("n_planned", c["n"])   # 15 even if the run stopped early

    if full:
        if code_ok < T.NONFUNC_CODE_BELOW or tool_ok < T.NONFUNC_TOOL_BELOW:
            verdict = "non_functional"
        elif code_ok < T.FUNCTIONAL_CODE_MIN or tool_ok < T.FUNCTIONAL_TOOL_MIN:
            verdict = "degraded"
        else:
            verdict = "functional"
        reasons.append(f"code {code_ok}/{code_n} (functional >= {T.FUNCTIONAL_CODE_MIN}, "
                       f"non-functional < {T.NONFUNC_CODE_BELOW}; BF16 {T.BF16_CODE_PLUS})")
        reasons.append(f"tool {tool_ok}/{t['n']} (functional >= {T.FUNCTIONAL_TOOL_MIN}, "
                       f"non-functional < {T.NONFUNC_TOOL_BELOW})")
    else:
        verdict = "pass"
        if code_ok < T.SCREEN_CODE_MIN:
            verdict = "suspect"
            reasons.append(f"code screen {code_ok}/{code_n} < {T.SCREEN_CODE_MIN}")
        if tool_ok < T.SCREEN_TOOL_MIN:
            verdict = "suspect"
            reasons.append(f"tool screen {tool_ok}/{t['n']} < {T.SCREEN_TOOL_MIN}")
        if verdict == "pass":
            reasons.append(f"code {code_ok}/{code_n}, tool {tool_ok}/{t['n']}")
    return verdict, reasons


def run_gate(model, kl_base=None, full=False, port=8080, fail_fast=False, cpu=False) -> dict:
    model = Path(model)
    t_start = time.time()
    rep = {
        "file": model.name,
        "size_bytes": model.stat().st_size,
        "sha256": sha256(model),
        "mode": "full" if full else "screen",
        "settings": T.SETTINGS,
        "metadata": read_metadata(model),
    }

    cases = [json.loads(l) for l in open(DATA / "tool_cases.jsonl")]
    if not full:
        cases = [c for c in cases if c["screen"]]
    tasks = code.load_tasks()
    code_ids = list(tasks) if full else json.load(open(DATA / "code_screen_tasks.json"))

    # 1) can llama-server load it at all?
    srv = LlamaServer(model, port=port, extra_args=["-ngl", "0"] if cpu else None)
    rep["server_binary"] = str(srv.binary)
    rep["llama_cpp"] = binary_version(srv.binary)
    try:
        srv.start()
    except (RuntimeError, TimeoutError) as e:
        rep.update(verdict="load_error", reasons=[f"llama-server could not load the file: {e}"],
                   total_seconds=round(time.time() - t_start, 1))
        return rep

    # 2) generation-based screens, one server process for both
    quick = fail_fast and not full
    samples = None
    try:
        rep["server_template_present"] = bool(srv.props().get("chat_template"))
        t0 = time.time()
        tool_res = tools.run(srv, cases)
        rep["tool"] = {**tools.summarize(tool_res), "seconds": round(time.time() - t0, 1)}
        tool_ok = round(rep["tool"]["score"] * rep["tool"]["n"])
        if not (quick and tool_ok < T.SCREEN_TOOL_MIN):
            t0 = time.time()
            samples = code.generate(
                srv, tasks, code_ids,
                max_truncated=(len(code_ids) - T.SCREEN_CODE_MIN) if quick else None)
    finally:
        srv.stop()

    # 3) run the generated code (harness errors propagate -> exit 3)
    if samples is None:
        rep["code"] = None
        rep["fail_fast"] = "code screen skipped: tool screen already below threshold"
    else:
        status = code.evaluate(samples, tasks,
                               REPO / "results" / "code_runs" / f"{model.stem}_{rep['mode']}")
        rows = [{**s, **status[s["task_id"]]} for s in samples]
        rep["code"] = {**code.summarize(rows),
                       "n_planned": len(code_ids),
                       "stopped_early": len(samples) < len(code_ids),
                       "failed": [r["task_id"] for r in rows if not r["plus"]],
                       "seconds": round(time.time() - t0, 1)}

    # 4) KL vs BF16 (reported, not a gate criterion yet)
    if kl_base:
        try:
            rep["kl"] = kl.run(model, kl_base)
        except Exception as e:
            rep["kl"] = {"error": str(e)}

    rep["verdict"], rep["reasons"] = decide(rep, full)
    rep["total_seconds"] = round(time.time() - t_start, 1)
    return rep


def print_summary(rep: dict):
    print(f"\n{rep['file']}  [{rep['mode']}]")
    md = rep["metadata"]
    if "error" not in md:
        print(f"  template: {'yes' if md['chat_template_present'] else 'NO'}   "
              f"imatrix in metadata: {'yes' if md['imatrix_used'] else 'no'}")
    if "tool" in rep:
        t = rep["tool"]
        print(f"  tool/JSON: {round(t['score'] * t['n'])}/{t['n']}  "
              f"(clean {t['clean_rate']}, leaked {t['leaked_thinking']})  {t['seconds']}s")
    if rep.get("code"):
        c = rep["code"]
        print(f"  code:      {c['solved_plus']}/{c.get('n_planned', c['n'])}  "
              f"(truncated {c['truncated']}, leaked {c['leaked_thinking']}"
              f"{', stopped early' if c.get('stopped_early') else ''})  {c['seconds']}s")
    elif rep.get("fail_fast"):
        print(f"  code:      skipped ({rep['fail_fast']})")
    if "kl" in rep:
        k = rep["kl"]
        print(f"  KL:        mean {k.get('mean_kld')}  p99 {k.get('kld_p99')}  "
              f"top-1 {k.get('top1_agree_pct')}%" if "error" not in k else f"  KL: error {k['error']}")
    print(f"  VERDICT:   {rep['verdict'].upper()}  ({'; '.join(rep['reasons'])})")
    print(f"  total:     {rep['total_seconds']}s")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="quant-gate")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="test one GGUF file")
    r.add_argument("model")
    r.add_argument("--kl-base", help="BF16 base file from llama-perplexity --kl-divergence-base")
    r.add_argument("--full", action="store_true", help="full benchmarks instead of the fast screen")
    r.add_argument("--out", help="report path (default: results/reports/<file>_<mode>.json)")
    r.add_argument("--port", type=int, default=8080)
    r.add_argument("--fail-fast", action="store_true",
                   help="screen mode: stop as soon as the file cannot pass")
    r.add_argument("--cpu", action="store_true", help="run on CPU only (-ngl 0)")
    args = ap.parse_args(argv)

    try:
        rep = run_gate(args.model, args.kl_base, args.full, args.port, args.fail_fast, args.cpu)
    except Exception as e:
        traceback.print_exc()
        print(f"HARNESS ERROR (the tester failed, not the file): {e}", file=sys.stderr)
        sys.exit(3)

    out = Path(args.out or f"results/reports/{Path(args.model).stem}_{rep['mode']}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=2, default=str))
    print_summary(rep)
    print(f"  report:    {out}")
    sys.exit(EXIT[rep["verdict"]])