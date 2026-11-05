import time
from quant_gate.server import LlamaServer

t0 = time.time()
with LlamaServer("models/LFM3-1.7B-Q8_0.gguf") as srv:
    print(f"Server ready in {time.time() - t0:.1f}s")

    tmpl = srv.props().get("chat_template", "")
    print(f"Chat template present: {bool(tmpl)} ({len(tmpl)} chars)")
    print("Template starts with:", tmpl[:200].replace("\n", " "), "...\n")

    out = srv.chat([{"role": "user", "content": "What is 17 * 23? Answer with just the number."}],
                   max_tokens=20)

    msg = out["choices"][0]["message"]
    print("finish_reason:", out["choices"][0]["finish_reason"])
    print("reasoning:", (msg.get("reasoning_content") or "")[:300])
    print("content:", msg.get("content"))
    print("Tokens used:", out.get("usage"))

print("Server stopped cleanly.")