"""Start/stop llama-server for one GGUF file and talk to it."""
import subprocess
import time
from pathlib import Path

import requests


class LlamaServer:
    def __init__(self, model_path, port=8080, ctx=8192, binary="llama-server",
                 log_path=None, extra_args=None):
        self.model_path = Path(model_path)
        self.port = port
        self.ctx = ctx
        self.binary = binary
        self.url = f"http://127.0.0.1:{port}"
        self.log_path = Path(log_path or f"results/logs/{self.model_path.stem}.log")
        self.extra_args = extra_args or []
        self.proc = None
        self._log = None

    # `with LlamaServer(...) as srv:` starts it, and always stops it at the end
    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()

    def start(self, timeout=300):
        if not self.model_path.exists():
            raise FileNotFoundError(self.model_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log = self.log_path.open("w")
        cmd = [self.binary, "-m", str(self.model_path), "--jinja",
               "-c", str(self.ctx), "--host", "127.0.0.1",
               "--port", str(self.port), "-np", "1", *self.extra_args]
        self.proc = subprocess.Popen(cmd, stdout=self._log, stderr=subprocess.STDOUT)

        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(
                    f"llama-server exited early (code {self.proc.returncode}). "
                    f"See {self.log_path}")
            try:
                if requests.get(f"{self.url}/health", timeout=2).status_code == 200:
                    return
            except requests.ConnectionError:
                pass
            time.sleep(1)
        self.stop()
        raise TimeoutError(f"server not ready after {timeout}s; see {self.log_path}")

    def props(self) -> dict:
        """Server/model metadata, including the chat template it loaded."""
        return requests.get(f"{self.url}/props", timeout=10).json()

    def chat(self, messages, max_tokens=512, tools=None, thinking=False, **kwargs) -> dict:
        payload = {"messages": messages, "temperature": 0, "seed": 0,
                   "max_tokens": max_tokens,
                   "chat_template_kwargs": {"enable_thinking": thinking},
                   **kwargs}
        if tools:
            payload["tools"] = tools
        r = requests.post(f"{self.url}/v1/chat/completions", json=payload, timeout=600)
        r.raise_for_status()
        return r.json()

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self._log:
            self._log.close()
            self._log = None