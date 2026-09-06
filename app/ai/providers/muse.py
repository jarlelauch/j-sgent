import os
import httpx
from ..base import AIProvider

# Muse Spark 1.2 free via OpenCode / generic OpenAI-compatible endpoint
# Env:
#   MUSE_API_KEY  -> required for hosted
#   MUSE_API_BASE -> default https://api.opencode.ai/v1  (fallback to OpenAI-compatible)
#   MUSE_MODEL    -> default opencode/muse-spark-1.2-contributor-free

DEFAULT_BASE = "https://api.opencode.ai/v1"
DEFAULT_MODEL = "opencode/muse-spark-1.2-contributor-free"

class MuseProvider(AIProvider):
    name = "muse"
    # capabilities match system needs + free tier
    capabilities = {
        "reasoning",
        "coding",
        "analysis",
        "planning",
        "synthesis",
        "critique",
        "local",  # treat as available for research-free paths
        "structured_output",
    }
    max_parallel = 3

    def __init__(self):
        self.api_key = os.getenv("MUSE_API_KEY") or os.getenv("OPENCODE_API_KEY") or ""
        self.base = (os.getenv("MUSE_API_BASE") or os.getenv("OPENCODE_API_BASE") or DEFAULT_BASE).rstrip("/")
        self.model = os.getenv("MUSE_MODEL") or DEFAULT_MODEL
        # also allow explicit model override via config.py if exists
        try:
            from ...core.config import MUSE_MODEL as CFG_MODEL  # type: ignore
            if CFG_MODEL:
                self.model = CFG_MODEL
        except Exception:
            pass

    def available(self) -> bool:
        # free tier: available if key present OR if base is local mock
        if self.api_key:
            return True
        # allow offline dev: if no key, still report False so router skips us
        return False

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def generate(self, messages, *, fast=False):
        # OpenAI-compatible /chat/completions
        # fast -> shorter max_tokens + lower temp
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.15 if fast else 0.30,
        }
        if fast:
            payload["max_tokens"] = 512
        else:
            payload["max_tokens"] = 2048

        # timeout tuned for free tier
        timeout = 60 if fast else 120
        url = f"{self.base}/chat/completions"

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=payload, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                # OpenAI shape
                if "choices" in data and data["choices"]:
                    content = data["choices"][0].get("message", {}).get("content") or data["choices"][0].get("text") or ""
                    if content:
                        return content
                # fallback: direct content
                if "content" in data:
                    return str(data["content"])
                # last fallback
                return str(data)
        except httpx.HTTPStatusError as exc:
            # surface friendly error
            body = ""
            try:
                body = exc.response.text[:600]
            except Exception:
                pass
            raise RuntimeError(f"Muse API {exc.response.status_code}: {body or exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"Muse generate failed: {exc}") from exc
