"""Hero chart for the README: same model, different files, very different results."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch

s = pd.read_csv("results/summary.csv")
rb = pd.read_csv("results/rebuild.csv")


def pick(uploader, label):
    r = s[(s["uploader"] == uploader) & (s["label"] == label)].iloc[0]
    return float(r["size_gb"]), int(r["code_full"])


q2 = rb[(rb["quant"] == "Q2_K") & (rb["arm"] == "plain")].iloc[0]
rows = [  # (name, size_gb, solved, is_reference)
    ("Original model (BF16)", *pick("official", "BF16"), True),
    ("Official Q8_0", *pick("official", "Q8_0"), False),
    ("AtomicChat AD-Q5_K_M", *pick("AtomicChat", "AD-Q5_K_M"), False),
    ("Official QAD-Q4_0", *pick("official", "QAD-Q4_0"), False),
    ("bartowski Q3_K_M", *pick("bartowski", "Q3_K_M"), False),
    ("prithivMLmods Q3_K_M", *pick("prithivMLmods", "Q3_K_M"), False),
    ("bartowski Q2_K", *pick("bartowski", "Q2_K"), False),
    ("bartowski IQ2_M", *pick("bartowski", "IQ2_M"), False),
    ("Q2_K, no calibration (my build)", round(q2["size_bytes"] / 1e9, 2), int(q2["code_full"]), False),
]

GREEN, ORANGE, RED, GRAY = "#2e9e5b", "#f0a030", "#d64545", "#9aa0a6"


def color(score, ref):
    if ref:
        return GRAY
    return GREEN if score >= 110 else ORANGE if score >= 59 else RED


fig, ax = plt.subplots(figsize=(9, 5))
names = [f"{n}  ·  {gb:.2f} GB" for n, gb, _, _ in rows][::-1]
scores = [sc for _, _, sc, _ in rows][::-1]
colors = [color(sc, ref) for _, _, sc, ref in rows][::-1]
bars = ax.barh(names, scores, color=colors, height=0.65)
for b, sc in zip(bars, scores):
    ax.text(b.get_width() + 1.5, b.get_y() + b.get_height() / 2, f"{sc}",
            va="center", fontsize=10, fontweight="bold")
ax.axvline(110, color="#555", ls="--", lw=1)
ax.text(111, len(rows) - 0.4, "works well (110+)", fontsize=8, color="#555")
ax.set_xlim(0, 135)
ax.set_xlabel("Coding problems solved, out of 164")
ax.set_title("Same AI model, different download: how many coding problems each file solves",
             fontsize=11, loc="left")
for side in ["top", "right"]:
    ax.spines[side].set_visible(False)
ax.legend(handles=[Patch(color=GREEN, label="Works"), Patch(color=ORANGE, label="Degraded"),
                   Patch(color=RED, label="Broken"), Patch(color=GRAY, label="Original")],
          loc="lower right", fontsize=8, frameon=False)
fig.tight_layout()
fig.savefig("figures/hero.png", dpi=200)
print("Saved figures/hero.png")