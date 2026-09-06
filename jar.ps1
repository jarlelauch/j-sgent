# J. S'GENT launcher - PowerShell-first
param([string]$cmd = "start", [string]$mode = "fast")
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
if (Test-Path ".\.venv\Scripts\Activate.ps1") { Set-ExecutionPolicy -Scope Process Bypass -Force; . .\.venv\Scripts\Activate.ps1 }
switch ($cmd) {
  "start" { python run.py $mode }
  "test" { python -m compileall app run.py server.py; python -c "from server import app; print('SERVER IMPORT: OK')" }
  "brain" { python -c "from app.memory.obsidian import ObsidianMemory; from app.memory.brain import Brain; from app.core.config import OBSIDIAN_VAULT; b=Brain(ObsidianMemory(OBSIDIAN_VAULT)); print(b.status())" }
  default { Write-Host "pakai: .\jar.ps1 start|test|brain [mode]" }
}
