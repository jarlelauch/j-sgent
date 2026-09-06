from ..base import AIProvider


class CustomProvider(AIProvider):

    name = "custom"

    def generate(self, messages, *, fast=False):
        raise RuntimeError(
            "Custom provider belum dikonfigurasi."
        )

    def available(self):
        return False
