from fastapi import APIRouter, HTTPException

from backend.app.state import VERIFIED_MACHINES
from backend.orca.diagram import mermaid_for
from backend.orca.registry import MACHINE_IDS
from backend.schemas import MachineSummary

router = APIRouter(tags=["machines"])


def _stem(filename: str) -> str:
    return filename[: -len(".orca.md")] if filename.endswith(".orca.md") else filename


def _doc_type_for(machine_id: str) -> str | None:
    return next((d for d, m in MACHINE_IDS.items() if m == machine_id), None)


@router.get("/machines", response_model=list[MachineSummary])
async def list_machines():
    """Every verified machine — the runtime validation machine plus the decomposed component
    machines (ingestion, contract_validation, ai_assessment, document_pipeline)."""
    return [
        MachineSummary(machine_id=_stem(fn), verified=True, hash=h, doc_type=_doc_type_for(_stem(fn)))
        for fn, h in sorted(VERIFIED_MACHINES.items())
    ]


@router.get("/machines/{machine_id}")
async def get_machine(machine_id: str):
    fn = f"{machine_id}.orca.md"
    if fn not in VERIFIED_MACHINES:
        raise HTTPException(404, "machine not found")
    return {
        "machine_id": machine_id,
        "doc_type": _doc_type_for(machine_id),
        "verified": True,
        "hash": VERIFIED_MACHINES.get(fn),
        "mermaid": mermaid_for(machine_id),
    }
