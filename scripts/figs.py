"""Figures for the IEEE report (paper/figures) and README landing-page assets (assets/)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch, Patch, Circle
from matplotlib.lines import Line2D
import pandas as pd

for f in fm.findSystemFonts():
    if "Inter" in f or "DejaVuSansMono" in f:
        fm.fontManager.addfont(f)

s = pd.read_csv("results/summary.csv")
rb = pd.read_csv("results/rebuild.csv")
full = s[s.full_verdict.notna()].copy()

THEMES = {
    "light": dict(bg="#fcfcfb", ink="#0b0b0b", ink2="#52514e", grid="#e6e5e1", card="#f3f2ef", border="#dcdbd6"),
    "dark": dict(bg="#0d1117", ink="#f0efec", ink2="#c3c2b7", grid="#2a2d33", card="#161b22", border="#30363d"),
}
GOOD, WARN, CRIT, REF = "#0ca30c", "#fab219", "#d03b3b", "#9aa0a6"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"
VCOL = {"functional": GOOD, "degraded": WARN, "non_functional": CRIT}
VMARK = {"functional": "o", "degraded": "s", "non_functional": "X"}
VLABEL = {"functional": "Functional (≥110)", "degraded": "Degraded", "non_functional": "Non-functional (<59)"}


def style(theme="light", paper=False):
    t = THEMES[theme]
    plt.rcParams.update({
        "font.family": "Inter" if not paper else "DejaVu Sans",
        "font.size": 8 if paper else 11,
        "axes.facecolor": t["bg"], "figure.facecolor": t["bg"], "savefig.facecolor": t["bg"],
        "axes.edgecolor": t["ink2"], "axes.labelcolor": t["ink"], "text.color": t["ink"],
        "xtick.color": t["ink2"], "ytick.color": t["ink2"],
        "axes.grid": True, "grid.color": t["grid"], "grid.linewidth": 0.6,
        "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
        "legend.frameon": False,
    })
    return t


# ----------------------------------------------------------------- paper figures
def paper_code_vs_bpw():
    t = style(paper=True)
    fig, ax = plt.subplots(figsize=(3.5, 2.4))
    d = full[full.approx_bpw < 10]
    for v, g in d.groupby("full_verdict"):
        ax.scatter(g.approx_bpw, g.code_full, c=VCOL[v], marker=VMARK[v], s=26,
                   edgecolors=t["bg"], linewidths=0.8, label=VLABEL[v], zorder=3)
    for y, ls, txt in [(118, "-", "BF16 (118)"), (110, "--", "functional"), (59, ":", "non-functional")]:
        ax.axhline(y, color=t["ink2"], ls=ls, lw=0.7)
        ax.text(2.8, y + 1.5, txt, ha="left", fontsize=6, color=t["ink2"])
    for _, r in d.iterrows():
        if r.label in ("IQ2_M", "Q2_K", "NVFP4", "IQ4_XS") or (r.uploader == "official" and r.label == "Q5_K_M"):
            ax.annotate(r.label, (r.approx_bpw, r.code_full), xytext=(4, -3),
                        textcoords="offset points", fontsize=6, color=t["ink2"])
    ax.set_xlim(2.7, 9.1); ax.set_ylim(0, 128)
    ax.set_xlabel("Bits per weight (file size × 8 / parameters)")
    ax.set_ylabel("HumanEval+ solved (of 164)")
    ax.legend(fontsize=6, loc="lower right")
    fig.tight_layout(); fig.savefig("paper/figures/code_vs_bpw.pdf"); plt.close(fig)


def paper_kl_vs_code():
    t = style(paper=True)
    fig, ax = plt.subplots(figsize=(3.5, 2.5))
    d = full[full.mean_kld > 0]
    for v, g in d.groupby("full_verdict"):
        ax.scatter(g.mean_kld, g.code_full, c=VCOL[v], marker=VMARK[v], s=26,
                   edgecolors=t["bg"], linewidths=0.8, label=VLABEL[v], zorder=3)
    r2 = rb[(rb.quant == "Q3_K_M") & (rb.arm != "plain")]
    ax.scatter(r2.mean_kld, r2.code_full, facecolors="none", edgecolors=t["ink"], marker="D",
               s=30, linewidths=0.9, label="Rebuilt Q3_K_M (two calibrations)", zorder=4)
    ax.axvline(0.121, color=t["ink2"], ls="--", lw=0.7)
    ax.text(0.124, 4, "best KL cutoff\n(0.121, in hindsight)", fontsize=6, color=t["ink2"])
    notes = {("official", "QAD-Q4_0"): (6, 2), ("official", "NVFP4"): (-34, -10),
             ("official", "Q5_K_M"): (-40, -9)}
    for _, r in d.iterrows():
        k = (r.uploader, r.label)
        if k in notes:
            name = "official " + r.label
            ax.annotate(name, (r.mean_kld, r.code_full), xytext=notes[k],
                        textcoords="offset points", fontsize=6, color=t["ink2"])
    ax.annotate("same KL,\n86 vs 104", (0.259, 95), xytext=(-48, -24), textcoords="offset points",
                fontsize=6, color=t["ink2"], arrowprops=dict(arrowstyle="-", lw=0.5, color=t["ink2"]))
    ax.set_xscale("log"); ax.set_ylim(0, 128)
    ax.set_xlabel("Mean KL divergence vs BF16 (log scale)")
    ax.set_ylabel("HumanEval+ solved (of 164)")
    ax.legend(fontsize=5.5, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2)
    fig.set_size_inches(3.5, 2.9)
    fig.tight_layout(); fig.savefig("paper/figures/kl_vs_code.pdf"); plt.close(fig)


def paper_code_vs_tool():
    t = style(paper=True)
    fig, ax = plt.subplots(figsize=(3.5, 2.2))
    d = full[full.approx_bpw < 10].sort_values("approx_bpw")
    ax.scatter(d.approx_bpw, d.code_full / 118, c=S1, marker="o", s=20, label="Code (HumanEval+)", zorder=3,
               edgecolors=t["bg"], linewidths=0.6)
    ax.scatter(d.approx_bpw, d.tool_full / 60, c=S2, marker="s", s=20, label="Tool call / JSON", zorder=3,
               edgecolors=t["bg"], linewidths=0.6)
    ax.axhline(1, color=t["ink2"], lw=0.7)
    ax.set_xlim(2.7, 9.1); ax.set_ylim(0, 1.1)
    ax.set_xlabel("Bits per weight"); ax.set_ylabel("Score relative to BF16")
    ax.legend(fontsize=6, loc="lower right")
    fig.tight_layout(); fig.savefig("paper/figures/code_vs_tool.pdf"); plt.close(fig)


def paper_imatrix_pairs():
    t = style(paper=True)
    pairs = [("Q3_K_L", "prithivMLmods"), ("Q3_K_M", "prithivMLmods"), ("Q4_K_S", "prithivMLmods"),
             ("Q4_K_M", "official"), ("Q5_K_S", "prithivMLmods"), ("Q5_K_M", "official"), ("Q6_K", "official")]
    plain, imx = [], []
    for q, up in pairs:
        plain.append(s[(s.uploader == up) & (s.label == q)].mean_kld.iloc[0])
        imx.append(s[(s.uploader == "bartowski") & (s.label == q)].mean_kld.iloc[0])
    fig, ax = plt.subplots(figsize=(3.5, 2.1))
    x = range(len(pairs)); w = 0.38
    ax.bar([i - w / 2 - 0.01 for i in x], plain, w, color=S1, label="Plain (no imatrix)")
    ax.bar([i + w / 2 + 0.01 for i in x], imx, w, color=S2, label="bartowski (imatrix)")
    ax.set_xticks(list(x)); ax.set_xticklabels([p[0] for p in pairs], fontsize=6)
    ax.set_ylabel("Mean KL vs BF16"); ax.grid(axis="x", visible=False)
    ax.legend(fontsize=6)
    fig.tight_layout(); fig.savefig("paper/figures/imatrix_pairs.pdf"); plt.close(fig)


def rebuild_chart(path, theme="light", paper=False):
    t = style(theme, paper)
    arms = [("plain", "No imatrix", S1), ("imatrix", "imatrix: WikiText-2", S2),
            ("bartimatrix", "imatrix: bartowski set", S3)]
    qs = ["Q2_K", "Q3_K_S", "Q3_K_M"]
    fig, ax = plt.subplots(figsize=(3.5, 2.3) if paper else (10, 4.6))
    w = 0.26
    for i, (a, name, col) in enumerate(arms):
        vals = [rb[(rb.quant == q) & (rb.arm == a)].code_full.iloc[0] for q in qs]
        xs = [j + (i - 1) * (w + 0.02) for j in range(3)]
        ax.bar(xs, vals, w, color=col, label=name)
        for xx, v in zip(xs, vals):
            ax.text(xx, v + 2, str(v), ha="center", fontsize=6 if paper else 11,
                    color=t["ink"], fontweight="bold" if not paper else "normal")
    ax.axhline(118, color=t["ink2"], lw=0.8)
    ax.axhline(110, color=t["ink2"], lw=0.8, ls="--")
    ax.text(2.45, 120, "original (118)", ha="right", fontsize=6 if paper else 10, color=t["ink2"])
    ax.set_xticks(range(3)); ax.set_xticklabels(qs)
    ax.set_ylim(0, 132); ax.grid(axis="x", visible=False)
    ax.text(-0.42, 111.5, "functional (110)", fontsize=6 if paper else 10, color=t["ink2"])
    ax.set_ylabel("HumanEval+ solved (of 164)")
    ax.legend(fontsize=6 if paper else 10, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3,
              handlelength=1.2, columnspacing=0.8)
    fig.tight_layout(); fig.savefig(path, dpi=200); plt.close(fig)


# ----------------------------------------------------------------- README assets
def canvas(fig, z=-5):
    W, H = fig.get_size_inches()
    a = fig.add_axes([0, 0, 1, 1], zorder=z)
    a.set_xlim(0, W); a.set_ylim(0, H); a.axis("off"); a.set_facecolor("none")
    return a, W, H


def rbox(a, x, y, w, h, fc, ec, r=0.18, lw=1.2):
    a.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                               fc=fc, ec=ec, lw=lw))


def card(fig, t):
    a, W, H = canvas(fig, z=-10)
    rbox(a, 0.03, 0.03, W - 0.06, H - 0.06, t["bg"], t["border"], r=0.22)


def hero(theme):
    t = style(theme)
    q2 = rb[(rb.quant == "Q2_K") & (rb.arm == "plain")].iloc[0]

    def pick(u, l):
        r = s[(s.uploader == u) & (s.label == l)].iloc[0]
        return float(r.size_gb), int(r.code_full)

    rows = [("Original model (BF16)", *pick("official", "BF16"), True),
            ("Official · Q8_0", *pick("official", "Q8_0"), False),
            ("AtomicChat · AD-Q5_K_M", *pick("AtomicChat", "AD-Q5_K_M"), False),
            ("Official · QAD-Q4_0", *pick("official", "QAD-Q4_0"), False),
            ("bartowski · Q3_K_M", *pick("bartowski", "Q3_K_M"), False),
            ("prithivMLmods · Q3_K_M", *pick("prithivMLmods", "Q3_K_M"), False),
            ("bartowski · Q2_K", *pick("bartowski", "Q2_K"), False),
            ("bartowski · IQ2_M", *pick("bartowski", "IQ2_M"), False),
            ("Q2_K without calibration", round(q2.size_bytes / 1e9, 2), int(q2.code_full), False)]
    col = lambda sc, ref: REF if ref else GOOD if sc >= 110 else WARN if sc >= 59 else CRIT
    fig = plt.figure(figsize=(11, 5.8))
    card(fig, t)
    ax = fig.add_axes([0.30, 0.12, 0.65, 0.66])
    ax.set_facecolor("none")
    y = list(range(len(rows)))[::-1]
    for yy, (n, gb, sc, ref) in zip(y, rows):
        ax.barh(yy, max(sc, 0.8), 0.62, color=col(sc, ref))
        ax.text(max(sc, 0.8) + 1.5, yy, str(sc), va="center", fontsize=12, fontweight="bold", color=t["ink"])
        ax.text(-2, yy + 0.12, n, va="center", ha="right", fontsize=12, color=t["ink"])
        ax.text(-2, yy - 0.26, f"{gb:.2f} GB", va="center", ha="right", fontsize=9.5, color=t["ink2"])
    ax.axvline(110, color=t["ink2"], ls="--", lw=1)
    ax.text(111, max(y) + 0.6, "works well (110+)", fontsize=9.5, color=t["ink2"])
    ax.set_xlim(0, 132); ax.set_ylim(-0.6, max(y) + 0.9)
    ax.set_yticks([]); ax.spines["left"].set_visible(False)
    ax.set_xlabel("Coding problems solved, out of 164", fontsize=11, color=t["ink2"])
    fig.text(0.035, 0.92, "Same model. Different download. Very different results.",
             fontsize=17, fontweight="bold", color=t["ink"])
    fig.text(0.035, 0.865, "LiquidAI LFM3-1.7B: every bar is a compressed GGUF file of the same weights",
             fontsize=11, color=t["ink2"])
    ax.legend(handles=[Patch(color=GOOD, label="Works"), Patch(color=WARN, label="Degraded"),
                       Patch(color=CRIT, label="Broken"), Patch(color=REF, label="Original")],
              loc="lower right", fontsize=10, ncol=4, bbox_to_anchor=(1.0, 1.01))
    fig.savefig(f"assets/hero-{theme}.png", dpi=160, transparent=True); plt.close(fig)


def stats(theme):
    t = style(theme)
    tiles = [("45", "public GGUF files tested"), ("1 / 164", "solved by a file\nthat loads with no error"),
             ("1 → 55", "after changing\none compression setting"), ("30 s", "to reject\na broken file")]
    fig = plt.figure(figsize=(11, 1.9))
    a, W, H = canvas(fig)
    gap = 0.18; w = (W - 0.06 - 3 * gap) / 4
    for i, (big, small) in enumerate(tiles):
        x0 = 0.03 + i * (w + gap)
        rbox(a, x0, 0.06, w, H - 0.12, t["card"], t["border"], r=0.16, lw=1)
        a.text(x0 + w / 2, H * 0.62, big, ha="center", va="center", fontsize=28, fontweight="bold", color=t["ink"])
        a.text(x0 + w / 2, H * 0.27, small, ha="center", va="center", fontsize=10.5, color=t["ink2"], linespacing=1.3)
    fig.savefig(f"assets/stats-{theme}.png", dpi=160, transparent=True); plt.close(fig)


def how(theme):
    t = style(theme)
    steps = [("1", "Load", "Starts the file in llama.cpp\nand checks its chat template"),
             ("2", "Exam", "20 tool calls + 15 coding problems,\nanswers executed and checked"),
             ("3", "Verdict", "PASS or SUSPECT, plus an exit code\nyour CI pipeline understands")]
    accent = [S1, S2, GOOD]
    fig = plt.figure(figsize=(11, 2.2))
    a, W, H = canvas(fig)
    gap = 0.4; w = (W - 0.06 - 2 * gap) / 3
    for i, (n, title, body) in enumerate(steps):
        x0 = 0.03 + i * (w + gap)
        rbox(a, x0, 0.06, w, H - 0.12, t["card"], t["border"], r=0.16, lw=1)
        a.add_patch(Circle((x0 + 0.42, H - 0.55), 0.2, fc=accent[i], ec="none"))
        a.text(x0 + 0.42, H - 0.56, n, ha="center", va="center", fontsize=12, fontweight="bold", color="white")
        a.text(x0 + 0.78, H - 0.55, title, va="center", fontsize=16, fontweight="bold", color=t["ink"])
        a.text(x0 + 0.24, 0.62, body, va="center", fontsize=11, color=t["ink2"], linespacing=1.45)
        if i < 2:
            a.text(x0 + w + gap / 2, H / 2, "›", ha="center", va="center", fontsize=26, color=t["ink2"])
    fig.savefig(f"assets/how-{theme}.png", dpi=160, transparent=True); plt.close(fig)


def demo():
    bg, fg, dim = "#0d1117", "#e6edf3", "#8b949e"
    green, red, cyan = "#3fb950", "#f85149", "#79c0ff"
    lines = [
        [("$ ", dim), ("quant-gate run ", fg), ("LFM3-1.7B-Q8_0.gguf", cyan), (" --fail-fast", fg)],
        [("  tool calls   ", dim), ("20/20", fg)],
        [("  coding       ", dim), ("15/15", fg)],
        [("  verdict      ", dim), ("PASS", green), ("   exit 0 · 3 min", dim)],
        [],
        [("$ ", dim), ("quant-gate run ", fg), ("LFM3-1.7B-Q2_K-no-imatrix.gguf", cyan), (" --fail-fast", fg)],
        [("  tool calls   ", dim), ("12/20", red), ("  (needs 18)", dim)],
        [("  coding       ", dim), ("skipped, already failed", dim)],
        [("  verdict      ", dim), ("SUSPECT", red), ("   exit 1 · 30 s", dim)],
    ]
    fig = plt.figure(figsize=(11, 4.2))
    a, W, H = canvas(fig)
    rbox(a, 0.03, 0.03, W - 0.06, H - 0.06, bg, "#30363d", r=0.2)
    for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        a.add_patch(Circle((0.33 + i * 0.24, H - 0.32), 0.075, fc=c))
    a.text(W / 2, H - 0.32, "terminal", ha="center", va="center", fontsize=10, color=dim)
    r = fig.canvas.get_renderer()
    y = H - 0.85
    for ln in lines:
        x = 0.35
        for txt, c in ln:
            tt = a.text(x, y, txt, fontsize=13, color=c, family="DejaVu Sans Mono", va="center",
                        fontweight="bold" if c in (green, red) else "normal")
            bb = tt.get_window_extent(renderer=r)
            x += bb.width / fig.dpi
        y -= 0.36
    fig.savefig("assets/demo.png", dpi=160, transparent=True); plt.close(fig)


def banner():
    bg = "#0d1117"
    fig = plt.figure(figsize=(12, 3.3))
    a, W, H = canvas(fig)
    rbox(a, 0.03, 0.03, W - 0.06, H - 0.06, bg, "#30363d", r=0.3)
    rbox(a, 0.55, 0.55, 0.62, H - 1.1, "#161b22", "#30363d", r=0.3, lw=1.5)
    for i, (c, al) in enumerate([(CRIT, 0.3), ("#fab219", 0.3), (GOOD, 1.0)]):
        a.add_patch(Circle((0.86, H - 0.95 - i * 0.7), 0.22, fc=c, alpha=al))
    a.text(1.7, H * 0.63, "quant-gate", fontsize=46, fontweight="bold", color="#f0f6fc", va="center")
    a.text(1.72, H * 0.37, "Your compressed AI model loads. Does it still work?", fontsize=19,
           color="#c9d1d9", va="center")
    a.text(1.72, H * 0.21, "Pass/fail acceptance test for GGUF models  ·  CLI + GitHub Action", fontsize=13,
           color="#8b949e", va="center")
    fig.savefig("assets/banner.png", dpi=160, transparent=True); plt.close(fig)


if __name__ == "__main__":
    paper_code_vs_bpw(); paper_kl_vs_code(); paper_code_vs_tool(); paper_imatrix_pairs()
    rebuild_chart("paper/figures/rebuild.pdf", paper=True)
    for th in ("light", "dark"):
        hero(th); stats(th); how(th); rebuild_chart(f"assets/rebuild-{th}.png", th)
    demo(); banner()
    print("done")
