from fastapi import APIRouter, HTTPException

from backend.app.state import VERIFIED_MACHINES
from backend.orca.diagram import mermaid_for
from backend.orca.registry import MACHINE_IDS, supported_doc_types
from backend.schemas import MachineSummary

router = APIRouter(tags=["machines"])


@router.get("/machines", response_model=list[MachineSummary])
async def list_machines():
    out = []
    for dt in supported_doc_types():
        mid = MACHINE_IDS[dt]
        h = VERIFIED_MACHINES.get(f"{mid}.orca.md")
        out.append(MachineSummary(doc_type=dt, machine_id=mid, verified=h is not None, hash=h))
    return out


@router.get("/machines/{machine_id}")
async def get_machine(machine_id: str):
    doc_type = next((d for d, m in MACHINE_IDS.items() if m == machine_id), None)
    if not doc_type:
        raise HTTPException(404, "machine not found")
    h = VERIFIED_MACHINES.get(f"{machine_id}.orca.md")
    return {
        "doc_type": doc_type,
        "machine_id": machine_id,
        "verified": h is not None,
        "hash": h,
        "mermaid": mermaid_for(machine_id),
    }
