from uuid import UUID

from fastapi import (APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.database import get_db
from backend.app.state import VERIFIED_MACHINES
from backend.deps import require_api_key
from backend.queue import enqueue
from backend.models import Document, ValidationResult, ValidationRun
from backend.orca.registry import MACHINE_IDS, supported_doc_types
from backend.pipeline.validate import run_validation
from backend.schemas import ResultResponse, StatusResponse, SubmitResponse
from backend.storage.blobs import get_blob_store

router = APIRouter(tags=["documents"])


async def _latest_run(db: AsyncSession, document_id: UUID) -> ValidationRun | None:
    return (await db.execute(
        select(ValidationRun)
        .where(ValidationRun.document_id == document_id)
        .order_by(ValidationRun.queued_at.desc())
    )).scalars().first()


@router.post("/documents", response_model=SubmitResponse)
async def submit_document(
    background: BackgroundTasks,
    doc_type: str = Form("contract"),
    file: UploadFile = File(...),
    subject: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    if doc_type not in supported_doc_types():
        raise HTTPException(400, f"unsupported doc_type {doc_type!r}; supported: {supported_doc_types()}")
    data = await file.read()
    if not data:
        raise HTTPException(400, "empty upload")

    blob_ref = get_blob_store().put(data, suffix=".pdf")
    doc = Document(owner=subject, doc_type=doc_type,
                   filename=file.filename or "upload.pdf", blob_ref=blob_ref, status="queued")
    db.add(doc)
    await db.flush()

    machine_id = MACHINE_IDS[doc_type]
    run = ValidationRun(
        document_id=doc.id, machine_id=machine_id, machine_version="0.1.30",
        machine_hash=VERIFIED_MACHINES.get(f"{machine_id}.orca.md", "unknown"), status="queued",
    )
    db.add(run)
    await db.commit()

    # Off-request processing: Redis worker if enabled, else in-process BackgroundTask.
    if get_settings().USE_REDIS_QUEUE:
        await enqueue(run.id)
    else:
        background.add_task(run_validation, run.id)
    return SubmitResponse(document_id=doc.id, run_id=run.id, status="queued")


@router.get("/documents/{document_id}", response_model=StatusResponse)
async def get_document(document_id: UUID, subject: str = Depends(require_api_key),
                       db: AsyncSession = Depends(get_db)):
    doc = (await db.execute(select(Document).where(Document.id == document_id))).scalars().first()
    if not doc:
        raise HTTPException(404, "document not found")
    run = await _latest_run(db, document_id)
    if not run:
        raise HTTPException(404, "no validation run for document")
    return StatusResponse(document_id=doc.id, run_id=run.id, status=run.status,
                          doc_type=doc.doc_type, machine_id=run.machine_id)


@router.get("/documents/{document_id}/result", response_model=ResultResponse)
async def get_result(document_id: UUID, subject: str = Depends(require_api_key),
                     db: AsyncSession = Depends(get_db)):
    run = await _latest_run(db, document_id)
    if not run:
        raise HTTPException(404, "no validation run for document")
    res = (await db.execute(
        select(ValidationResult).where(ValidationResult.run_id == run.id)
    )).scalars().first()
    if res is None:
        # not ready — an explicit "still running", never a fabricated result
        return ResultResponse(run_id=run.id, status=run.status, ready=False)
    return ResultResponse(
        run_id=run.id, status=run.status, ready=True,
        verdict=res.verdict, final_state=res.final_state, reasons=res.reasons,
        extracted_fields=res.extracted_fields, machine_id=run.machine_id, machine_hash=run.machine_hash,
    )
