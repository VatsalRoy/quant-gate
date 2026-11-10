"""Full gate on the 6 rebuilt files; screen results derived from the full run. Resumable."""
import csv
import json
from pathlib import Path

from quant_gate import thresholds as T
from quant_gate.cli import run_gate

OUT = Path("models/rebuild")
KL_BASE = "models/LFM3-1.7B-BF16.kld"
CSV = Path("results/rebuild.csv")
REPORTS = Path("results/reports/rebuild")
REPORTS.mkdir(parents=True, exist_ok=True)

SCREEN_CODE = set(json.load(open("data/code_screen_tasks.json")))
SCREEN_TOOL = {json.loads(l)["id"] for l in open("data/tool_cases.jsonl") if json.loads(l)["screen"]}
FIELDS = ["quant", "arm", "size_bytes", "mean_kld", "top1_agree_pct",
          "code_full", "tool_full", "full_verdict", "code_screen", "tool_screen", "screen_verdict",
          "code_truncated", "code_leaked", "seconds"]


def derived_screen(rep):
    code_s = len(SCREEN_CODE) - len(SCREEN_CODE & set(rep["code"]["failed"]))
    tool_s = len(SCREEN_TOOL) - len(SCREEN_TOOL & set(rep["tool"]["failures"]))
    v = "pass" if code_s >= T.SCREEN_CODE_MIN and tool_s >= T.SCREEN_TOOL_MIN else "suspect"
    return code_s, tool_s, v


done = set()
if CSV.exists():
    done = {(r["quant"], r["arm"]) for r in csv.DictReader(CSV.open())}

for q in ["Q2_K", "Q3_K_S", "Q3_K_M"]:
    for arm in ["plain", "imatrix", "bartimatrix"]:
        if (q, arm) in done:
            continue
        path = OUT / f"LFM3-1.7B-rebuild-{q}-{arm}.gguf"
        print(f"{q} {arm} ...")
        rep = run_gate(path, KL_BASE, full=True)
        (REPORTS / f"{path.stem}_full.json").write_text(json.dumps(rep, indent=2, default=str))
        cs, ts, sv = derived_screen(rep)
        row = {"quant": q, "arm": arm, "size_bytes": rep["size_bytes"],
               "mean_kld": rep["kl"].get("mean_kld"), "top1_agree_pct": rep["kl"].get("top1_agree_pct"),
               "code_full": rep["code"]["solved_plus"],
               "tool_full": round(rep["tool"]["score"] * rep["tool"]["n"]),
               "full_verdict": rep["verdict"], "code_screen": cs, "tool_screen": ts,
               "screen_verdict": sv, "code_truncated": rep["code"]["truncated"],
               "code_leaked": rep["code"]["leaked_thinking"], "seconds": rep["total_seconds"]}
        new = not CSV.exists()
        with CSV.open("a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if new:
                w.writeheader()
            w.writerow(row)
        print(f"   -> full {row['full_verdict'].upper()}  code {row['code_full']}/164  "
              f"tool {row['tool_full']}/60  KL {row['mean_kld']}  "
              f"(screen derived: {cs}/15, {ts}/20 -> {sv})")

# determinism check: real screen run on one file must match the derived screen
chk = OUT / "LFM3-1.7B-rebuild-Q3_K_M-plain.gguf"
real = run_gate(chk, None, full=False)
row = next(r for r in csv.DictReader(CSV.open()) if r["quant"] == "Q3_K_M" and r["arm"] == "plain")
print(f"\nDeterminism check (Q3_K_M plain): real screen code {real['code']['solved_plus']}/15, "
      f"tool {round(real['tool']['score'] * real['tool']['n'])}/20  |  derived {row['code_screen']}/15, "
      f"{row['tool_screen']}/20")