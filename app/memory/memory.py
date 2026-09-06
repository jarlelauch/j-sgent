import json
from pathlib import Path


class Memory:

    def __init__(self, path: Path):
        self.path = path

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.path.exists():
            self.path.write_text(
                "[]",
                encoding="utf-8",
            )

    def load(self):
        return json.loads(
            self.path.read_text(
                encoding="utf-8"
            )
        )

    def save(self, memories):
        self.path.write_text(
            json.dumps(
                memories,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def add(self, content: str):
        memories = self.load()

        memories.append({
            "content": content,
        })

        self.save(memories)

    def recall(self):
        return self.load()
