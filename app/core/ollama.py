from ollama import Client

from .config import OLLAMA_HOST, OLLAMA_MODEL


class OllamaBrain:

    def __init__(self):
        self.client = Client(host=OLLAMA_HOST)
        self.model = OLLAMA_MODEL

    def think(self, messages):
        response = self.client.chat(
            model=self.model,
            messages=messages,
        )

        return response["message"]["content"]
