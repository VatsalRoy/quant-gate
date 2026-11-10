"""Paired plain-vs-imatrix comparison per quant type (exact McNemar test)."""
import json
import math
from pathlib import Path

from quant_gate.screens.code import load_tasks

R = Path("results/reports/rebuild")
ALL_CODE = set(load_tasks())
ALL_TOOL = {json.loads(l)["id"] for l in open("data/tool_cases.jsonl")}


def failed_sets(q, arm):
    rep = json.load(open(R / f"LFM3-1.7B-rebuild-{q}-{arm}_full.json"))
    return set(rep["code"]["failed"]), set(rep["tool"]["failures"])


def mcnemar_p(b, c):
    """Exact two-sided McNemar p-value from the two discordant counts."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n
    return round(min(1.0, 2 * tail), 4)


out = []
for q in ["Q2_K", "Q3_K_S", "Q3_K_M"]:
    (pc, pt), (ic, it) = failed_sets(q, "plain"), failed_sets(q, "imatrix")
    for kind, allids, pf, imf in [("code", ALL_CODE, pc, ic), ("tool", ALL_TOOL, pt, it)]:
        only_plain = len(imf - pf)    # plain solved, imatrix failed
        only_imx = len(pf - imf)      # imatrix solved, plain failed
        row = {"quant": q, "kind": kind,
               "plain_solved": len(allids) - len(pf), "imatrix_solved": len(allids) - len(imf),
               "only_plain_solved": only_plain, "only_imatrix_solved": only_imx,
               "p_value": mcnemar_p(only_plain, only_imx)}
        out.append(row)
        print(f"{q:7s} {kind:4s}  plain {row['plain_solved']:3d}  imatrix {row['imatrix_solved']:3d}  "
              f"| only-plain {only_plain:3d}  only-imatrix {only_imx:3d}  p = {row['p_value']}")

Path("results/rebuild_stats.json").write_text(json.dumps(out, indent=2))
print("\nSaved results/rebuild_stats.json")