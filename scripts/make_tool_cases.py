import json
from collections import Counter
from pathlib import Path

from quant_gate.screens.tools_cases import build_cases

cases = build_cases()
out = Path("data/tool_cases.jsonl")
out.parent.mkdir(exist_ok=True)
with out.open("w") as f:
    for c in cases:
        f.write(json.dumps(c) + "\n")

print(f"Wrote {len(cases)} cases to {out}")
print("By kind:", Counter(c["kind"] for c in cases))
print("Screen:", Counter(c["kind"] for c in cases if c["screen"]))