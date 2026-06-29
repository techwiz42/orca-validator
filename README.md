# orca-validator

**ORCA-verification-as-a-service for business documents.**

Upload a business document (starting with **contracts**), and the service OCRs it, structures it
into typed fields, and validates it against a **formally-verified [ORCA](https://github.com/jascal/orca-lang)
state machine** — returning a pass/fail verdict with reasons. The validation rules are not ad-hoc
code; they are an ORCA machine whose control flow has been topology-verified before it is ever
allowed to run. *The verification is the product.*

Served at `orca.cyberiad.ai`.

## Status

📋 **Spec-first, pre-implementation.** The full design lives in OpenSpec:

```
openspec/changes/bootstrap-orca-validator/   # proposal · design · tasks · specs
```

```bash
openspec show bootstrap-orca-validator      # read the change
openspec validate bootstrap-orca-validator  # validate the spec
```

No application code yet — the next step is `/opsx:apply bootstrap-orca-validator`.

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
