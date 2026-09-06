from ollama import Client

from ..base import AIProvider

from ...core.config import (
    OLLAMA_HOST,
    OLLAMA_MODEL,
    OLLAMA_FAST_MODEL,
)


class OllamaProvider(AIProvider):

    name = "ollama"

    capabilities = {
        "reasoning",
        "coding",
        "analysis",
        "planning",
        "local",
        "structured_output",
        "synthesis",
        "critique",
    }

    max_parallel = 1

    def __init__(self):

        self.client = Client(
            host=OLLAMA_HOST
        )

        self.model = OLLAMA_MODEL
        self.fast_model = OLLAMA_FAST_MODEL

        self._models = None

    def _available_models(self):

        if self._models is None:

            response = self.client.list()

            # ollama 0.3+ returns object with .models or dict
            raw = None
            if hasattr(response, "models"):
                raw = response.models
            elif isinstance(response, dict):
                raw = response.get("models", [])

            names = set()
            for item in raw or []:
                if isinstance(item, dict):
                    names.add(item.get("name") or item.get("model"))
                else:
                    # Model object
                    names.add(getattr(item, "model", None) or getattr(item, "name", None))

            # normalize qwen3:1.7b variants
            # ollama list shows qwen3:1.7b, config is qwen3:1.7b
            self._models = {n for n in names if n}

        return self._models

    def _select_model(self, fast=False):

        if not fast:
            return self.model

        models = self._available_models()

        if self.fast_model in models:
            return self.fast_model

        return self.model

    def generate(
        self,
        messages,
        *,
        fast=False,
    ):

        model = self._select_model(
            fast=fast
        )

        if fast:

            response = self.client.chat(
                model=model,
                messages=messages,
                options={
                    "temperature": 0.15,
                    "num_predict": 96,
                    "top_k": 20,
                    "top_p": 0.8,
                },
                keep_alive="10m",
            )

        else:

            response = self.client.chat(
                model=model,
                messages=messages,
                options={
                    "temperature": 0.25,
                },
                keep_alive="10m",
            )

        return (
            response["message"]["content"]
        )

    def available(self):

        try:

            self.client.list()

            return True

        except Exception:

            return False
