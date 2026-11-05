"""Compare BF16 vs Q8_0 task-by-task -> results/baselines.json"""
import json
import math

def load(path):
    return {r["id" if "id" in r else "task_id"]: r
            for r in json.load(open(path))["results"]}

out = {}
for kind, a_path, b_path, key in [
    ("code", "results/code_LFM3-1.7B-BF16_full.json", "results/code_LFM3-1.7B-Q8_0_full.json", "plus"),
    ("tools", "results/tools_LFM3-1.7B-BF16_full.json", "results/tools_LFM3-1.7B-Q8_0_full.json", "ok"),
]:
    a, b = load(a_path), load(b_path)
    ids = sorted(a)
    bf_only = [i for i in ids if a[i][key] and not b[i][key]]
    q8_only = [i for i in ids if b[i][key] and not a[i][key]]
    n = len(ids)
    flips = len(bf_only) + len(q8_only)
    out[kind] = {
        "n": n,
        "bf16_score": round(sum(a[i][key] for i in ids) / n, 3),
        "q8_0_score": round(sum(b[i][key] for i in ids) / n, 3),
        "bf16_only_pass": bf_only,
        "q8_0_only_pass": q8_only,
        "flips": flips,
        # rough standard error of a paired score difference, in percentage points
        "paired_se_pts": round(100 * math.sqrt(flips) / n, 2),
    }
    print(f"{kind}: BF16 {out[kind]['bf16_score']}  Q8_0 {out[kind]['q8_0_score']}  "
          f"flips {flips} (BF16-only {len(bf_only)}, Q8_0-only {len(q8_only)})  "
          f"paired SE ~{out[kind]['paired_se_pts']} pts")

json.dump(out, open("results/baselines.json", "w"), indent=2)
print("Saved results/baselines.json")