"""Brain = konektor ringan OrbitalEngine <-> Obsidian Vault.

Bukan embeddings / vector DB. Keyword recall + auto-log,
dibuat ringan untuk Ryzen 5 3500U / RAM 8GB.
"""
from pathlib import Path


IDENTITY_MD = """---
type: core
agent: J. S'GENT
---

# J. S'GENT - Identity

Project: JAR TOOLS
UI identity: J. S'GENT
Core visual: Salib Petrus terbalik (inverted cross)

Batang atas panjang, palang dekat bawah, batang bawah pendek.
Elemen pertama yang dikenali dari jauh harus salib.

Engine: OrbitalEngine (FAST 1 / NORMAL 5 / HIGH 15 / ULTRA 50)
Local brain: Ollama qwen3:8b-q4_K_M, FAST qwen3:1.7b
Memory: Obsidian Vault ini sebagai external brain.
"""

SYSTEM_MD = """---
type: core
agent: J. S'GENT
---

# System

- LOCAL ENGINE tanpa HTTP (run.py). UI web dibekukan di web/static/index.html.
- HTTP / server.py hanya untuk hosting gratis nanti.
- Laptop = development machine, bukan server publik 24/7.
- R2010 = VPN edge, bukan compute AI.

Aturan orbit:
- FAST: 1 orbit, prompt minimal, tanpa research.
- NORMAL: 5 orbit + cross-provider review.
- HIGH: 15 orbit + parallel + adversarial.
- ULTRA: 50 orbit + research + evidence.
"""

PROVIDERS_MD = """---
type: core
agent: J. S'GENT
---

# Providers

- ollama: aktif lokal (qwen3:8b-q4_K_M, fast qwen3:1.7b)
- clipper: slot kosong
- custom: slot kosong

Rotation: capability + reliability + quality + diversity.
Reviewer harus beda provider bila cross-review aktif.
"""


class Brain:

    def __init__(self, obsidian_memory):
        self.mem = obsidian_memory
        self.ensure_identity()

    def ensure_identity(self):
        try:
            core = self.mem.core
            files = {
                "identity.md": IDENTITY_MD,
                "system.md": SYSTEM_MD,
                "providers.md": PROVIDERS_MD,
            }
            for name, content in files.items():
                path = Path(core) / name
                if not path.exists():
                    path.write_text(content, encoding="utf-8")
        except Exception:
            pass

    def _keywords(self, text, limit=4):
        words = []
        for w in text.lower().split():
            w = "".join(c for c in w if c.isalnum())
            if len(w) >= 4 and w not in words:
                words.append(w)
            if len(words) >= limit:
                break
        return words or [text.lower()[:20]]

    def recall(self, query, budget=2000, max_files=3):
        """Kembalikan snippet relevan, tidak pernah raise."""
        try:
            seen = set()
            chunks = []
            for kw in self._keywords(query):
                try:
                    results = self.mem.search(kw)
                except Exception:
                    continue
                for r in results:
                    fp = r.get("file", "")
                    if fp in seen:
                        continue
                    seen.add(fp)
                    text = (r.get("content") or "")[:800]
                    chunks.append(f"[{Path(fp).name}]\n{text}")
                    if len(chunks) >= max_files:
                        break
                if len(chunks) >= max_files:
                    break
            out = "\n\n".join(chunks)
            return out[-budget:] if out else ""
        except Exception:
            return ""

    def log_task(self, state):
        """Simpan experience tiap task selesai. Tidak pernah raise."""
        try:
            providers = []
            for h in getattr(state, "history", [])[-5:]:
                providers.append(f"{h.index}:{h.purpose}:{h.provider}")
            content = (
                f"objective: {state.objective}\n"
                f"mode: {state.mode.value}\n"
                f"orbits: {state.orbit_count}\n"
                f"confidence: {state.confidence:.2f}\n"
                f"trace: {', '.join(providers)}\n\n"
                f"CORE:\n{(state.core_answer or '')[:2000]}\n"
            )
            title = f"task {state.mode.value} {state.orbit_count}orbit"
            return self.mem.experience_log(title, content)
        except Exception:
            return None

    def status(self):
        try:
            files = list(self.mem.vault.rglob("*.md"))
            return {
                "vault": str(self.mem.vault),
                "notes": len(files),
            }
        except Exception as exc:
            return {"vault": str(getattr(self.mem, "vault", "?")), "error": str(exc)}
