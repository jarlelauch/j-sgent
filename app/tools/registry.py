from dataclasses import dataclass
from typing import Callable


@dataclass
class Tool:
    name: str
    description: str
    function: Callable


class ToolRegistry:

    def __init__(self):
        self.tools: dict[str, Tool] = {}

    def register(
        self,
        name: str,
        description: str,
        function: Callable,
    ):
        self.tools[name] = Tool(
            name=name,
            description=description,
            function=function,
        )

    def get(self, name: str):
        return self.tools.get(name)

    def list_tools(self):
        return list(self.tools.values())
