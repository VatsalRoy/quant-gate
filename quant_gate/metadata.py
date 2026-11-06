"""Read a GGUF file's header without running it."""
from collections import Counter


def read_metadata(path) -> dict:
    try:
        from gguf import GGUFReader
        r = GGUFReader(str(path))
    except Exception as e:
        return {"error": f"could not parse GGUF header: {e}"}

    def val(key):
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
                return part.tolist() if hasattr(part, "tolist") else str(part)

    tmpl = val("tokenizer.chat_template")
    imatrix = {k: val(k) for k in r.fields if k.startswith("quantize.imatrix")}
    tensor_types = Counter(t.tensor_type.name for t in r.tensors)

    return {
        "architecture": val("general.architecture"),
        "file_type": val("general.file_type"),
        "chat_template_present": bool(tmpl),
        "chat_template_chars": len(tmpl) if isinstance(tmpl, str) else 0,
        "imatrix_used": bool(imatrix),
        "imatrix": imatrix,
        "tensor_types": dict(tensor_types.most_common()),
        "n_tensors": len(r.tensors),
    }