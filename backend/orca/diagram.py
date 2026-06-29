"""Best-effort Mermaid diagram for a machine, via `orca compile mermaid`."""
import subprocess
from pathlib import Path

from backend.orca.verification import _orca_cli


def mermaid_for(machine_id: str) -> str | None:
    f = Path("machines") / f"{machine_id}.orca.md"
    if not f.exists():
        return None
    try:
        proc = subprocess.run(
            [*_orca_cli(), "compile", "mermaid", str(f)],
            capture_output=True, text=True, timeout=60,
        )
    except Exception:
        return None
    return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else None
