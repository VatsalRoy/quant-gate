import argparse
import json
from pathlib import Path

from quant_gate.screens import code
from quant_gate.server import LlamaServer

ap = argparse.ArgumentParser()
ap.add_argument("model")
ap.add_argument("--tasks", help="JSON list of task_ids (e.g. the 15-task screen). Default: all 164")
ap.add_argument("--limit", type=int, help="only the first N tasks (for a quick test)")
args = ap.parse_args()

tasks = code.load_tasks()
ids = json.load(open(args.tasks)) if args.tasks else list(tasks)
if args.limit:
    ids = ids[:args.limit]
split = "screen" if args.tasks else ("full" if not args.limit else f"first{args.limit}")
stem = Path(args.model).stem

with LlamaServer(args.model) as srv:
    samples = code.generate(srv, tasks, ids)

status = code.evaluate(samples, tasks, f"results/code_runs/{stem}_{split}")
rows = [{**s, **status[s["task_id"]]} for s in samples]
summary = code.summarize(rows)

out = Path(f"results/code_{stem}_{split}.json")
out.write_text(json.dumps({"summary": summary, "results": rows}, indent=2))
print(json.dumps(summary, indent=2))
print("Failed (plus):", [r["task_id"] for r in rows if not r["plus"]][:30])
print(f"Saved {out}")