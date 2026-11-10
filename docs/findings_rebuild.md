# Controlled rebuild: imatrix and calibration

Source: official BF16, llama.cpp b12128. All arms share an identical tensor-type mix
(verified per tensor). Only the importance matrix differs.

| Quant | No imatrix | imatrix: WikiText-2 train, 200 chunks | imatrix: bartowski calibration-v6, 486 chunks |
|---|---|---|---|
| Q2_K  | code 1, tool 36 | code 55, tool 60 | code 51, tool 51 |
| Q3_K_S | code 96 | code 83 | code 78 |
| Q3_K_M | code 76 (KL 0.349) | code 86 (KL 0.258) | code 104 (KL 0.261) |

Exact McNemar tests (18 comparisons; Bonferroni threshold 0.0028):
- Q2_K: both imatrix arms beat no-imatrix on code (p≈0) and tools (p≤0.0026). Survives.
- Q3_K_M: bartowski calibration beats no-imatrix (p=0.0002, survives) and beats the
  WikiText imatrix (p=0.0039, just misses strict cutoff).
- Q3_K_S: both imatrix arms below no-imatrix (p=0.066, 0.013). Suggestive only.

Conclusions:
1. At 2 bits, any imatrix rescues a non-functional model (1 -> 51-55 of 164).
2. At 3 bits, the calibration setup (data and amount) matters more than imatrix yes/no,
   and a calibration can even hurt.
3. KL vs BF16 cannot distinguish calibrations: at Q3_K_M the two imatrix arms have
   KL 0.258 vs 0.261 but solve 86 vs 104 problems.
Caveat: the bartowski arm differs in both calibration text and amount (486 vs 200
chunks), so we cannot say which of the two matters.