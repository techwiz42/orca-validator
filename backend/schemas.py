"""Pydantic request/response models."""
from uuid import UUID

from pydantic import BaseModel


class SubmitResponse(BaseModel):
    document_id: UUID
    run_id: UUID
    status: str


class StatusResponse(BaseModel):
    document_id: UUID
    run_id: UUID
    status: str
    doc_type: str
    machine_id: str


class ResultResponse(BaseModel):
    run_id: UUID
    status: str
    ready: bool
    verdict: str | None = None
    final_state: str | None = None
    reasons: list = []
    extracted_fields: dict = {}
    machine_id: str | None = None
    machine_hash: str | None = None
    # AI-assisted layer (not part of the verified verdict)
    analysis: dict = {}
    analysis_status: str = "skipped"      # done | skipped | error | budget_exceeded
    revised_available: bool = False       # download via /documents/{id}/revised.(md|docx)
    revised_redline: str | None = None    # {--removed--}/{++added++} markup for the in-UI redline
    document_fsm: dict = {}                # the FSM the document expresses: {mermaid, verified, report}


class MachineSummary(BaseModel):
    machine_id: str
    verified: bool
    hash: str | None = None
    doc_type: str | None = None   # set only for runtime-executed validation machines
