import json
import sys

rows = json.load(open(sys.argv[1]))["results"]
fail = [r for r in rows if not r["plus"]]
trunc = [r for r in rows if r["finish_reason"] == "length"]
both = [r for r in trunc if not r["plus"]]

print(f"failed: {len(fail)}   truncated: {len(trunc)}   truncated AND failed: {len(both)}")
print(f"time in truncated replies: {sum(r['seconds'] for r in trunc):.0f}s "
      f"of {sum(r['seconds'] for r in rows):.0f}s total")

if trunc:
    t = trunc[0]
    print(f"\n=== TRUNCATED: {t['task_id']} (passed plus: {t['plus']}) — last 800 chars ===")
    print(t["reply"][-800:])

nt = next((r for r in fail if r["finish_reason"] != "length"), None)
if nt:
    print(f"\n=== FAILED, NOT TRUNCATED: {nt['task_id']} ===")
    print(nt["reply"][:1500])