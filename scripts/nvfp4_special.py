"""Does NVFP4 break only when special tokens are present?"""
import requests

from quant_gate.server import LlamaServer

PLAIN = "The capital of France is"
MSG = [{"role": "user", "content": "What is the capital of France?"}]

for m in ["models/LFM3-1.7B-Q8_0.gguf", "models/LFM3-1.7B-NVFP4.gguf"]:
    with LlamaServer(m) as srv:
        # the exact prompt text the chat endpoint would build, special tokens included
        chat_prompt = requests.post(f"{srv.url}/apply-template",
                                    json={"messages": MSG}, timeout=30).json()["prompt"]
        tests = [
            ("plain text", PLAIN),
            ("plain + 1 special", "<|im_start|>" + PLAIN),
            ("full chat format", chat_prompt),
        ]
        for name, p in tests:
            r = requests.post(f"{srv.url}/completion",
                              json={"prompt": p, "n_predict": 30, "temperature": 0, "seed": 0},
                              timeout=120).json()
            print(f"{m.split('/')[-1]:22s} {name:18s} -> {r.get('content', '')[:70]!r}")
    print()

print("chat prompt looked like:", repr(chat_prompt[:200]))