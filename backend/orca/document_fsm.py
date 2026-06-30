"""Verify + render an AI-extracted document FSM (supports hierarchical / nested states).

Runs the REAL ORCA verifier on the extracted .orca.md (reachability / deadlock / determinism /
completeness — works for nested machines too), then builds the Mermaid diagram ourselves from the
.orca.md so composite states render as proper nested boxes with readable labels (ORCA's own Mermaid
only declares a composite's initial child inside the box). A verifier failure is a *result*, not an
error — it means the document's described process has a structural flaw.
"""
import os
import re
import subprocess
import tempfile

from backend.orca.verification import _orca_cli


def _humanize(sid: str) -> str:
    s = re.sub(r"_(state|phase|status|st)$", "", sid)
    return s.replace("_", " ").strip().title() or sid


def _parse_machine(orca_md: str):
    """Parse states (with hierarchy via heading level) + transitions from the .orca.md."""
    lines = orca_md.splitlines()
    states: list[dict] = []
    transitions: list[tuple[str, str, str]] = []
    stack: list[tuple[int, str]] = []  # (heading level, state id) → determines parent

    for idx, raw in enumerate(lines):
        sm = re.match(r"^(#+)\s+state\s+([A-Za-z0-9_]+)\s*(?:\[([^\]]*)\])?\s*$", raw)
        if sm:
            level, sid, ann = len(sm.group(1)), sm.group(2), (sm.group(3) or "")
            while stack and stack[-1][0] >= level:
                stack.pop()
            parent = stack[-1][1] if stack else None
            label = ""
            for j in range(idx + 1, min(idx + 4, len(lines))):
                if re.match(r"^#+\s+state", lines[j]):
                    break
                t = lines[j].strip()
                if t.startswith(">"):
                    label = t.lstrip(">").strip().replace('"', "").replace(":", "")
                    break
            states.append({
                "id": sid, "label": (label or _humanize(sid))[:52],
                "initial": "initial" in ann, "final": "final" in ann, "parent": parent,
            })
            stack.append((level, sid))
            continue
        tm = re.match(r"^\|(.+)\|\s*$", raw)
        if tm and "-->" not in raw:
            cols = [c.strip() for c in tm.group(1).split("|")]
            if len(cols) >= 4 and cols[0] and cols[0].lower() != "source" and set(cols[0]) - set("-: "):
                transitions.append((cols[0], cols[1], cols[3]))
    return states, transitions


def _build_mermaid(orca_md: str) -> str | None:
    """Emit nested-aware Mermaid (composite states as boxes-within-boxes) with readable labels."""
    states, transitions = _parse_machine(orca_md)
    if not states:
        return None
    by_id = {s["id"]: s for s in states}
    children: dict[str, list[dict]] = {}
    for s in states:
        if s["parent"]:
            children.setdefault(s["parent"], []).append(s)
    composites = set(children)
    parent_of = lambda sid: (by_id.get(sid) or {}).get("parent")

    internal: dict[str, list[tuple[str, str, str]]] = {c: [] for c in composites}
    toplevel: list[tuple[str, str, str]] = []
    for src, evt, tgt in transitions:
        ps, pt = parent_of(src), parent_of(tgt)
        (internal[ps] if ps and ps == pt else toplevel).append((src, evt, tgt))  # type: ignore[arg-type]

    def edge(src, evt, tgt, ind):
        return f"{ind}{src} --> {tgt}" + (f" : {evt}" if evt else "")

    out = ["stateDiagram-v2", "  direction LR", ""]
    # top-level leaf labels
    for s in states:
        if not s["parent"] and s["id"] not in composites:
            out.append(f'  {s["id"]} : {s["label"]}')
    for s in states:
        if s["initial"] and not s["parent"]:
            out.append(f'  [*] --> {s["id"]}')
    for s in states:
        if s["final"] and not s["parent"]:
            out.append(f'  {s["id"]} --> [*]')
    # composite boxes
    for c in sorted(composites):
        out.append(f'  state "{by_id[c]["label"]}" as {c} {{')
        kids = children[c]
        for k in kids:
            out.append(f'    {k["id"]} : {k["label"]}')
        for k in kids:
            if k["initial"]:
                out.append(f'    [*] --> {k["id"]}')
        for k in kids:
            if k["final"]:
                out.append(f'    {k["id"]} --> [*]')
        for src, evt, tgt in internal[c]:
            out.append(edge(src, evt, tgt, "    "))
        out.append("  }")
    for src, evt, tgt in toplevel:
        out.append(edge(src, evt, tgt, "  "))
    return "\n".join(out)


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
    except Exception as e:  # noqa: BLE001
        return {"orca_md": orca_md, "mermaid": None, "verified": False, "report": f"error: {e}"}
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass

    try:
        mermaid = _build_mermaid(orca_md)
    except Exception:  # noqa: BLE001 — never let diagram generation fail the run
        mermaid = None
    return {
        "orca_md": orca_md,
        "mermaid": mermaid,
        "verified": verify.returncode == 0,
        "report": (verify.stdout + verify.stderr).strip(),
    }
