from .providers.ollama import OllamaProvider
from .providers.clipper import ClipperProvider
from .providers.custom import CustomProvider

try:
    from .providers.muse import MuseProvider  # Muse Spark 1.2 free
    _has_muse = True
except Exception:
    MuseProvider = None  # type: ignore
    _has_muse = False


class AIRouter:

    def __init__(self):

        self.providers = {}

        self.register(OllamaProvider())
        if _has_muse and MuseProvider is not None:
            try:
                self.register(MuseProvider())
            except Exception:
                pass
        self.register(ClipperProvider())
        self.register(CustomProvider())

    def register(self, provider):
        self.providers[provider.name] = provider

    def get(self, name):
        return self.providers.get(name)

    def available(self):

        return {
            name: provider.available()
            for name, provider in self.providers.items()
        }

    def choose(self, preferred=None):

        if preferred:
            provider = self.get(preferred)

            if provider and provider.available():
                return provider

        for provider in self.providers.values():

            if provider.available():
                return provider

        raise RuntimeError(
            "Tidak ada AI provider yang tersedia."
        )

    def generate(self, messages, preferred=None, *, fast=False):

        provider = self.choose(preferred)

        return provider.generate(messages, fast=fast)
