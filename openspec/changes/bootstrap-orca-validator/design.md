# Design

## Architecture at a glance

```
PDF ──► API (FastAPI) ──► queue (Redis) ──► worker
                                              │
                          ┌───────────────────┼─────────────────────┐
                          ▼                    ▼                     ▼
                       OCR/extract        OrcaBridge            persistence
                    (PyMuPDF→fields)   (verified machine)       (Postgres)
                                              │
                                              ▼
                                       ValidationResult ──► GET /{id}/result
```

Two layers, mirroring ORCA itself:

1. **Spec verification (build + boot, TypeScript).** Every `machines/*.orca.md` is topology-
   verified by the `@orcalang` CLI. This runs in CI as a gate and again at service startup,
   which **refuses to boot** if any registered machine fails verification — the same discipline
   as agent_framework's `validate_access_logging_coverage` boot gate. No unverified machine ever
   executes. This is *the* product guarantee; it is not optional or best-effort.

2. **Document validation (runtime, Python).** The pipeline OCRs the PDF, structures it into
   typed fields, and drives the verified `OrcaMachine` over those fields. The machine's
   transitions/guards *are* the validation rules; its final state + context is the verdict.

## Why this stack (the "change it up" decision)

The earlier instinct was to consider a wholesale stack change for a greenfield repo. The grounded
answer is narrower and driven by the dependency, not novelty:

- **OCR is Python's home turf** and we are explicitly emulating `revenue_cycle/eob_ocr.py`
  (PyMuPDF + tesseract + LLM structuring). That pins the ingestion backend to **Python/FastAPI**.
- **ORCA execution** has a first-class Python runtime (`orca-runtime-python`) we already use.
- **ORCA verification** is TypeScript-first (`@orcalang` CLI). We do **not** port it to Python;
  we invoke the CLI as a build/boot tool. TypeScript enters the repo *only* as a verification
  tool (a `package.json` with the one CLI dep), not as a second runtime.

Net: a single Python service, Postgres, with the TS verifier as a sidecar gate. Postgres stays —
JSONB is ideal for the parsed AST, extracted fields, and verification reports. The only honest
"change" vs. the agent_framework stack is that this is a small, single-purpose service rather than
a module inside the monolith builder.

## Emulation map (agent_framework → orca-validator)

| agent_framework (revenue_cycle)        | orca-validator                          |
|----------------------------------------|-----------------------------------------|
| `sub_services/eob_ocr.py`              | `backend/ocr/` (reader, extract, result)|
| `orca_bridge.py` (`RCMOrcaBridge`)     | `backend/orca/bridge.py` (`OrcaBridge`) |
| `machine_persistence.py`               | `backend/orca/persistence.py`           |
| `actions/eob_actions.py`               | `backend/orca/actions/`                 |
| `activities/eob_activities.py`         | `backend/pipeline/` + `worker.py`       |
| `storage.py`                           | `backend/storage/` (local now, S3 later)|
| `EOB_PROCESSOR_DEF` (.orca.md)         | `machines/*.orca.md`                    |

## Data model (initial)

- `Document` — id, tenant/owner, doc_type, source filename, blob ref, status, timestamps.
- `ValidationRun` — id, document_id, machine_id, machine_version, status (queued/running/
  done/failed), queued_at/started_at/finished_at.
- `ValidationResult` — run_id, verdict (pass/fail/error), final_state, context (JSONB),
  reasons (JSONB list), extracted_fields (JSONB).
- `MachineSnapshot` — persisted OrcaMachine state for durable runs (mirrors revenue_cycle's
  Postgres snapshots, auto-saved on each transition).

## Co-location on the shared droplet (designed-for, not assumed)

We just watched a 600× simulator starve the shared backend's connection pool and 500 every login.
This service is built so it *cannot* do that to the builder:

- **Its own Postgres + Redis** containers — never the builder's instances.
- **Explicit `cpus` / `mem_limit`** on api and worker in `docker-compose.yml`.
- **Small, bounded worker concurrency** (OCR + LLM are the heavy bit) — a fixed worker pool, not
  unbounded task spawning.
- **DB engine carries forward the hardening**: `pool_pre_ping=True` + `pool_timeout` (fail fast
  on exhaustion rather than stall), per agent_framework's `AUTH_LOGIN_SESSION_RACE` lessons.
- `orca.cyberiad.ai` is a separate nginx vhost routing to this stack only.

Migration to a dedicated droplet later is then a lift-and-shift of an already-isolated unit.

## Key decisions & trade-offs

- **Async worker vs. synchronous request.** OCR + LLM are seconds-scale; doing them in-request
  would tie up API workers and amplify co-location risk. Decision: Redis queue + worker. The
  MVP slice may run synchronously to prove the spine, but the queue is the target shape.
- **Boot-time verification gate vs. CI-only.** CI catches it earlier, but a boot gate makes the
  guarantee enforced by code, not discipline — chosen, given verification is the product.
- **LLM structuring vs. deterministic extraction.** LLM extraction (emulating `_extract_json`)
  is flexible but slow/nondeterministic and adds an external dependency + cost. Decision: the
  extractor is an interface; MVP uses deterministic/heuristic extraction for one doc type, LLM
  is an opt-in adapter behind it.
- **Storage.** Local volume now behind a `storage/` interface; S3/Spaces adapter later. No
  premature object-store dependency.

## Repo layout

```
orca-validator/
├── docker-compose.yml          # api · worker · postgres · redis · (web) — CPU/mem LIMITED
├── Makefile                    # verify-machines · dev · test · migrate
├── package.json                # ONLY @orcalang/orca (the verifier CLI)
├── pyproject.toml
├── machines/                   # verified ORCA specs (*.orca.md)
├── backend/
│   ├── app/ (main, config, database)   # database.py: pool_pre_ping + pool_timeout
│   ├── api/ (documents, machines, health)
│   ├── ocr/ (reader, extract, result)          # ◄ eob_ocr.py
│   ├── orca/ (bridge, persistence, registry, actions/)  # ◄ orca_bridge.py
│   ├── pipeline/ (validate, worker)
│   ├── storage/ · queue.py · models/ · schemas/ · tests/
├── web/                        # OPTIONAL thin Next.js UI (deferred for MVP)
├── migrations/                 # Alembic
└── ops/ (nginx/orca.cyberiad.ai.conf, DEPLOY.md)
```

## Open questions (resolve during apply)

- **First target doc type: `contract` (resolved).** The bootstrap machine is
  `machines/contract_validation.orca.md` and the MVP extractor targets contract fields
  (parties, effective/termination dates, term, signatures, governing law, key clauses).
- Auth model: shared API key for bootstrap, or reuse agent_framework JWT? (Bootstrap: shared key.)
- Does the thin `web/` UI ship in v1 or stay deferred? (Lean: deferred, API-first.)
