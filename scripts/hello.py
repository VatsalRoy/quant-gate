import requests

r = requests.post(
    "http://localhost:8080/v1/chat/completions",
    json={
        "messages": [{"role": "user", "content": "Write a Python function that reverses a string."}],
        "temperature": 0,      # greedy decoding = same answer every run
        "seed": 0,
        "max_tokens": 300,
    },
    timeout=120,
)
print(r.json()["choices"][0]["message"]["content"])