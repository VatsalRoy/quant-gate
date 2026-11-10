"""Merge census + confirmation, test H1-H4, compute screen error rates, draw figures."""
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from quant_gate import thresholds as T

R, F = Path("results"), Path("figures")
F.mkdir(exist_ok=True)
COLORS = {"official": "#1f77b4", "bartowski": "#d62728",
          "prithivMLmods": "#2ca02c", "AtomicChat": "#9467bd"}
out = {}


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0, c - h), 3), round(min(1, c + h), 3)]


def full_verdict(code, tool):
    if pd.isna(code):
        return None
    if code < T.NONFUNC_CODE_BELOW or tool < T.NONFUNC_TOOL_BELOW:
        return "non_functional"
    if code < T.FUNCTIONAL_CODE_MIN or tool < T.FUNCTIONAL_TOOL_MIN:
        return "degraded"
    return "functional"


# ---------- 1. merge ----------
census = pd.read_csv(R / "census.csv")
confirm = pd.read_csv(R / "confirm.csv")


def baseline_row(stem, filename):
    c = json.load(open(R / f"code_{stem}_full.json"))["summary"]
    t = json.load(open(R / f"tools_{stem}_full.json"))["summary"]
    return {"repo": "LiquidAI/LFM3-1.7B-GGUF", "filename": filename, "group": "baseline",
            "code_full": c["solved_plus"], "tool_full": round(t["score"] * t["n"]),
            "code_truncated": c["truncated"], "code_leaked": c["leaked_thinking"], "seconds": None}


full = pd.concat([confirm, pd.DataFrame([
    baseline_row("LFM3-1.7B-BF16", "LFM3-1.7B-BF16.gguf"),
    baseline_row("LFM3-1.7B-Q8_0", "LFM3-1.7B-Q8_0.gguf")])], ignore_index=True)
full = full[["repo", "filename", "group", "code_full", "tool_full",
             "code_truncated", "code_leaked", "seconds"]].rename(columns={
    "code_truncated": "full_truncated", "code_leaked": "full_leaked", "seconds": "full_seconds"})

df = census.merge(full, on=["repo", "filename"], how="left")
df["variant"] = df["variant"].fillna("")
df["imatrix"] = df["imatrix_in_metadata"].astype(str) == "True"
df["label"] = df.apply(lambda r: (r["variant"] + "-" if r["variant"] else "") + r["quant"], axis=1)
df["full_verdict"] = [full_verdict(c, t) for c, t in zip(df["code_full"], df["tool_full"])]
nv = df["filename"].str.contains("NVFP4")
df.loc[nv, "full_verdict"] = "non_functional"   # screen 0/15, 0/20; full skipped (see findings_nvfp4.md)
df["full_source"] = df["code_full"].notna().map({True: "full", False: ""})
df.loc[nv, "full_source"] = "screen evidence"
df.to_csv(R / "summary.csv", index=False)

# ---------- 2. how good is the screen? ----------
passers = df[df["group"] == "passer"]
misses = passers[passers["full_verdict"] != "functional"]
sus = df[(df["verdict"] == "suspect") & df["code_full"].notna()]
false_alarms = sus[sus["full_verdict"] == "functional"]
out["screen"] = {
    "passers_sampled": len(passers),
    "misses": len(misses), "miss_files": (misses["uploader"] + "/" + misses["label"]).tolist(),
    "miss_rate_wilson95": wilson(len(misses), len(passers)),
    "suspects_confirmed": len(sus),
    "false_alarms": len(false_alarms),
    "false_alarm_files": (false_alarms["uploader"] + "/" + false_alarms["label"]).tolist(),
    "false_alarm_rate_wilson95": wilson(len(false_alarms), len(sus)),
    "median_screen_seconds": float(df["seconds"].median()),
    "median_full_seconds": float(df["full_seconds"].median()),
}

# ---------- 3. H3: best single KL cutoff vs the task screen ----------
lab = df[df["full_verdict"].notna()].copy()
lab["bad"] = lab["full_verdict"] != "functional"
best = None
for c in sorted(lab["mean_kld"].unique()):
    pred_bad = lab["mean_kld"] > c
    wrong = lab[pred_bad != lab["bad"]]
    if best is None or len(wrong) < best[1]:
        best = (c, len(wrong), wrong)
c, n_wrong, wrong = best
task_wrong = lab[(lab["verdict"] != "pass") != lab["bad"]]
fl = lab[lab["full_source"] == "full"]
out["H3"] = {
    "files_with_verdict": len(lab),
    "spearman_kl_vs_full_code": round(fl[["mean_kld", "code_full"]].corr("spearman").iloc[0, 1], 3),
    "best_kl_cutoff": c,
    "kl_cutoff_errors": n_wrong,
    "kl_cutoff_wrong": [f"{r.uploader}/{r.label} (KL {r.mean_kld}, {r.full_verdict})"
                        for r in wrong.itertuples()],
    "task_screen_errors": len(task_wrong),
    "task_screen_wrong": [f"{r.uploader}/{r.label} (screen {r.verdict}, full {r.full_verdict})"
                          for r in task_wrong.itertuples()],
}

# ---------- 4. H2: same quant name, imatrix vs plain ----------
pairs = []
for q in sorted(df["quant"].unique()):
    imx = df[(df["quant"] == q) & (df["uploader"] == "bartowski") & df["imatrix"]]
    plain = df[(df["quant"] == q) & df["uploader"].isin(["official", "prithivMLmods"])
               & ~df["imatrix"] & (df["variant"] == "")]
    if len(imx) and len(plain):
        a, b = imx.iloc[0], plain.iloc[0]
        pairs.append({"quant": q, "kl_imatrix": a["mean_kld"], "kl_plain": b["mean_kld"],
                      "kl_reduction_pct": round(100 * (1 - a["mean_kld"] / b["mean_kld"]), 1)
                      if b["mean_kld"] else None,
                      "code_full_imatrix": a["code_full"], "code_full_plain": b["code_full"],
                      "plain_from": b["uploader"]})
out["H2_pairs"] = pairs

# ---------- 5. H1 / H4 tables ----------
fl = fl.sort_values("approx_bpw")
out["H1_full_by_bpw"] = [f"{r.approx_bpw:5.2f} bpw  {r.uploader:13s} {r.label:10s} "
                         f"code {int(r.code_full):3d}  tool {int(r.tool_full):2d}  {r.full_verdict}"
                         for r in fl.itertuples()]
out["secondary_leak_vs_bpw_spearman"] = round(
    df[["approx_bpw", "code_leaked"]].corr("spearman").iloc[0, 1], 3)
out["secondary_trunc_vs_bpw_spearman"] = round(
    df[["approx_bpw", "code_truncated"]].corr("spearman").iloc[0, 1], 3)

(R / "analysis.json").write_text(json.dumps(out, indent=2, default=str))

# ---------- 6. figures ----------
def scatter_by_uploader(ax, d, x, y, label_if=None):
    for up, g in d.groupby("uploader"):
        ax.scatter(g[x], g[y], c=COLORS[up], label=up, s=40,
                   edgecolors=["black" if i else "none" for i in g["imatrix"]])
        if label_if:
            for r in g.itertuples():
                if label_if(r):
                    ax.annotate(r.label, (getattr(r, x), getattr(r, y)), fontsize=7,
                                xytext=(4, 3), textcoords="offset points")


KEY = {"NVFP4", "QAD-Q4_0", "IQ2_M", "Q2_K", "AD-IQ3_S", "Q8_0"}


# Fig 1: KL vs bits per weight, all 45
d = df.copy()
d["kl_plot"] = d["mean_kld"].clip(lower=1e-6)
fig, ax = plt.subplots(figsize=(8, 5))
scatter_by_uploader(ax, d, "approx_bpw", "kl_plot", label_if=lambda r: r.label in KEY)
ax.set_xlim(2.5, 9)
ax.text(8.9, 2e-6, "BF16/F16 (16 bpw, KL≈0) not shown", ha="right", fontsize=7, color="gray")
ax.set_yscale("log")
ax.set_xlabel("file bits per weight")
ax.set_ylabel("mean KL vs BF16 (log; 0 shown as 1e-6)")
ax.set_title("Drift from BF16 vs file size (black edge = imatrix in metadata)")
ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(F / "fig1_kl_vs_bpw.png", dpi=150); plt.close(fig)

# Fig 2: full code score vs bits per weight
fig, ax = plt.subplots(figsize=(8, 5))
scatter_by_uploader(ax, fl, "approx_bpw", "code_full",
                    label_if=lambda r: r.code_full < T.FUNCTIONAL_CODE_MIN or r.label in KEY)
ax.set_xlim(2.5, 9)
for yv, name, ls in [(T.BF16_CODE_PLUS, "BF16", "-"), (T.FUNCTIONAL_CODE_MIN, "functional", "--"),
                     (T.NONFUNC_CODE_BELOW, "non-functional", ":")]:
    ax.axhline(yv, color="gray", ls=ls, lw=1)
    ax.text(ax.get_xlim()[1], yv, f" {name}", va="center", fontsize=7)
ax.set_xlabel("file bits per weight"); ax.set_ylabel("HumanEval+ solved (of 164)")
ax.set_title("Full code benchmark vs file size")
ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(F / "fig2_code_vs_bpw.png", dpi=150); plt.close(fig)

# Fig 3: KL vs full code (H3)
fig, ax = plt.subplots(figsize=(8, 5))
g = lab.copy()
g["kl_plot"] = g["mean_kld"].clip(lower=1e-6)
g["code_plot"] = g["code_full"].fillna(0)
for v, col in [("functional", "#2ca02c"), ("degraded", "#ff7f0e"), ("non_functional", "#d62728")]:
    s = g[(g["full_verdict"] == v) & (g["full_source"] == "full")]
    ax.scatter(s["kl_plot"], s["code_plot"], c=col, label=v, s=45)
s = g[g["full_source"] == "screen evidence"]
ax.scatter(s["kl_plot"], s["code_plot"], facecolors="none", edgecolors="#d62728", s=90,
           label="non_functional (screen evidence)")
for r in g.itertuples():
    if "NVFP4" in r.filename or r.variant == "QAD":
        ax.annotate(f"{r.label}", (r.kl_plot, r.code_plot), fontsize=8,
                    xytext=(5, 5), textcoords="offset points")
ax.axvline(c, color="gray", ls="--", lw=1)
ax.text(c, ax.get_ylim()[1], f" best KL cutoff {c:.3f}", fontsize=7, va="top")
ax.set_xscale("log")
ax.set_xlabel("mean KL vs BF16 (log)"); ax.set_ylabel("HumanEval+ solved (of 164)")
ax.set_title("Does KL predict real task failure? (H3)")
ax.legend(fontsize=7)
fig.tight_layout(); fig.savefig(F / "fig3_kl_vs_code.png", dpi=150); plt.close(fig)

# Fig 4: code vs tool degradation relative to BF16 (H4)
fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(fl["approx_bpw"], fl["code_full"] / T.BF16_CODE_PLUS, label="code (vs BF16)", marker="o")
ax.scatter(fl["approx_bpw"], fl["tool_full"] / T.BF16_TOOL, label="tool/JSON (vs BF16)", marker="s")
ax.set_xlim(2.5, 9)
ax.axhline(1.0, color="gray", lw=1)
ax.set_xlabel("file bits per weight"); ax.set_ylabel("score relative to BF16")
ax.set_title("Which breaks first as bits go down? (H4)")
ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(F / "fig4_code_vs_tool.png", dpi=150); plt.close(fig)

# Fig 5: imatrix vs plain at the same quant name (H2)
if pairs:
    p = pd.DataFrame(pairs)
    fig, ax = plt.subplots(figsize=(8, 4))
    x = range(len(p))
    ax.bar([i - 0.2 for i in x], p["kl_plain"], width=0.4, label="plain (no imatrix)")
    ax.bar([i + 0.2 for i in x], p["kl_imatrix"], width=0.4, label="bartowski (imatrix)")
    ax.set_xticks(list(x)); ax.set_xticklabels(p["quant"])
    ax.set_ylabel("mean KL vs BF16"); ax.set_title("Same quant name, different recipe (H2)")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(F / "fig5_imatrix_pairs.png", dpi=150); plt.close(fig)

# Fig 6: controlled rebuild
rb = pd.read_csv(R / "rebuild.csv")
arms = ["plain", "imatrix", "bartimatrix"]
names = {"plain": "no imatrix",
         "imatrix": "imatrix: WikiText (200 chunks)",
         "bartimatrix": "imatrix: bartowski calib (486 chunks)"}
quants = ["Q2_K", "Q3_K_S", "Q3_K_M"]
fig, ax = plt.subplots(figsize=(8, 4.5))
w = 0.27
for i, arm in enumerate(arms):
    vals = [rb[(rb["quant"] == q) & (rb["arm"] == arm)]["code_full"].iloc[0] for q in quants]
    xs = [j + (i - 1) * w for j in range(len(quants))]
    ax.bar(xs, vals, width=w, label=names[arm])
    for x, v in zip(xs, vals):
        ax.text(x, v + 1, str(int(v)), ha="center", fontsize=7)
ax.axhline(T.BF16_CODE_PLUS, color="gray", lw=1)
ax.text(-0.45, T.BF16_CODE_PLUS + 1.5, f"BF16 ({T.BF16_CODE_PLUS})", fontsize=7, color="gray")
ax.axhline(T.FUNCTIONAL_CODE_MIN, color="gray", ls="--", lw=1)
ax.text(-0.45, T.FUNCTIONAL_CODE_MIN - 5, f"functional cutoff ({T.FUNCTIONAL_CODE_MIN})",
        fontsize=7, color="gray")
ax.set_ylim(0, 130)
ax.set_xticks(range(len(quants))); ax.set_xticklabels(quants)
ax.set_ylabel("HumanEval+ solved (of 164)")
ax.set_title("Controlled rebuild: same tensor mix, only the importance matrix differs")
ax.legend(fontsize=7, loc="center left", bbox_to_anchor=(0.0, 0.62))
fig.tight_layout(); fig.savefig(F / "fig6_rebuild.png", dpi=150); plt.close(fig)

print(json.dumps(out, indent=2, default=str))
print(f"\nSaved results/summary.csv, results/analysis.json, and {len(list(F.glob('*.png')))} figures")