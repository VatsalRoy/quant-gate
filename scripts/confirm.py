"""Confirmation: full benchmarks on every suspect + a fixed random sample of 10 passers.
The selection is saved on first run and never changes. Resumable."""
import argparse
import csv
import json
import random
import shutil
import sys
import time
import traceback
from pathlib import Path

from huggingface_hub import hf_hub_download

from quant_gate.cli import run_gate

CENSUS = Path("results/census.csv")
INV = Path("results/inventory.csv")
SEL = Path("results/confirm_selection.json")
OUT = Path("results/confirm.csv")
REPORTS = Path("results/reports/confirm")
WORK = Path("models/census")
LOCAL = Path("models")
KL_BASE = "models/LFM3-1.7B-BF16.kld"
ALREADY_FULL = {("LiquidAI/LFM3-1.7B-GGUF", "LFM3-1.7B-BF16.gguf"),
                ("LiquidAI/LFM3-1.7B-GGUF", "LFM3-1.7B-Q8_0.gguf")}

FIELDS = ["repo", "uploader", "filename", "quant", "group", "screen_verdict", "full_verdict",
          "code_full", "tool_full", "tool_clean", "code_truncated", "code_leaked",
          "mean_kld", "reasons", "seconds"]


def select() -> dict:
    if SEL.exists():
        return json.loads(SEL.read_text())
    rows = list(csv.DictReader(CENSUS.open()))
    suspects = [r for r in rows if r["verdict"] != "pass"]
    passers = [r for r in rows if r["verdict"] == "pass"
               and (r["repo"], r["filename"]) not in ALREADY_FULL]
    sample = random.Random(7).sample(passers, 10)
    # NVFP4 last: if it generates garbage, its full run is very slow
    suspects.sort(key=lambda r: "NVFP4" in r["filename"])
    sel = {"seed": 7,
           "suspects": [[r["repo"], r["filename"]] for r in suspects],
           "passers": [[r["repo"], r["filename"]] for r in sample]}
    SEL.write_text(json.dumps(sel, indent=1))
    print(f"Saved selection: {len(suspects)} suspects + {len(sample)} passers -> {SEL}")
    return sel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--skip", nargs="*", default=[], help="filenames to skip this run")
    args = ap.parse_args()

    sel = select()
    census = {(r["repo"], r["filename"]): r for r in csv.DictReader(CENSUS.open())}
    inv = {(r["repo"], r["filename"]): r for r in csv.DictReader(INV.open())}
    done = set()
    if OUT.exists():
        done = {(r["repo"], r["filename"]) for r in csv.DictReader(OUT.open())}

    # passers first, then suspects (NVFP4 is already last among suspects)
    todo = [("passer", tuple(k)) for k in sel["passers"]] + [("suspect", tuple(k)) for k in sel["suspects"]]
    todo = [(g, k) for g, k in todo if k not in done and k[1] not in args.skip]
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(done)} done, {len(todo)} to run now")

    REPORTS.mkdir(parents=True, exist_ok=True)
    for i, (group, key) in enumerate(todo, 1):
        t0 = time.time()
        row = inv[key]
        local = LOCAL / row["filename"]
        reuse = row["uploader"] == "official" and local.exists()
        print(f"[{i}/{len(todo)}] {group}: {row['uploader']}/{row['filename']}")
        if reuse:
            path = local
        else:
            need = int(row["size_bytes"]) + 2 * 10**9
            if shutil.disk_usage(".").free < need:
                sys.exit("Stopping: not enough disk space. Free some and rerun.")
            path = Path(hf_hub_download(row["repo"], row["filename"], revision=row["revision"],
                                        local_dir=WORK / row["uploader"]))
        try:
            rep = run_gate(path, KL_BASE, full=True)
        except Exception:
            traceback.print_exc()
            sys.exit("HARNESS ERROR: stopping so no fake results are recorded.")

        (REPORTS / f"{row['uploader']}__{Path(row['filename']).stem}.json").write_text(
            json.dumps(rep, indent=2, default=str))
        t, c = rep.get("tool", {}), rep.get("code", {})
        out = {
            "repo": row["repo"], "uploader": row["uploader"], "filename": row["filename"],
            "quant": row["quant"], "group": group,
            "screen_verdict": census[key]["verdict"], "full_verdict": rep["verdict"],
            "code_full": c.get("solved_plus", ""),
            "tool_full": round(t["score"] * t["n"]) if t else "",
            "tool_clean": t.get("clean_rate", ""),
            "code_truncated": c.get("truncated", ""), "code_leaked": c.get("leaked_thinking", ""),
            "mean_kld": rep.get("kl", {}).get("mean_kld", ""),
            "reasons": " | ".join(rep.get("reasons", [])),
            "seconds": round(time.time() - t0, 1),
        }
        new = not OUT.exists()
        with OUT.open("a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if new:
                w.writeheader()
            w.writerow(out)
        print(f"   -> screen {out['screen_verdict'].upper()} | full {out['full_verdict'].upper()}  "
              f"code {out['code_full']}/164  tool {out['tool_full']}/60  {out['seconds']:.0f}s")
        if not reuse:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()