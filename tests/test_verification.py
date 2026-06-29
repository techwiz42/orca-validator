"""The verification gate is the product guarantee — test that it accepts a valid machine
and rejects a broken one. These shell out to the real @orcalang verifier (node + the CLI
must be installed; `make install`)."""
from pathlib import Path

from backend.orca.verification import (
    MachineVerificationError,
    verify_machine_file,
    verify_machines_dir,
)

GOOD = Path("machines/contract_validation.orca.md")

# Incomplete: state s1 does not handle event B → ORCA INCOMPLETE_EVENT_HANDLING.
BROKEN = """# machine Broken

## events
- A
- B

## state s1 [initial]
## state s2 [final]

## transitions
| Source | Event | Guard | Target | Action |
|---|---|---|---|---|
| s1 | A | | s2 | |
"""


def test_good_machine_verifies():
    ok, out = verify_machine_file(GOOD)
    assert ok, out


def test_broken_machine_is_rejected(tmp_path):
    f = tmp_path / "broken.orca.md"
    f.write_text(BROKEN)
    ok, out = verify_machine_file(f)
    assert not ok
    assert "INCOMPLETE" in out.upper() or "ERROR" in out.upper()


def test_dir_gate_returns_verified_hashes():
    verified = verify_machines_dir("machines")
    assert "contract_validation.orca.md" in verified
    assert len(verified["contract_validation.orca.md"]) == 32  # sha256[:32]


def test_dir_gate_raises_on_broken(tmp_path):
    (tmp_path / "broken.orca.md").write_text(BROKEN)
    try:
        verify_machines_dir(str(tmp_path))
        assert False, "expected MachineVerificationError"
    except MachineVerificationError as e:
        assert "refusing to boot" in str(e)
