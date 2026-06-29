"""ORCA machine topology verification — the hard build + boot gate.

Invokes the @orcalang/orca-lang verifier over each *.orca.md machine. The service
refuses to boot if any machine fails verification: the formal verification is the
product guarantee, so it is enforced by code, not discipline. We do NOT reimplement
the verifier — we shell out to the published CLI.
"""
import hashlib
import subprocess
from pathlib import Path


class MachineVerificationError(RuntimeError):
    pass


def _orca_cli() -> list[str]:
    """The @orcalang/orca-lang entry. Prefer the local install's node entry (prints
    diagnostics and returns the correct exit code); fall back to npx."""
    entry = Path("node_modules/@orcalang/orca-lang/dist/index.js")
    if entry.exists():
        return ["node", str(entry)]
    return ["npx", "--yes", "--package=@orcalang/orca-lang", "orca"]


def verify_machine_file(path: Path) -> tuple[bool, str]:
    """Return (passed, diagnostic_output) for one machine file."""
    try:
        proc = subprocess.run(
            [*_orca_cli(), "verify", str(path)],
            capture_output=True, text=True, timeout=120,
        )
    except FileNotFoundError as e:  # node / cli missing — fail loud, never skip
        raise MachineVerificationError(
            f"ORCA verifier CLI not available ({e}); cannot enforce the verification gate."
        ) from e
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def machine_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:32]


def verify_machines_dir(machines_dir: str) -> dict[str, str]:
    """Verify every *.orca.md in `machines_dir`. Raise on any failure (boot gate).

    Returns {machine_filename: content_hash} for verified machines so runs can be
    attributed to an exact verified spec.
    """
    d = Path(machines_dir)
    files = sorted(d.glob("*.orca.md"))
    if not files:
        raise MachineVerificationError(f"No *.orca.md machines found in {machines_dir!r}")

    verified: dict[str, str] = {}
    failures: list[str] = []
    for f in files:
        ok, out = verify_machine_file(f)
        if ok:
            verified[f.name] = machine_hash(f)
        else:
            failures.append(f"{f.name}:\n{out}")
    if failures:
        raise MachineVerificationError(
            "ORCA machine verification failed — refusing to boot:\n\n" + "\n\n".join(failures)
        )
    return verified
