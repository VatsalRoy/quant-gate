import argparse
import json
from pathlib import Path

from quant_gate.screens import kl

BASE = "models/LFM3-1.7B-BF16.kld"

ap = argparse.ArgumentParser()
ap.add_argument("model", nargs="?")
ap.add_argument("--make-base", action="store_true")
args = ap.parse_args()

if args.make_base:
    secs = kl.make_base("models/LFM3-1.7B-BF16.gguf", "data/kl_text.txt", BASE)
    size = Path(BASE).stat().st_size / 1e9
    print(f"Saved {BASE} ({size:.2f} GB) in {secs:.0f}s")
else:
    res = kl.run(args.model, BASE)
    out = Path(f"results/kl_{Path(args.model).stem}.json")
    out.write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    print(f"Saved {out}")