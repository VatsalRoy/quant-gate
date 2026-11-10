"""Controlled rebuild: same BF16 source, same llama.cpp build; imatrix is the only variable."""
import json
import subprocess
import time
from pathlib import Path

from gguf import GGUFReader

from quant_gate.config import llama_version, tool

SRC = Path("models/LFM3-1.7B-BF16.gguf")
OUT = Path("models/rebuild")
CALIB = Path("data/calib_text.txt")          # WikiText-2 TRAIN slice (never the KL test text)
IMATRIX = OUT / "lfm3-wikitext-train.imatrix.gguf"
TYPES = ["Q2_K", "Q3_K_S", "Q3_K_M"]

OUT.mkdir(parents=True, exist_ok=True)
Path("results/logs").mkdir(parents=True, exist_ok=True)
record = {"llama_cpp": llama_version(), "source": str(SRC), "calibration": str(CALIB), "steps": []}


def run(cmd, name):
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    log = Path(f"results/logs/rebuild_{name}.log")
    log.write_text(p.stdout + p.stderr)
    if p.returncode != 0:
        raise SystemExit(f"{name} failed (code {p.returncode}); see {log}")
    record["steps"].append({"name": name, "cmd": " ".join(cmd), "seconds": round(time.time() - t0, 1)})
    print(f"  {name}: {time.time() - t0:.0f}s")


# 1) importance matrix from BF16 on the calibration text
if not IMATRIX.exists():
    print("Computing imatrix ...")
    run([tool("llama-imatrix"), "-m", str(SRC), "-f", str(CALIB), "-o", str(IMATRIX),
         "-c", "512", "--chunks", "200"], "imatrix")

# 2) quantize each type twice: without and with --imatrix
for q in TYPES:
    for arm in ["plain", "imatrix"]:
        dst = OUT / f"LFM3-1.7B-rebuild-{q}-{arm}.gguf"
        if dst.exists():
            continue
        cmd = [tool("llama-quantize")]
        if arm == "imatrix":
            cmd += ["--imatrix", str(IMATRIX)]
        cmd += [str(SRC), str(dst), q]
        print(f"Quantizing {q} ({arm}) ...")
        run(cmd, f"{q}_{arm}")


# 3) verify the ONLY difference is imatrix: same type for every single tensor
def tensor_map(path):
    r = GGUFReader(str(path))
    imx = any(k.startswith("quantize.imatrix") for k in r.fields)
    return {t.name: t.tensor_type.name for t in r.tensors}, imx


checks = []
for q in TYPES:
    a_path = OUT / f"LFM3-1.7B-rebuild-{q}-plain.gguf"
    b_path = OUT / f"LFM3-1.7B-rebuild-{q}-imatrix.gguf"
    (a, a_imx), (b, b_imx) = tensor_map(a_path), tensor_map(b_path)
    diff = [n for n in a if a[n] != b.get(n)]
    counts = {}
    for t in a.values():
        counts[t] = counts.get(t, 0) + 1
    checks.append({
        "quant": q,
        "plain_has_imatrix_meta": a_imx, "imatrix_has_imatrix_meta": b_imx,
        "tensors_with_different_type": len(diff),
        "size_plain_bytes": a_path.stat().st_size, "size_imatrix_bytes": b_path.stat().st_size,
        "tensor_types": ";".join(f"{k}:{v}" for k, v in sorted(counts.items(), key=lambda x: -x[1])),
    })

record["checks"] = checks
Path("results/rebuild_build.json").write_text(json.dumps(record, indent=2))
print(json.dumps(checks, indent=2))