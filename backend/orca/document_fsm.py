"""Verify + compile an AI-extracted document FSM.

Takes the .orca.md the LLM produced for the document's own lifecycle, runs the REAL ORCA verifier
(reachability / deadlock / determinism / completeness) and the Mermaid compiler on it. A verifier
failure is a *result*, not an error — it means the document's described process has a structural
flaw (unreachable state, deadlock, …), which is exactly what we want to surface.
"""
import os
import subprocess
import tempfile

from backend.orca.verification import _orca_cli


def verify_and_compile(orca_md: str) -> dict:
    if not orca_md or "## state" not in orca_md:
        return {"orca_md": orca_md, "mermaid": None, "verified": False,
                "report": "no state machine could be extracted from the document"}

    fd, path = tempfile.mkstemp(suffix=".orca.md")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(orca_md)
        verify = subprocess.run([*_orca_cli(), "verify", path],
                                capture_output=True, text=True, timeout=60)
        compiled = subprocess.run([*_orca_cli(), "compile", "mermaid", path],
                                  capture_output=True, text=True, timeout=60)
    except Exception as e:  # noqa: BLE001
        return {"orca_md": orca_md, "mermaid": None, "verified": False, "report": f"error: {e}"}
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass

    report = (verify.stdout + verify.stderr).strip()
    mermaid = compiled.stdout.strip() if compiled.returncode == 0 and compiled.stdout.strip() else None
    return {
        "orca_md": orca_md,
        "mermaid": mermaid,
        "verified": verify.returncode == 0,
        "report": report,
    }
