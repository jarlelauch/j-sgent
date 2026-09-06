# PORT-PS: verifikasi J. S'GENT (tanpa paste besar)
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent)
Set-ExecutionPolicy -Scope Process Bypass -Force
if (Test-Path ".\.venv\Scripts\Activate.ps1") { . .\.venv\Scripts\Activate.ps1 }
python -m compileall app run.py server.py
python -c "from server import app; print('SERVER IMPORT: OK')"
python -c "from app.memory.obsidian import ObsidianMemory; from app.memory.brain import Brain; from app.core.config import OBSIDIAN_VAULT; b=Brain(ObsidianMemory(OBSIDIAN_VAULT)); print(b.status())"
