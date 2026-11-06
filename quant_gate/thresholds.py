"""Pass/fail rules. Keep in sync with docs/thresholds.md."""

# Reference (BF16) on the full sets
BF16_CODE_PLUS = 118          # of 164
BF16_TOOL = 60                # of 60

# Full-benchmark verdicts
FUNCTIONAL_CODE_MIN = 110     # BF16 72.0% - 5 pts = 67.0% of 164 -> 110
FUNCTIONAL_TOOL_MIN = 57      # of 60
NONFUNC_CODE_BELOW = 59       # < half of BF16
NONFUNC_TOOL_BELOW = 30       # < half of 60

# Screen (fast) rules: below either -> "suspect"
SCREEN_CODE_MIN = 13          # of 15
SCREEN_TOOL_MIN = 18          # of 20

SETTINGS = {
    "decoding": "greedy (temperature 0, seed 0)",
    "thinking": "off; leaked reasoning before </think> stripped",
    "code_max_tokens": 2048,
    "tool_max_tokens": 256,
    "ctx": 8192,
    "kl": "WikiText-2 test, 100 chunks x 512 tokens, vs BF16 base",
}