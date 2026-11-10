# Environment

All results in this repo were produced on this setup unless a row says otherwise.

## Hardware
- MacBook Air, Apple M5
- Backend: Metal (Apple GPU)

## llama.cpp (main, used for all results)
- Built from source, tag: b12128
- Version: 0.9.0-dev (build 12128, commit a01dff908)
- Compiler: AppleClang 21.0.0.21000101, Darwin arm64
- Path: ~/Projects/llama.cpp/build/bin/
- Why source: Homebrew only had build 11960, and the official NVFP4 file
  requires build 12088 or newer (older builds load it but produce incorrect output).

## llama.cpp (legacy, NVFP4 demo only)
- Homebrew 0.8.0 (build 11960, commit 8642541b2)
- Kept only to demonstrate a "runtime incompatibility" failure. Not used for census results.

## Inference settings (all files)
- Greedy decoding: temperature 0, seed 0
- Thinking mode: off (chat_template_kwargs.enable_thinking = false)
- Chat template: read from the GGUF metadata (--jinja)
- Context: 8192 tokens, 1 parallel slot

## Policy
llama.cpp is pinned at this build for the whole project. Do not upgrade mid-census.

## Dependencies Version
- evalplus 0.3.1

## Correction (found 2026-11-10)
A bug made `LlamaServer` launch whichever `llama-server` was first on PATH (the Homebrew
build b11960) instead of the pinned source build b12128.
- Affected: all *generation* results (baselines, census, confirmation, rebuild gate runs,
  local CLI tests) before the fix commit.
- Not affected: KL (llama-perplexity) and quantization/imatrix (llama-quantize,
  llama-imatrix), which always used b12128.
- Version-sensitivity check on b12128: 4 files rerun on the screen gave identical results
  (Q8_0 15/15·20/20; rebuild Q3_K_M plain 9/15·20/20; rebuild Q2_K imatrix 8/15·20/20;
  rebuild Q3_K_M bartowski-imatrix 12/15·20/20). Generation results are therefore reported
  as measured on b11960.
- Exception: NVFP4 needs ≥ b12088 and was retested on b12128 (see findings_nvfp4.md).
- Every report now records the binary actually launched (`server_binary`, `llama_cpp`).