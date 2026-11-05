import argparse
import json
from pathlib import Path

from quant_gate.screens import tools
from quant_gate.server import LlamaServer

ap = argparse.ArgumentParser()
ap.add_argument("model")
ap.add_argument("--full", action="store_true", help="all 60 cases instead of the 20-case screen")
args = ap.parse_args()

cases = [json.loads(l) for l in open("data/tool_cases.jsonl")]
if not args.full:
    cases = [c for c in cases if c["screen"]]

with LlamaServer(args.model) as srv:
    results = tools.run(srv, cases)

summary = tools.summarize(results)
split = "full" if args.full else "screen"
out = Path(f"results/tools_{Path(args.model).stem}_{split}.json")
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({"summary": summary, "results": results}, indent=2))

print(json.dumps({k: v for k, v in summary.items() if k != "failures"}, indent=2))
print(f"Total time: {sum(r['seconds'] for r in results):.1f}s")
print("Correct but not clean:", summary["unclean"])
for r in results:
    if not r["ok"]:
        print(f"\n--- {r['id']}: {r['reason']}")
        print("content:", r["content"][:300])
        if r["tool_calls"]:
            print("tool_calls:", json.dumps(r["tool_calls"])[:300])
print(f"\nSaved {out}")