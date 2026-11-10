"""Render a quant-gate report as Markdown for the GitHub job summary."""
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
if not p.exists():
    print("## quant-gate: HARNESS ERROR\n\nThe tester failed before writing a report. "
          "This says nothing about the model file. See the step log.")
    sys.exit(0)

r = json.loads(p.read_text())
icon = {"pass": "✅", "functional": "✅", "degraded": "⚠️", "suspect": "❌",
        "non_functional": "❌", "packaging": "📦", "load_error": "💥"}.get(r["verdict"], "❓")
print(f"## quant-gate: {icon} {r['verdict'].upper()}\n")
print(f"**File:** `{r['file']}`  ")
print(f"**SHA256:** `{r['sha256'][:16]}…`  ")
print(f"**Mode:** {r['mode']} · **llama.cpp:** {r.get('llama_cpp', '')}\n")
print("| Check | Result |\n|---|---|")
md = r.get("metadata", {})
print(f"| Chat template | {'yes' if md.get('chat_template_present') else '**missing**'} |")
if r.get("tool"):
    t = r["tool"]
    print(f"| Tool calls / JSON | {round(t['score'] * t['n'])}/{t['n']} |")
if r.get("code"):
    c = r["code"]
    print(f"| Code (HumanEval+) | {c['solved_plus']}/{c.get('n_planned', c['n'])} |")
elif r.get("fail_fast"):
    print(f"| Code (HumanEval+) | skipped: {r['fail_fast']} |")
print(f"| Time | {r.get('total_seconds')} s |\n")
print("**Why:** " + "; ".join(r.get("reasons", [])))