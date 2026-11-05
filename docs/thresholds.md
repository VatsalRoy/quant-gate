## JSON scoring policy (decided before testing any quant)
- Pass/fail uses "correct": the first JSON object in the reply has exactly the
  expected keys, values and types. Code fences are allowed.
- "Clean" (reply is only JSON, as instructed) is tracked as a secondary metric.
- Why: on Q8_0, json-order-7 returned the correct object followed by a stray "```".
  Real applications extract JSON from replies, so a formatting slip shouldn't count
  as a functional failure, but it may be an early sign of degradation, so we keep it.
- Q8_0 full set: tool 30/30, JSON 30/30 correct, 59/60 clean.

## Leaked reasoning (decided on Q8_0, before testing any quant)
- With thinking disabled, LFM3 still reasons in plain text on some prompts, ending with
  "</think>" before its answer. On Q8_0 with max_tokens=768, 27/164 code replies did this
  and were cut off, costing ~16 points unrelated to quantization.
- Rule: text before the last "</think>" is stripped and counted as leaked_thinking.
- Code screen max_tokens = 2048; tool/JSON = 256.
- A truncated reply is a fail, even if it contains code.
- leaked_thinking rate is reported per file as a secondary metric.

## Baselines (full sets, greedy, thinking off, llama.cpp b12128, Apple M5 / Metal)
| File | Code plus (164) | Tool/JSON (60) |
|---|---|---|
| BF16 | 118 (72.0%) | 60 (100%) |
| Q8_0 | 119 (72.6%) | 60 (100%) |
BF16 vs Q8_0 code flips: [N] -> paired SE ~[X] pts.

BF16 vs Q8_0 code flips: 5 (2 BF16-only, 3 Q8_0-only) -> paired SE ~1.4 pts.
Tool/JSON flips: 0.

Why 5 pts: ~3.7x the paired SE between BF16 and Q8_0, so a drop that large is
unlikely to be rounding noise. The tool margin (57/60) is a judgment call: BF16 and
Q8_0 had zero churn, so any 3+ case drop is a clear change.

Reproducibility: BF16 rerun on the 15-task screen reproduced 15/15.
Screen cost: Q8_0 ~47s code + ~12s tools ≈ 1 min/file; full code set ≈ 28 min/file.

## Verdicts
Each file gets one verdict, based on the FULL benchmarks:
- **Functional:** code plus >= BF16 - 5 pts AND tool/JSON >= 57/60 (95%)
- **Degraded:** works, but below one of those margins
- **Non-functional:** code plus < half of BF16 (< 59/164) OR tool/JSON < 30/60
Separate categories (not weights): **packaging** (missing/broken chat template),
**runtime incompatibility** (needs a newer llama.cpp than the tester).

Why 5 pts: about [5 / X]x the paired SE between BF16 and Q8_0, so a drop that large
is unlikely to be rounding noise. "Non-functional" follows the spirit of the
Broken on Arrival paper: unusable, not just worse.

## Screen (fast) rules
- Code screen: 15 tasks (data/code_screen_tasks.json), all solved by BF16.
- Tool screen: 20 cases (screen=True in data/tool_cases.jsonl), all solved by BF16.
- **Suspect** if code screen < 13/15 OR tool screen < 18/20.
- Mean KL vs BF16 is reported for every file but is NOT a gate criterion yet;
  testing whether it could be one is H3.
- These screen cutoffs are provisional. The confirmation phase measures the miss rate
  (screen passes but full benchmark fails) and they may be revised then; any revision
  is documented with its reason.