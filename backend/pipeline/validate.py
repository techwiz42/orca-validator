"""End-to-end validation: OCR → extract → drive the verified machine → persist verdict.

The machine's final state IS the verdict — this module does not duplicate the validation
rules, it only feeds the machine extracted facts and reads its outcome. Idempotent per run.

MVP runs synchronously (invoked via FastAPI BackgroundTasks). The Redis worker (§4.1) swaps
in behind the same `run_validation` entrypoint later.
"""
import logging
from datetime import datetime, timezone
from uuid import UUID


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC (matches the columns)

from sqlalchemy import select

from backend.app.config import get_settings
from backend.app.database import AsyncSessionLocal
from backend.models import Document, ValidationResult, ValidationRun
from backend.ocr.extract import get_extractor
from backend.ocr.reader import read_document
from backend.llm.together import analyze_contract, revise_contract
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
        run.started_at = _utcnow()
        doc.status = "running"
        doc_type, blob_ref, owner, document_id = doc.doc_type, doc.blob_ref, doc.owner, str(doc.id)
        await db.commit()

    bridge = get_bridge()
    entity_id = str(run_id)
    verdict, final_state, reasons, fields = "error", "error", ["unknown"], {}
    doc_text = ""

    try:
        await bridge.get_or_create(doc_type, entity_id, {
            "document_id": document_id, "owner": owner, "tenant_id": owner,
        })
        ocr = read_document(get_blob_store().path(blob_ref), dpi=settings.OCR_DPI)
        if not ocr.ok:
            _, machine = await bridge.send(doc_type, entity_id, "EXTRACTION_FAILED", {"error": ocr.error})
        else:
            doc_text = ocr.raw_text
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

    # AI-assisted layer (Together): full analysis + a redlined revision, on top of the verified
    # verdict. Best-effort + visible — a model/key failure is recorded, never silently swallowed,
    # and never blocks the machine-verified verdict.
    analysis: dict = {}
    revised_markdown = None
    analysis_status = "skipped"
    if doc_text and verdict != "error" and settings.llm_enabled:
        try:
            analysis = await analyze_contract(doc_text)
            revised_markdown = await revise_contract(doc_text, analysis)
            analysis_status = "done"
        except Exception as e:  # noqa: BLE001
            logger.exception("LLM analysis failed for run %s", run_id)
            analysis = {"error": str(e)[:500]}
            analysis_status = "error"

    async with AsyncSessionLocal() as db:
        run = (await db.execute(select(ValidationRun).where(ValidationRun.id == run_id))).scalars().first()
        doc = (await db.execute(select(Document).where(Document.id == run.document_id))).scalars().first()
        db.add(ValidationResult(
            run_id=run_id, verdict=verdict, final_state=final_state,
            reasons=list(reasons), extracted_fields=fields, machine_context={},
            analysis=analysis, revised_markdown=revised_markdown, analysis_status=analysis_status,
        ))
        run.status = "done" if verdict in ("pass", "fail") else "failed"
        run.finished_at = _utcnow()
        if verdict == "error":
            run.error = "; ".join(map(str, reasons))[:1000]
        doc.status = run.status
        await db.commit()
