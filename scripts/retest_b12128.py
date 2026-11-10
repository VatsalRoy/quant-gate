"""Retest on the pinned b12128 build: NVFP4 (screen + full) and 4 version-sensitivity checks."""
import json
from pathlib import Path

from quant_gate.cli import run_gate

KL_BASE = "models/LFM3-1.7B-BF16.kld"
OUT = Path("results/reports/retest_b12128")
OUT.mkdir(parents=True, exist_ok=True)

# (file, previous screen result on b11960: code/15, tool/20)
CHECKS = [
    ("models/LFM3-1.7B-NVFP4.gguf", (0, 0)),
    ("models/LFM3-1.7B-Q8_0.gguf", (15, 20)),
    ("models/rebuild/LFM3-1.7B-rebuild-Q3_K_M-plain.gguf", (9, 20)),
    ("models/rebuild/LFM3-1.7B-rebuild-Q2_K-imatrix.gguf", (8, 20)),
    ("models/rebuild/LFM3-1.7B-rebuild-Q3_K_M-bartimatrix.gguf", (12, 20)),
]

for path, (old_code, old_tool) in CHECKS:
    rep = run_gate(path, None, full=False)
    (OUT / f"{Path(path).stem}_screen.json").write_text(json.dumps(rep, indent=2, default=str))
    c = rep["code"]["solved_plus"] if rep.get("code") else "-"
    t = round(rep["tool"]["score"] * rep["tool"]["n"]) if rep.get("tool") else "-"
    print(f"{Path(path).name:45s} b12128: code {c}/15 tool {t}/20 | b11960: code {old_code}/15 "
          f"tool {old_tool}/20 | {rep['llama_cpp']}")

print("\nNVFP4 full run on b12128 ...")
rep = run_gate("models/LFM3-1.7B-NVFP4.gguf", KL_BASE, full=True)
(OUT / "LFM3-1.7B-NVFP4_full.json").write_text(json.dumps(rep, indent=2, default=str))
print(f"NVFP4 full: code {rep['code']['solved_plus']}/164  "
      f"tool {round(rep['tool']['score'] * rep['tool']['n'])}/60  "
      f"KL {rep['kl'].get('mean_kld')}  -> {rep['verdict'].upper()}")