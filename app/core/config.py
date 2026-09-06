from pathlib import Path
import os
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(override=False)
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]

APP_NAME = "J. S'GENT"

OLLAMA_HOST = "http://127.0.0.1:11434"

# Model utama untuk NORMAL / HIGH / ULTRA
OLLAMA_MODEL = "qwen3:8b-q4_K_M"

# Model cepat untuk FAST.
# Kalau belum tersedia, sistem akan fallback ke OLLAMA_MODEL.
OLLAMA_FAST_MODEL = "qwen3:1.7b"

# Muse Spark 1.2 free (OpenCode hosted) — single-account auth via env
MUSE_MODEL = os.getenv("MUSE_MODEL", "opencode/muse-spark-1.2-contributor-free")
MUSE_API_BASE = os.getenv("MUSE_API_BASE", "https://api.opencode.ai/v1")
MUSE_API_KEY = os.getenv("MUSE_API_KEY", "")

# Single-account login for web (http local + gratisan)
SINGLE_USER = os.getenv("JSGENT_USER", "admin")
SINGLE_PASS = os.getenv("JSGENT_PASS", "jsGENT-2026")
SESSION_SECRET = os.getenv("JSGENT_SECRET", "js-gent-local-secret-please-change")

OBSIDIAN_VAULT = (
    PROJECT_ROOT
    / "obsidian"
    / "J S'GENT"
)

MEMORY_PATH = (
    PROJECT_ROOT
    / "data"
    / "memory"
    / "memory.json"
)
