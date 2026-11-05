import json
from quant_gate.server import LlamaServer

tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current weather for a city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
            },
            "required": ["city", "unit"],
        },
    },
}]

with LlamaServer("models/LFM3-1.7B-Q8_0.gguf") as srv:
    out = srv.chat([{"role": "user", "content": "What's the weather in Oslo? Use celsius."}],
                   tools=tools, max_tokens=256)
    ch = out["choices"][0]
    print("finish_reason:", ch["finish_reason"])
    print(json.dumps(ch["message"], indent=2))