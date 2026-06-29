# orca-validator

**ORCA-verification-as-a-service for business documents.**

Upload a business document (starting with **contracts**), and the service OCRs it, structures it
into typed fields, and validates it against a **formally-verified [ORCA](https://github.com/jascal/orca-lang)
state machine** — returning a pass/fail verdict with reasons. The validation rules are not ad-hoc
code; they are an ORCA machine whose control flow has been topology-verified before it is ever
allowed to run. *The verification is the product.*

Served at `orca.cyberiad.ai`.

## Status

✅ **MVP implemented** (the `bootstrap-orca-validator` OpenSpec change, 30/30). The full spine
works end-to-end against the real `orca_runtime_python` + Postgres, with a thin Next.js UI.
`13` backend tests pass (verification gate, OCR, ORCA bridge incl. snapshot resume, e2e demo).

```bash
cp .env.example .env            # set API_KEY
make install                    # npm (verifier) + pip install -e ".[dev]"
make verify-machines            # topology gate — must pass
docker compose up -d --build    # api + web + its own postgres + redis (CPU/mem limited)
docker compose exec api alembic upgrade head
# API:  http://localhost:8080   (programmatic / CI)
# UI:   http://localhost:3000   (drop a contract PDF → verdict + machine diagram)
```

Run the tests: `make test`. Design + tasks live in `openspec/changes/bootstrap-orca-validator/`.

## How it works (two layers, mirroring ORCA)

1. **Spec verification (build + boot, TypeScript).** Every `machines/*.orca.md` is topology-
   verified by the `@orcalang` CLI in CI and re-checked at startup; the service refuses to boot on
   an unverified machine.
2. **Document validation (runtime, Python).** A PDF is OCR'd (PyMuPDF, tesseract fallback),
   structured into typed fields, and run through the verified machine; the machine's final state
   + context is the verdict.

## Stack

Python 3.11 · FastAPI · SQLAlchemy[asyncio] + asyncpg over PostgreSQL · Redis-backed worker ·
PyMuPDF/tesseract OCR · `orca-runtime-python` · `@orcalang/orca-lang` verifier CLI (the `orca` bin; TypeScript,
build/boot gate only). Optional thin Next.js UI.

Patterns emulate `agent_framework/modules/revenue_cycle` (`eob_ocr.py`, `orca_bridge.py`,
`machine_persistence.py`).
