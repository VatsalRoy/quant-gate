"""KL divergence vs BF16 via llama-perplexity."""
import re
import subprocess
import time
from pathlib import Path

from quant_gate.config import tool

CTX = 512      # tokens per chunk
CHUNKS = 100   # number of chunks -> ~25k scored tokens (llama.cpp scores the 2nd half of each chunk)

PATTERNS = {
    "mean_kld": r"Mean\s+KLD:\s*([-\d.]+)",
    "kld_p99": r"99\.0%\s+KLD:\s*([-\d.]+)",
    "top1_agree_pct": r"Same top p:\s*([-\d.]+)",
    "ppl_q": r"Mean PPL\(Q\)\s*:\s*([-\d.]+)",
    "ppl_base": r"Mean PPL\(base\)\s*:\s*([-\d.]+)",
}


def _run(cmd: list[str], log_path: str) -> tuple[str, float]:
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    log = Path(log_path)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(proc.stdout + proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(f"llama-perplexity failed (code {proc.returncode}); see {log}")
    return proc.stdout + proc.stderr, time.time() - t0


def make_base(bf16_path, text_path, base_out, ctx=CTX, chunks=CHUNKS) -> float:
    """Run BF16 once over the text and save its probabilities."""
    cmd = [tool("llama-perplexity"), "-m", str(bf16_path), "-f", str(text_path),
           "-c", str(ctx), "--chunks", str(chunks), "--kl-divergence-base", str(base_out)]
    _, secs = _run(cmd, "results/logs/kl_base.log")
    return secs


def run(model_path, base_path, ctx=CTX, chunks=CHUNKS) -> dict:
    """Compare a model against the saved BF16 base."""
    cmd = [tool("llama-perplexity"), "-m", str(model_path),
           "--kl-divergence-base", str(base_path), "--kl-divergence",
           "-c", str(ctx), "--chunks", str(chunks)]
    log = f"results/logs/kl_{Path(model_path).stem}.log"
    out, secs = _run(cmd, log)
    res = {}
    for key, pat in PATTERNS.items():
        m = re.search(pat, out)
        res[key] = float(m.group(1)) if m else None
    if res["mean_kld"] is None:
        raise RuntimeError(f"Could not find 'Mean KLD' in output; see {log}")
    res["seconds"] = round(secs, 1)
    return res