"""Which llama-server setting makes NVFP4 break?"""
import requests

from quant_gate.server import LlamaServer

NV = "models/LFM3-1.7B-NVFP4.gguf"
Q8 = "models/LFM3-1.7B-Q8_0.gguf"
PROMPT = "The capital of France is"

CONFIGS = [
    ("Q8_0 control (ctx 8192)", Q8, 8192, []),
    ("NVFP4 default (ctx 8192)", NV, 8192, []),
    ("NVFP4 ctx 512", NV, 512, []),
    ("NVFP4 ctx 2048", NV, 2048, []),
    ("NVFP4 flash-attn off", NV, 8192, ["-fa", "off"]),
    ("NVFP4 flash-attn on", NV, 8192, ["-fa", "on"]),
    ("NVFP4 swa-full", NV, 8192, ["--swa-full"]),
    ("NVFP4 ctx 512 + fa off", NV, 512, ["-fa", "off"]),
]

for name, model, ctx, extra in CONFIGS:
    log = f"results/logs/nvfp4_cfg_{name.replace(' ', '_').replace('(', '').replace(')', '')}.log"
    try:
        with LlamaServer(model, ctx=ctx, extra_args=extra, log_path=log) as srv:
            r = requests.post(f"{srv.url}/completion",
                              json={"prompt": PROMPT, "n_predict": 20, "temperature": 0, "seed": 0},
                              timeout=120).json()
            print(f"{name:28s} -> {r.get('content', '')[:60]!r}")
    except Exception as e:
        print(f"{name:28s} -> ERROR: {e}")