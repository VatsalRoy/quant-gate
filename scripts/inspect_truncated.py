import json
import sys

rows = json.load(open(sys.argv[1]))["results"]
trunc = [r for r in rows if r["finish_reason"] == "length"]
print(f"{len(trunc)} truncated\n")
for r in trunc:
    lines = [l for l in r["reply"].splitlines() if l.strip()]
    uniq = len(set(lines)) / max(len(lines), 1)
    print(f"{r['task_id']:15s} lines={len(lines):4d}  unique_lines={uniq:.2f}  "
          f"has_code_fence={'```' in r['reply']}")
print(f"\n=== last 600 chars of {trunc[0]['task_id']} ===\n{trunc[0]['reply'][-600:]}")