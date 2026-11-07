"""Same NVFP4 file, 4 setups: new/old llama.cpp x Metal/CPU."""
import time

from quant_gate.config import tool
from quant_gate.server import LlamaServer

MODEL = "models/LFM3-1.7B-NVFP4.gguf"
SETUPS = [
    ("new build, Metal", tool("llama-server"), []),
    ("new build, CPU", tool("llama-server"), ["-ngl", "0"]),
    ("old brew b11960, Metal", "llama-server", []),
    ("old brew b11960, CPU", "llama-server", ["-ngl", "0"]),
]

for name, binary, extra in SETUPS:
    print(f"\n=== {name} ===")
    try:
        with LlamaServer(MODEL, binary=binary, extra_args=extra,
                         log_path=f"results/logs/nvfp4_{name.replace(' ', '_').replace(',', '')}.log") as srv:
            t0 = time.time()
            out = srv.chat([{"role": "user", "content": "What is 17 * 23? Answer with just the number."}],
                           max_tokens=60)
            ch = out["choices"][0]
            print(f"finish: {ch['finish_reason']}   {time.time() - t0:.1f}s")
            print("reply:", repr((ch["message"].get("content") or "")[:300]))
    except Exception as e:
        print("ERROR:", e)

print("\n=== what comes after the answer (new build, Metal, 200 tokens) ===")
for m in ["models/LFM3-1.7B-Q8_0.gguf", MODEL]:
    with LlamaServer(m) as srv:
        out = srv.chat([{"role": "user", "content": "What is 17 * 23? Answer with just the number."}],
                       max_tokens=200)
        ch = out["choices"][0]
        print(f"\n{m.split('/')[-1]}: finish={ch['finish_reason']}  "
              f"tokens={out['usage']['completion_tokens']}")
        print(repr(ch["message"].get("content")))