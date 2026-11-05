import glob
import json
import traceback

d = json.load(open("results/code_LFM3-1.7B-Q8_0_first5.json"))
r = d["results"][0]  # HumanEval/0

print("=== MODEL REPLY ===")
print(r["reply"][:1500])
print("\n=== SOLUTION WE SENT TO EVALPLUS ===")
print(r["solution"][:1500])

print("\n=== DOES IT RUN? ===")
try:
    ns = {}
    exec(r["solution"], ns)
    print("has_close_elements([1.0, 2.0, 3.0], 0.5) ->", ns["has_close_elements"]([1.0, 2.0, 3.0], 0.5),
          "(expected False)")
    print("has_close_elements([1.0, 2.8, 3.0], 0.3) ->", ns["has_close_elements"]([1.0, 2.8, 3.0], 0.3),
          "(expected True)")
except Exception:
    traceback.print_exc()

print("\n=== EVALPLUS RECORD ===")
files = glob.glob("results/code_runs/LFM3-1.7B-Q8_0_first5/*eval_results*.json")
print("results file:", files)
ev = json.load(open(files[0]))["eval"]["HumanEval/0"]
rec = ev[0] if isinstance(ev, list) else ev
print({k: v for k, v in rec.items() if k != "solution"})