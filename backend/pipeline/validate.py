"""End-to-end validation: OCR → extract → drive the verified machine → persist verdict.

The machine's final state IS the verdict — this module does not duplicate the validation
rules, it only feeds the machine extracted facts and reads its outcome. Idempotent per run.

MVP runs synchronously (invoked via FastAPI BackgroundTasks). The Redis worker (§4.1) swaps
in behind the same `run_validation` entrypoint later.
"""
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from backend.app.config import get_settings
from backend.app.database import AsyncSessionLocal
from backend.models import Document, ValidationResult, ValidationRun
from backend.ocr.extract import get_extractor
from backend.ocr.reader import read_pdf
from backend.orca.bridge import get_bridge
from backend.storage.blobs import get_blob_store

logger = logging.getLogger(__name__)


async def run_validation(run_id: UUID) -> None:
    settings = get_settings()

    async with AsyncSessionLocal() as db:
        run = (await db.execute(select(ValidationRun).where(ValidationRun.id == run_id))).scalars().first()
        if run is None or run.status in ("done", "failed", "running"):
            return  # idempotent: never re-run a claimed/finished run
        doc = (await db.execute(select(Document).where(Document.id == run.document_id))).scalars().first()
        run.status = "running"
        run.started_at = datetime.utcnow()
        doc.status = "running"
        doc_type, blob_ref, owner, document_id = doc.doc_type, doc.blob_ref, doc.owner, str(doc.id)
        await db.commit()

    bridge = get_bridge()
    entity_id = str(run_id)
    verdict, final_state, reasons, fields = "error", "error", ["unknown"], {}

    try:
        await bridge.get_or_create(doc_type, entity_id, {
            "document_id": document_id, "owner": owner, "tenant_id": owner,
        })
        ocr = read_pdf(get_blob_store().path(blob_ref), dpi=settings.OCR_DPI)
        if not ocr.ok:
            _, machine = await bridge.send(doc_type, entity_id, "EXTRACTION_FAILED", {"error": ocr.error})
        else:
            ext = get_extractor(doc_type, settings.EXTRACTOR).extract(ocr)
            fields = ext["fields"]
            await bridge.send(doc_type, entity_id, "EXTRACTED", ext)
            _, machine = await bridge.send(doc_type, entity_id, "EVALUATE", {})
        final_state = str(machine.state)
        ctx = machine.context
        verdict = ctx.get("verdict") or ("error" if final_state == "error" else "fail")
        reasons = ctx.get("reasons", [])
    except Exception as e:  # noqa: BLE001 — fail the run loudly, record the reason
        logger.exception("validation run %s failed", run_id)
        verdict, final_state, reasons = "error", "error", [str(e)]

    async with AsyncSessionLocal() as db:
        run = (await db.execute(select(ValidationRun).where(ValidationRun.id == run_id))).scalars().first()
        doc = (await db.execute(select(Document).where(Document.id == run.document_id))).scalars().first()
        db.add(ValidationResult(
            run_id=run_id, verdict=verdict, final_state=final_state,
            reasons=list(reasons), extracted_fields=fields, machine_context={},
        ))
        run.status = "done" if verdict in ("pass", "fail") else "failed"
        run.finished_at = datetime.utcnow()
        if verdict == "error":
            run.error = "; ".join(map(str, reasons))[:1000]
        doc.status = run.status
        await db.commit()
