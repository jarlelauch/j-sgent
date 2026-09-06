from .ollama import OllamaBrain
from .config import MEMORY_PATH
from ..memory.memory import Memory
from ..tools.registry import ToolRegistry


class Agent:

    def __init__(self):
        self.brain = OllamaBrain()
        self.memory = Memory(MEMORY_PATH)
        self.tools = ToolRegistry()

        self.messages = []

    def register_tool(
        self,
        name,
        description,
        function,
    ):
        self.tools.register(
            name,
            description,
            function,
        )

    def build_context(self):

        tools = []

        for tool in self.tools.list_tools():
            tools.append(
                f"- {tool.name}: {tool.description}"
            )

        if not tools:
            return "No tools available."

        return "\n".join(tools)

    def run(self, task: str):

        system = f"""
You are J. S'GENT.

You are an AI AGENT, not merely a chatbot.

Your objective is to solve tasks by:
1. Understanding the objective.
2. Determining what actions are required.
3. Using available tools when appropriate.
4. Observing tool results.
5. Continuing until the task is complete.
6. Reporting the result clearly.

Available tools:

{self.build_context()}
"""

        self.messages = [
            {
                "role": "system",
                "content": system,
            },
            {
                "role": "user",
                "content": task,
            },
        ]

        return self.brain.think(self.messages)
