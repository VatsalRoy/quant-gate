"""Where the llama.cpp tools live, and which version they are."""
import os
import subprocess
from pathlib import Path

# Override with:  export QG_LLAMA_BIN_DIR=/some/other/path
LLAMA_BIN_DIR = Path(os.environ.get(
    "QG_LLAMA_BIN_DIR",
    Path.home() / "Projects" / "llama.cpp" / "build" / "bin",
))


def tool(name: str) -> str:
    """Full path to a llama.cpp tool, e.g. tool('llama-server')."""
    p = LLAMA_BIN_DIR / name
    if not p.exists():
        raise FileNotFoundError(f"{p} not found. Build llama.cpp or set QG_LLAMA_BIN_DIR.")
    return str(p)


def llama_version(name: str = "llama-server") -> str:
    """The version line, so every result can record exactly which build made it."""
    out = subprocess.run([tool(name), "--version"], capture_output=True, text=True)
    text = (out.stdout + out.stderr).strip()
    return next((l for l in text.splitlines() if l.startswith("version")), text)