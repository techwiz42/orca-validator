"""Verify + compile an AI-extracted document FSM.

Takes the .orca.md the LLM produced for the document's own lifecycle, runs the REAL ORCA verifier
(reachability / deadlock / determinism / completeness) and the Mermaid compiler on it, then injects
a human-readable label for every state (the compiler emits bare snake_case ids otherwise). A
verifier failure is a *result*, not an error — it means the document's described process has a
structural flaw, which is exactly what we want to surface.
"""
import os
import re
import subprocess
import tempfile

from backend.orca.verification import _orca_cli


def _humanize(sid: str) -> str:
    s = re.sub(r"_(state|phase|status|st)$", "", sid)
    return s.replace("_", " ").strip().title() or sid


def _state_labels(orca_md: str) -> dict[str, str]:
    """Map state id -> human label (its `> description`, else a humanized id)."""
    labels: dict[str, str] = {}
    lines = orca_md.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^##\s+state\s+([A-Za-z0-9_]+)", line)
        if not m:
            continue
        sid = m.group(1)
        desc = ""
        for j in range(i + 1, min(i + 5, len(lines))):
            t = lines[j].strip()
            if t.startswith("##"):
                break
            if t.startswith(">"):
                desc = t.lstrip(">").strip()
                break
        desc = desc.replace('"', "").replace("\n", " ").strip()
        # a short description makes a good box label; a long sentence does not — fall back to the
        # humanized id in that case (clean "Draft" beats a truncated paragraph).
        labels[sid] = desc if 0 < len(desc) <= 45 else _humanize(sid)
    return labels


def _label_mermaid(mermaid: str | None, orca_md: str) -> str | None:
    """Inject `state "Label" as id` declarations so the diagram shows readable state names."""
    if not mermaid:
        return mermaid
    labels = _state_labels(orca_md)
    if not labels:
        return mermaid
    decls = [f'  state "{lab}" as {sid}' for sid, lab in labels.items()]
    lines = mermaid.splitlines()
    # insert after the 'direction ...' line if present, else just after the header
    idx = next((i for i, l in enumerate(lines) if l.strip().startswith("direction")), None)
    if idx is None:
        idx = next((i for i, l in enumerate(lines) if l.strip() == "stateDiagram-v2"), 0)
    lines[idx + 1 : idx + 1] = decls
    return "\n".join(lines)


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
        "mermaid": _label_mermaid(mermaid, orca_md),
        "verified": verify.returncode == 0,
        "report": report,
    }
