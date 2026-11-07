- Code execution: EvalPlus runs each solution in a separate process with per-test
  time limits. On macOS its memory cap (RLIMIT_AS) is unsupported, so it is disabled
  (EVALPLUS_MAX_MEMORY_BYTES=-1). This is a guard, not a security sandbox.
- Found during development: with the memory cap enabled on macOS, every test crashed
  before running and was recorded as "timeout", giving a false 0% score. The harness
  now aborts if that happens.

  - NVFP4 was not run on the full benchmark. On the screen it scored 0/15 code and 0/20
  tool while taking ~27 min (vs ~4 min typical), generating until the token limit on
  every item. A full run would take 3+ hours to confirm a 0% result, so it was replaced
  by a targeted diagnosis (new vs old llama.cpp, Metal vs CPU); see results.