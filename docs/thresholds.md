## JSON scoring policy (decided before testing any quant)
- Pass/fail uses "correct": the first JSON object in the reply has exactly the
  expected keys, values and types. Code fences are allowed.
- "Clean" (reply is only JSON, as instructed) is tracked as a secondary metric.
- Why: on Q8_0, json-order-7 returned the correct object followed by a stray "```".
  Real applications extract JSON from replies, so a formatting slip shouldn't count
  as a functional failure, but it may be an early sign of degradation, so we keep it.
- Q8_0 full set: tool 30/30, JSON 30/30 correct, 59/60 clean.