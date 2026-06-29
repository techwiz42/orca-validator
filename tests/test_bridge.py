"""Drive the verified ContractValidation machine over known field sets against the REAL
orca_runtime_python runtime, and confirm snapshots resume after a simulated restart (§3.4)."""
import pytest

from backend.orca.bridge import OrcaBridge

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _ext(missing):
    fields = ["parties", "effective_date", "term", "signatures", "governing_law"]
    return {
        "missing_count": len(missing),
        "missing_fields": missing,
        "fields": {f: f not in missing for f in fields},
        **{f"has_{f}": int(f not in missing) for f in fields},
    }


async def test_machine_drives_to_valid():
    b = OrcaBridge()
    await b.get_or_create("contract", "run-valid", {"document_id": "d1", "owner": "o", "tenant_id": "o"})
    await b.send("contract", "run-valid", "EXTRACTED", _ext([]))
    _, m = await b.send("contract", "run-valid", "EVALUATE", {})
    assert "valid" in str(m.state) and "invalid" not in str(m.state)
    assert m.context.get("verdict") == "pass"


async def test_machine_drives_to_invalid():
    b = OrcaBridge()
    await b.get_or_create("contract", "run-invalid", {"document_id": "d2", "owner": "o", "tenant_id": "o"})
    await b.send("contract", "run-invalid", "EXTRACTED", _ext(["term", "signatures"]))
    _, m = await b.send("contract", "run-invalid", "EVALUATE", {})
    assert "invalid" in str(m.state)
    assert m.context.get("verdict") == "fail"
    assert any("term" in r for r in m.context.get("reasons", []))


async def test_snapshot_survives_restart():
    b1 = OrcaBridge()
    await b1.get_or_create("contract", "run-restart", {"document_id": "d3", "owner": "o", "tenant_id": "o"})
    await b1.send("contract", "run-restart", "EXTRACTED", _ext([]))
    # New bridge instance == simulated process restart; resume from the persisted snapshot.
    b2 = OrcaBridge()
    m = await b2.get_or_create("contract", "run-restart", {})
    assert "validating" in str(m.state)
