from ..base import AIProvider


class ClipperProvider(AIProvider):

    name = "clipper"

    def generate(self, messages, *, fast=False):
        raise RuntimeError(
            "Clipper provider belum dikonfigurasi."
        )

    def available(self):
        return False
