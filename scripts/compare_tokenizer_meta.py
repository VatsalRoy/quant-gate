"""Compare stop-token and template metadata between two GGUF files."""
import hashlib
import sys

from gguf import GGUFReader


def val(r, key):
    f = r.fields.get(key)
    if f is None:
        return None
    try:
        return f.contents()
    except Exception:
        part = f.parts[f.data[0]]
        try:
            return bytes(part).decode()
        except Exception:
            return part.tolist() if hasattr(part, "tolist") else part


def summary(path):
    r = GGUFReader(path)
    tokens = val(r, "tokenizer.ggml.tokens") or []
    info = {}
    for k in sorted(r.fields):
        if k.startswith("tokenizer.ggml.") and k.endswith("_id"):
            tid = val(r, k)
            text = tokens[tid] if isinstance(tid, int) and tid < len(tokens) else "?"
            info[k] = f"{tid}  ({text!r})"
    tmpl = val(r, "tokenizer.chat_template") or ""
    info["chat_template sha256[:12]"] = hashlib.sha256(tmpl.encode()).hexdigest()[:12]
    info["chat_template chars"] = len(tmpl)
    info["vocab size"] = len(tokens)
    return info


a, b = sys.argv[1], sys.argv[2]
sa, sb = summary(a), summary(b)
print(f"{'key':45s} | {a.split('/')[-1]:30s} | {b.split('/')[-1]}")
print("-" * 110)
for k in sorted(set(sa) | set(sb)):
    mark = "   " if sa.get(k) == sb.get(k) else "<<<"
    print(f"{k:45s} | {str(sa.get(k)):30s} | {str(sb.get(k))}  {mark}")