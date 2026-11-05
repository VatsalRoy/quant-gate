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