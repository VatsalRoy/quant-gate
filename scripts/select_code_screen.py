"""Pick the 15-task code screen from BF16 results only -> data/code_screen_tasks.json"""
import json
import random

from quant_gate.screens.code import load_tasks

tasks = load_tasks()
bf = {r["task_id"]: r for r in json.load(open("results/code_LFM3-1.7B-BF16_full.json"))["results"]}
q8 = {r["task_id"]: r for r in json.load(open("results/code_LFM3-1.7B-Q8_0_full.json"))["results"]}

eligible = [t for t, r in bf.items()
            if r["plus"] and r["finish_reason"] != "length" and not r["leaked_thinking"]]

def difficulty(tid):  # non-empty lines in the official reference solution
    return sum(1 for l in tasks[tid]["canonical_solution"].splitlines() if l.strip())

eligible.sort(key=lambda t: (difficulty(t), t))
k = len(eligible) // 3
bands = {"short": eligible[:k], "medium": eligible[k:2 * k], "long": eligible[2 * k:]}

rng = random.Random(2026)
screen = []
for name, band in bands.items():
    pick = sorted(rng.sample(band, 5), key=lambda t: int(t.split("/")[1]))
    screen += pick
    print(f"{name:6s} ({len(band)} eligible, {difficulty(band[0])}-{difficulty(band[-1])} lines): {pick}")

json.dump(screen, open("data/code_screen_tasks.json", "w"), indent=1)
print(f"\nEligible: {len(eligible)} of {len(bf)}")
print(f"BF16 generation time on these 15: {sum(bf[t]['seconds'] for t in screen):.0f}s")
print(f"Q8_0 on these 15 (report only, not used for selection): {sum(q8[t]['plus'] for t in screen)}/15")
print("Saved data/code_screen_tasks.json")