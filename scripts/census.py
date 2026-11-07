"""Census: download -> gate (screen) -> record -> delete, for every file in inventory.csv.
Resumable: rerun the same command and it skips files already in census.csv."""
import argparse
import csv
import json
import shutil
import sys
import time
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from huggingface_hub import hf_hub_download

from quant_gate.cli import run_gate

INV = Path("results/inventory.csv")
OUT = Path("results/census.csv")
REPORTS = Path("results/reports/census")
KL_BASE = "models/LFM3-1.7B-BF16.kld"
WORK = Path("models/census")      # temporary downloads (gitignored via models/)
LOCAL = Path("models")            # official files already here are reused and kept

FIELDS = ["repo", "uploader", "filename", "quant", "variant", "size_gb", "approx_bpw",
          "imatrix_per_card", "imatrix_in_metadata", "template", "tensor_types",
          "tool_screen", "tool_clean", "tool_leaked",
          "code_screen", "code_truncated", "code_leaked",
          "mean_kld", "kld_p99", "top1_agree_pct", "ppl_q",
          "verdict", "reasons", "sha_match", "seconds", "llama_cpp", "timestamp"]


def done_keys() -> set:
    if not OUT.exists():
        return set()
    with OUT.open() as f:
        return {(r["repo"], r["filename"]) for r in csv.DictReader(f)}


def append(row: dict):
    new = not OUT.exists()
    with OUT.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


def flatten(inv: dict, rep: dict, sha_ok, secs: float) -> dict:
    md, t, c, k = (rep.get("metadata", {}), rep.get("tool", {}),
                   rep.get("code", {}), rep.get("kl", {}))
    return {
        **{x: inv[x] for x in ["repo", "uploader", "filename", "quant", "variant",
                               "size_gb", "approx_bpw", "imatrix_per_card"]},
        "imatrix_in_metadata": md.get("imatrix_used", ""),
        "template": md.get("chat_template_present", ""),
        "tensor_types": ";".join(f"{a}:{b}" for a, b in md.get("tensor_types", {}).items()),
        "tool_screen": round(t["score"] * t["n"]) if t else "",
        "tool_clean": t.get("clean_rate", ""),
        "tool_leaked": t.get("leaked_thinking", ""),
        "code_screen": c.get("solved_plus", ""),
        "code_truncated": c.get("truncated", ""),
        "code_leaked": c.get("leaked_thinking", ""),
        "mean_kld": k.get("mean_kld", ""),
        "kld_p99": k.get("kld_p99", ""),
        "top1_agree_pct": k.get("top1_agree_pct", ""),
        "ppl_q": k.get("ppl_q", ""),
        "verdict": rep["verdict"],
        "reasons": " | ".join(rep.get("reasons", [])),
        "sha_match": sha_ok,
        "seconds": round(secs, 1),
        "llama_cpp": rep.get("llama_cpp", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uploader", help="only this uploader (official, bartowski, prithivMLmods, AtomicChat)")
    ap.add_argument("--limit", type=int, help="stop after N files (for a test run)")
    ap.add_argument("--keep", action="store_true", help="don't delete downloaded files")
    args = ap.parse_args()

    rows = list(csv.DictReader(INV.open()))
    if args.uploader:
        rows = [r for r in rows if r["uploader"] == args.uploader]
    done = done_keys()
    todo = [r for r in rows if (r["repo"], r["filename"]) not in done]
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(done)} already done, {len(todo)} to run now")

    REPORTS.mkdir(parents=True, exist_ok=True)
    for i, inv in enumerate(todo, 1):
        t0 = time.time()
        label = f"[{i}/{len(todo)}] {inv['uploader']}/{inv['filename']}"
        local = LOCAL / inv["filename"]
        reuse = inv["uploader"] == "official" and local.exists()

        if reuse:
            path = local
            print(f"{label}  (using local copy)")
        else:
            need = int(inv["size_bytes"]) + 2 * 10**9
            free = shutil.disk_usage(".").free
            if free < need:
                sys.exit(f"Stopping: need {need/1e9:.1f} GB free, have {free/1e9:.1f} GB. "
                         f"Free some space and rerun; finished files are kept.")
            print(f"{label}  downloading {inv['size_gb']} GB ...")
            path = Path(hf_hub_download(inv["repo"], inv["filename"], revision=inv["revision"],
                                        local_dir=WORK / inv["uploader"]))

        try:
            rep = run_gate(path, KL_BASE)
        except Exception:
            traceback.print_exc()
            sys.exit("HARNESS ERROR: stopping the census so no fake results are recorded. "
                     "Fix the problem and rerun; finished files are kept.")

        sha_ok = (rep["sha256"] == inv["sha256"]) if inv["sha256"] else "unknown"
        report_path = REPORTS / f"{inv['uploader']}__{Path(inv['filename']).stem}.json"
        report_path.write_text(json.dumps(rep, indent=2, default=str))
        append(flatten(inv, rep, sha_ok, time.time() - t0))

        k = rep.get("kl", {})
        print(f"   -> {rep['verdict'].upper()}  code {rep.get('code', {}).get('solved_plus', '-')}/15  "
              f"tool {round(rep['tool']['score'] * rep['tool']['n']) if 'tool' in rep else '-'}/20  "
              f"KL {k.get('mean_kld', '-')}  sha_ok={sha_ok}  {time.time() - t0:.0f}s")

        if not reuse and not args.keep:
            path.unlink(missing_ok=True)

    if OUT.exists():
        with OUT.open() as f:
            verdicts = Counter(r["verdict"] for r in csv.DictReader(f))
        print("\nCensus so far:", dict(verdicts))


if __name__ == "__main__":
    main()