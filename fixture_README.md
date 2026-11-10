---
license: other
license_name: lfm1.0
base_model: LiquidAI/LFM3-1.7B
tags: [gguf, test-fixture, do-not-use]
---
# ⚠️ DELIBERATELY BROKEN: test fixture, do not use

LFM3-1.7B quantized to Q2_K with llama.cpp b12128 **without an importance matrix**.
It solves 1/164 HumanEval+ problems (BF16: 118) and fails 40% of tool calls.

It exists as the failing example for [quant-gate](https://github.com/VatsalRoy/quant-gate),
a functional acceptance gate for GGUF files. The same weights quantized *with* an
imatrix solve 51–55/164; see the repo for the controlled experiment.

Base model: [LiquidAI/LFM3-1.7B](https://huggingface.co/LiquidAI/LFM3-1.7B), LFM Open License v1.0.