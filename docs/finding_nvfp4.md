# NVFP4: a runtime incompatibility the gate caught

| Runtime | Screen | Full | KL vs BF16 |
|---|---|---|---|
| llama.cpp b11960 (card: unsupported, "incorrect output") | code 0/15, tool 0/20 → SUSPECT | not run | n/a |
| llama.cpp b12128 (supported) | code 12/15, tool 20/20 → SUSPECT | code 99/164, tool 60/60 → DEGRADED | 0.097 |

- On b11960 the file loads with no error and generates "GGGG…", as the model card warns
  for builds before b12088. The gate rejected it; a load-only check would have passed it.
- On the supported build it works but is degraded on code (99 vs BF16 118; functional ≥ 110),
  while its KL (0.097) is close to functional 4-bit files (AD-IQ4_XS 0.102 → 113 solved;
  IQ4_XS 0.121 → 111). KL does not separate functional from degraded here.
- Diagnosis history: one early run that passed the new binary explicitly produced coherent
  text. Later diagnostics used the default binary, which, due to a harness bug, was the old
  b11960, so they reproduced the garbage. An earlier "stray server" explanation was wrong.