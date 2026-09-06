from datetime import datetime
from pathlib import Path


class ObsidianMemory:

    def __init__(self, vault_path: Path):
        self.vault = Path(vault_path)

        self.core = self.vault / "00_CORE"
        self.memory = self.vault / "01_MEMORY"
        self.knowledge = self.vault / "02_KNOWLEDGE"
        self.experience = self.vault / "03_EXPERIENCE"
        self.projects = self.vault / "04_PROJECTS"
        self.plans = self.vault / "05_PLANS"
        self.archive = self.vault / "99_ARCHIVE"

        self._ensure_directories()

    def _ensure_directories(self):
        for directory in [
            self.core,
            self.memory,
            self.knowledge,
            self.experience,
            self.projects,
            self.plans,
            self.archive,
        ]:
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )

    def write_note(
        self,
        folder: Path,
        filename: str,
        content: str,
    ):
        path = folder / filename

        if path.suffix.lower() != ".md":
            path = path.with_suffix(".md")

        path.write_text(
            content,
            encoding="utf-8",
        )

        return path

    def remember(self, title: str, content: str):

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        note = f"""---
type: memory
created: {timestamp}
agent: J. S'GENT
---

# {title}

{content}
"""

        filename = (
            datetime.now().strftime("%Y%m%d-%H%M%S")
            + "-"
            + title.replace(" ", "-")
            + ".md"
        )

        return self.write_note(
            self.memory,
            filename,
            note,
        )

    def learn(self, title: str, content: str):

        note = f"""---
type: knowledge
agent: J. S'GENT
---

# {title}

{content}
"""

        filename = title.replace(" ", "-") + ".md"

        return self.write_note(
            self.knowledge,
            filename,
            note,
        )

    def experience_log(
        self,
        title: str,
        content: str,
    ):

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        note = f"""---
type: experience
created: {timestamp}
agent: J. S'GENT
---

# {title}

{content}
"""

        filename = (
            datetime.now().strftime("%Y%m%d-%H%M%S")
            + "-"
            + title.replace(" ", "-")
            + ".md"
        )

        return self.write_note(
            self.experience,
            filename,
            note,
        )

    def search(self, query: str):

        query = query.lower()
        results = []

        for file in self.vault.rglob("*.md"):

            try:
                text = file.read_text(
                    encoding="utf-8"
                )
            except Exception:
                continue

            if query in text.lower():
                results.append({
                    "file": str(file),
                    "content": text,
                })

        return results
