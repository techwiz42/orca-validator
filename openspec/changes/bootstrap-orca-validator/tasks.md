# Tasks

> Sequenced as vertical slices. **§5 is the thinnest viable MVP** — it proves the full spine
> (PDF → OCR → verified machine → verdict) with everything else stubbed minimally. §6–§8 harden
> and expand. Nothing here is built yet.

## 0. Repo & infrastructure scaffold

- [ ] 0.1 `pyproject.toml` (fastapi, sqlalchemy[asyncio], asyncpg, alembic, orca-runtime-python, pymupdf, pytesseract, pillow, redis, pydantic-settings) + `package.json` pinning only `@orcalang/orca`.
- [ ] 0.2 `docker-compose.yml`: `api`, `worker`, `postgres`, `redis` — each with explicit `cpus`/`mem_limit`; dedicated Postgres/Redis (never the builder's). `.env.example`, `Makefile` (`verify-machines`, `dev`, `test`, `migrate`).
- [ ] 0.3 `backend/app/database.py`: async engine with `pool_pre_ping=True` **and** `pool_timeout` (carry forward the agent_framework login-race lessons). `config.py` via pydantic-settings. `app/main.py` FastAPI app + lifespan skeleton.
- [ ] 0.4 Alembic wired; `GET /health` green against Postgres + Redis.

## 1. Verification gate (`machine-verification`)

- [ ] 1.1 `machines/contract_validation.orca.md` — the bootstrap contract-validation machine.
- [ ] 1.2 `make verify-machines` → `npx @orcalang/orca verify machines/*.orca.md`; non-zero exit fails the target. Wire into CI.
- [ ] 1.3 Boot gate: `main.py` lifespan verifies every registered machine at startup and **refuses to boot** on failure (mirrors `validate_access_logging_coverage`). Verified-machine metadata (id, version, hash) recorded.
- [ ] 1.4 Test: an intentionally-broken machine (unreachable state / non-deterministic guard) fails both `make verify-machines` and boot.

## 2. OCR ingestion (`document-ingestion`) — emulate `eob_ocr.py`

- [ ] 2.1 `backend/ocr/result.py` (`OCRResult`), `reader.py` (PyMuPDF text extraction; tesseract fallback for pages with no embedded text).
- [ ] 2.2 `backend/ocr/extract.py`: extractor interface → typed fields. Deterministic/heuristic extractor for the MVP doc type; LLM adapter behind the same interface (opt-in, off by default).
- [ ] 2.3 `backend/storage/`: blob put/get interface; local-volume implementation now (S3/Spaces adapter is a later task).
- [ ] 2.4 Tests: text PDF → fields; scanned (image-only) PDF → tesseract path exercised; no silent empty-result fallback (fail loudly on undecodable input).

## 3. ORCA bridge & persistence (`orca-validation`) — emulate `orca_bridge.py`

- [ ] 3.1 `backend/orca/persistence.py`: `AsyncPersistenceAdapter` over Postgres (snapshot save/load).
- [ ] 3.2 `backend/orca/bridge.py` (`OrcaBridge`): registry of `OrcaMachine`s, `load_or_start()`, auto-save snapshot after each transition.
- [ ] 3.3 `backend/orca/registry.py` (machine_id → def + actions) and `backend/orca/actions/` (the computation layer the machine invokes: field checks, record_* steps).
- [ ] 3.4 Test: drive a verified machine over a known field set → expected final state + reasons; snapshot survives a simulated restart (resume mid-run).

## 4. Pipeline & worker

- [ ] 4.1 `backend/queue.py` (Redis job queue) + `backend/pipeline/worker.py` (fixed, bounded worker pool).
- [ ] 4.2 `backend/pipeline/validate.py`: ingest → OCR/extract → run machine → persist `ValidationResult`. Idempotent per `document_id`.
- [ ] 4.3 Models + migrations: `Document`, `ValidationRun`, `ValidationResult`, `MachineSnapshot`.

## 5. MVP vertical slice  ⟵ THINNEST VIABLE PRODUCT

- [ ] 5.1 Doc type = `contract`; the `contract_validation` machine; deterministic contract-field extractor, local storage, shared-key auth.
- [ ] 5.2 `POST /documents` (upload one PDF) → enqueue → worker OCRs (PyMuPDF only) → runs the one verified machine → stores `ValidationResult`.
- [ ] 5.3 `GET /documents/{id}` (status) and `GET /documents/{id}/result` (verdict + reasons + extracted fields).
- [ ] 5.4 End-to-end test: upload a sample PDF, poll to completion, assert verdict + reasons. **This is the demo.**

## 6. API surface (`validation-api`)

- [ ] 6.1 `backend/api/machines.py`: `GET /machines` (registry of verified machines), `GET /machines/{id}` (topology + Mermaid via `@orcalang ... compile`).
- [ ] 6.2 Request validation, error contract (loud failures, no silent empties), pagination on list endpoints.
- [ ] 6.3 OpenAPI surface reviewed; shared-key auth dependency on all write endpoints.

## 7. Co-location hardening & deploy (`ops/`)

- [ ] 7.1 Confirm compose `cpus`/`mem_limit` on api + worker; bounded worker concurrency verified under load (a small flood must not starve Postgres).
- [ ] 7.2 `ops/nginx/orca.cyberiad.ai.conf` (subdomain vhost → this stack); TLS via the existing wildcard/cert story.
- [ ] 7.3 `ops/DEPLOY.md`: how it co-exists on the shared droplet; the "migrate to its own droplet" lift-and-shift checklist.

## 8. Optional — thin web UI (deferred)

- [ ] 8.1 `web/` (Next.js): drop-a-PDF upload, live status, verdict + the machine's Mermaid diagram. Ship only if API-first usage shows a UI is wanted.
