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


PAIRS = [("plain", "imatrix"), ("plain", "bartimatrix"), ("imatrix", "bartimatrix")]
out = []
for q in ["Q2_K", "Q3_K_S", "Q3_K_M"]:
    for a, b in PAIRS:
        (ac, at), (bc, bt) = failed_sets(q, a), failed_sets(q, b)
        for kind, allids, fa, fb in [("code", ALL_CODE, ac, bc), ("tool", ALL_TOOL, at, bt)]:
            only_a = len(fb - fa)   # a solved, b failed
            only_b = len(fa - fb)   # b solved, a failed
            row = {"quant": q, "kind": kind, "a": a, "b": b,
                   "a_solved": len(allids) - len(fa), "b_solved": len(allids) - len(fb),
                   "only_a": only_a, "only_b": only_b, "p_value": mcnemar_p(only_a, only_b)}
            out.append(row)
            print(f"{q:7s} {kind:4s} {a:>11s} {row['a_solved']:3d} vs {b:<11s} {row['b_solved']:3d} "
                  f"| only-{a} {only_a:3d}  only-{b} {only_b:3d}  p = {row['p_value']}")

Path("results/rebuild_stats.json").write_text(json.dumps(out, indent=2))
print("\nSaved results/rebuild_stats.json")