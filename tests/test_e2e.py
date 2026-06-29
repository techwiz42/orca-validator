"""End-to-end demo (§5.4): upload a contract PDF → OCR → verified machine → verdict.

Exercises the full spine through the real FastAPI app, ORCA runtime, and Postgres.
"""
from uuid import UUID

import fitz  # PyMuPDF
import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app
from backend.pipeline.validate import run_validation

pytestmark = pytest.mark.asyncio(loop_scope="session")

GOOD_CONTRACT = (
    "This Agreement is made by and between Acme Corp and Beta LLC.\n"
    "Effective Date: January 1, 2026.\nTerm: twelve (12) months.\n"
    "Governing Law: the laws of the State of Delaware.\n"
    "IN WITNESS WHEREOF, the parties have signed below.\n"
)
BAD_CONTRACT = "A short note that is not really a contract and is missing everything.\n"
AUTH = {"Authorization": "Bearer testkey"}


def _pdf(text: str) -> bytes:
    doc = fitz.open()
    doc.new_page().insert_text((72, 100), text)
    data = doc.tobytes()
    doc.close()
    return data


async def _submit_and_resolve(client: AsyncClient, text: str) -> dict:
    r = await client.post(
        "/documents", headers=AUTH,
        files={"file": ("c.pdf", _pdf(text), "application/pdf")},
        data={"doc_type": "contract"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Deterministic: run the pipeline explicitly (idempotent with the scheduled BackgroundTask).
    await run_validation(UUID(body["run_id"]))
    res = (await client.get(f"/documents/{body['document_id']}/result", headers=AUTH)).json()
    return res


async def test_unauthenticated_is_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/documents", files={"file": ("c.pdf", _pdf("x"), "application/pdf")})
        assert r.status_code == 401


async def test_valid_contract_passes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await _submit_and_resolve(client, GOOD_CONTRACT)
        assert res["ready"] is True, res
        assert res["verdict"] == "pass", res
        assert res["final_state"].endswith("valid")
        assert res["machine_id"] == "contract_validation"
        assert res["machine_hash"] and res["machine_hash"] != "unknown"


async def test_incomplete_contract_fails_with_reasons():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await _submit_and_resolve(client, BAD_CONTRACT)
        assert res["ready"] is True, res
        assert res["verdict"] == "fail", res
        assert res["reasons"], "a failing verdict must explain why"
