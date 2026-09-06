from pathlib import Path

ALLOWED_ROOTS = [
    Path(r"C:\Users\realh\JAR TOOLS").resolve(),
]

BLOCKED = {".env", "id_rsa", "credentials"}

def _safe(p: Path) -> Path:
    rp = p.resolve()
    if any(str(rp).startswith(str(r)) for r in ALLOWED_ROOTS):
        if rp.name.lower() in BLOCKED:
            raise PermissionError(f"Blocked: {rp.name}")
        return rp
    raise PermissionError(f"Outside allowed root: {rp}")

def fs_read(path: str, limit: int = 4000) -> str:
    p = _safe(Path(path))
    if not p.exists():
        return f"NOT FOUND: {p}"
    if p.is_dir():
        return "\n".join(str(x.name) for x in p.iterdir())[:limit]
    try:
        return p.read_text(encoding="utf-8", errors="ignore")[:limit]
    except Exception as exc:
        return f"READ ERROR: {exc}"

def fs_write(path: str, content: str) -> str:
    p = _safe(Path(path))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"WROTE: {p}"

def fs_search(query: str, root: str = r"C:\Users\realh\JAR TOOLS\obsidian") -> str:
    q = query.lower()
    hits = []
    for f in Path(root).rglob("*.md"):
        try:
            t = f.read_text(encoding="utf-8", errors="ignore")
            if q in t.lower() or q in f.name.lower():
                hits.append(str(f))
                if len(hits) >= 10:
                    break
        except Exception:
            continue
    return "\n".join(hits) if hits else "(no hits)"
