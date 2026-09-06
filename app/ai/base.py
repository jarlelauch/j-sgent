from abc import ABC, abstractmethod


class AIProvider(ABC):

    name: str = "unknown"

    @abstractmethod
    def generate(self, messages, *, fast=False):
        raise NotImplementedError

    def available(self) -> bool:
        return True
