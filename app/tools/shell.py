import subprocess


def run_powershell(command: str) -> str:
    """Execute a PowerShell command and return its output."""

    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                command,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout.strip()
        error = result.stderr.strip()

        if result.returncode != 0:
            return f"COMMAND ERROR:`n{error or output}"

        return output or "(command returned no output)"

    except subprocess.TimeoutExpired:
        return "COMMAND ERROR: execution timed out."

    except Exception as exc:
        return f"COMMAND ERROR: {exc}"
