"""Is NVFP4's output stable? Fresh server per run, Metal vs CPU."""
from quant_gate.server import LlamaServer

MODEL = "models/LFM3-1.7B-NVFP4.gguf"
Q = [{"role": "user", "content": "What is 17 * 23? Answer with just the number."}]

for name, extra in [("Metal", []), ("CPU", ["-ngl", "0"])]:
    for i in range(4):
        with LlamaServer(MODEL, extra_args=extra,
                         log_path=f"results/logs/nvfp4_repeat_{name}_{i}.log") as srv:
            out = srv.chat(Q, max_tokens=200)
            ch = out["choices"][0]
            print(f"{name} run {i}: finish={ch['finish_reason']:6s} "
                  f"tokens={out['usage']['completion_tokens']:3d}  "
                  f"{(ch['message'].get('content') or '')[:70]!r}")