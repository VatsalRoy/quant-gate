- Code execution: EvalPlus runs each solution in a separate process with per-test
  time limits. On macOS its memory cap (RLIMIT_AS) is unsupported, so it is disabled
  (EVALPLUS_MAX_MEMORY_BYTES=-1). This is a guard, not a security sandbox.
- Found during development: with the memory cap enabled on macOS, every test crashed
  before running and was recorded as "timeout", giving a false 0% score. The harness
  now aborts if that happens.