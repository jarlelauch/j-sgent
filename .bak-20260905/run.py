"""J. S'GENT - Local CLI (tanpa HTTP) + Otak Obsidian.

Satu engine dengan server.py, tapi langsung lokal:
PowerShell -> run.py -> OrbitalEngine + Brain(Obsidian) -> Ollama.
UI web dibekukan di web/static/index.html.
"""
import sys

from app.ai.router import AIRouter
from app.ai.orchestration import AgentMode, OrbitalEngine, get_policy
from app.core.config import OBSIDIAN_VAULT
from app.memory.obsidian import ObsidianMemory
from app.memory.brain import Brain


MODES = ("fast", "normal", "high", "ultra")


def parse_mode(value: str):
    value = value.strip().lower()
    if value in MODES:
        return AgentMode(value)
    return None


def print_help():
    print("Perintah:")
    print("  <tugas>                  jalankan task mode aktif")
    print("  mode fast|normal|high|ultra")
    print("  otak <query>             cari di Obsidian")
    print("  remember <judul> | <isi>  simpan memory")
    print("  learn <judul> | <isi>     simpan knowledge")
    print("  brain                    status otak")
    print("  help                     bantuan")
    print("  exit                     keluar")
    print()


def main():
    default_mode = AgentMode.FAST
    if len(sys.argv) >= 2:
        m = parse_mode(sys.argv[1])
        if m:
            default_mode = m

    print("=" * 50)
    print(" J. S'GENT - LOCAL + OTAK OBSIDIAN")
    print("=" * 50)
    print("UI web dibekukan. Tanpa HTTP/browser.")
    print()

    router = AIRouter()

    try:
        mem = ObsidianMemory(OBSIDIAN_VAULT)
        brain = Brain(mem)
        st = brain.status()
        print(f"Otak: {st.get('vault')} ({st.get('notes', 0)} notes)")
    except Exception as exc:
        print(f"Otak gagal: {exc}")
        brain = None

    engine = OrbitalEngine(router, memory=brain)

    try:
        print(f"Providers: {router.available()}")
    except Exception as exc:
        print(f"Providers check gagal: {exc}")

    mode = default_mode
    print(f"Mode awal: {mode.value} (FAST = ringan qwen3:1.7b)")
    print("Ketik 'help' untuk perintah.")
    print()

    while True:
        try:
            raw = input(f"YOU [{mode.value}] > ").strip()
        except KeyboardInterrupt:
            print()
            break

        if not raw:
            continue

        low = raw.lower()
        if low in {"exit", "quit"}:
            break
        if low == "help":
            print_help()
            continue
        if low == "brain":
            if brain:
                print(brain.status())
            else:
                print("Otak off.")
            print()
            continue
        if low.startswith("mode"):
            parts = low.split()
            if len(parts) == 2 and parse_mode(parts[1]):
                mode = parse_mode(parts[1])
                print(f"Mode -> {mode.value} ({get_policy(mode).max_orbits} orbits)\n")
            else:
                print("Pakai: mode fast|normal|high|ultra\n")
            continue
        if low.startswith("otak ") or low.startswith("search ") or low.startswith("memory "):
            q = raw.split(" ", 1)[1] if " " in raw else ""
            if brain and q:
                txt = brain.recall(q, budget=1500)
                print(txt or "(tidak ada yang relevan)\n")
            else:
                print("Otak off / query kosong.\n")
            continue
        if low.startswith("remember "):
            if not brain:
                print("Otak off.\n")
                continue
            body = raw[len("remember "):]
            if "|" in body:
                title, content = [s.strip() for s in body.split("|", 1)]
                p = brain.mem.remember(title, content)
                print(f"Tersimpan memory: {p}\n")
            else:
                print("Pakai: remember <judul> | <isi>\n")
            continue
        if low.startswith("learn "):
            if not brain:
                print("Otak off.\n")
                continue
            body = raw[len("learn "):]
            if "|" in body:
                title, content = [s.strip() for s in body.split("|", 1)]
                p = brain.mem.learn(title, content)
                print(f"Tersimpan knowledge: {p}\n")
            else:
                print("Pakai: learn <judul> | <isi>\n")
            continue

        policy = get_policy(mode)
        print(f"-- orbit {policy.max_orbits}x [{mode.value}] + otak...")

        def on_orbit(state, record):
            conf = int((record.confidence or 0) * 100)
            print(f"  [ORBIT {record.index:02d}/{policy.max_orbits}] {record.purpose} via {record.provider} ({conf}%)")

        try:
            state = engine.run(raw, mode, on_orbit=on_orbit)
            print()
            print("J. S'GENT >")
            print(state.core_answer or "(no output)")
            print(f"[conf {state.confidence:.2f} | {state.orbit_count} orbit | otak tersimpan]\n")
        except Exception as error:
            print(f"\nERROR:\n{error}\n")


if __name__ == "__main__":
    main()
