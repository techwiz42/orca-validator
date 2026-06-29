## Why

ORCA gives us *formally-verified* state machines: the verifier guarantees a machine's topology is
reachable, deadlock-free, guard-deterministic, and complete before it ever runs. We already
execute ORCA machines inside agent_framework's `revenue_cycle` (EOB processing) via
`orca-runtime-python`. What does not exist yet is a standalone product that turns that capability
outward — a service that takes an arbitrary **business document** (invoice, claim, statement,
contract) and validates it against a **verified** ORCA machine, returning a trustworthy
pass/fail with reasons.

The verification *is* the value proposition. The validation rules are not ad-hoc code; they are
an ORCA machine whose control flow has been formally checked. "Validated by a verified machine"
is a materially stronger claim than "we wrote a validator," and it is the product.

## What Changes

Bootstraps a new standalone repository (`orca-validator`, served at `orca.cyberiad.ai`):

- A **document-ingestion pipeline** that accepts a PDF, OCRs it (PyMuPDF, with a tesseract
  fallback for scanned pages), and structures it into typed fields — emulating
  `revenue_cycle/sub_services/eob_ocr.py`.
- An **ORCA execution bridge** that loads, runs, and snapshots validation machines —
  emulating `revenue_cycle/orca_bridge.py` + `machine_persistence.py` over PostgreSQL.
- A **verification gate**: every `*.orca.md` machine is topology-verified by the `@orcalang`
  CLI in CI *and* re-checked at boot; an unverified machine cannot run.
- A **FastAPI surface**: submit a document, poll its validation run, fetch the verdict; browse
  the registry of verified machines (topology + Mermaid diagram).
- A **Redis-backed worker** so slow OCR/LLM work never blocks the API.
- **Resource-limited containers + its own Postgres/Redis** so the service can sit on the shared
  droplet without starving the existing builder/production workloads.

## Capabilities

### New Capabilities

- `document-ingestion` — accept a PDF, OCR it, and structure it into typed fields.
- `machine-verification` — verify ORCA machine topology as a hard build + boot gate.
- `orca-validation` — execute a verified machine over extracted fields and return a verdict.
- `validation-api` — HTTP surface for submission, status, results, and the machine registry.

## Non-goals

- **No real PHI/PII at bootstrap** — synthetic / non-sensitive business docs only. A HIPAA-style
  hardening gate (mirroring agent_framework's Track B) would precede any real sensitive data.
- **No in-app machine authoring** — machines are authored as `*.orca.md` files and verified
  offline; the service consumes them.
- **No multi-tenant billing/quotas** at bootstrap.
- **Not reimplementing the ORCA verifier** — the `@orcalang` CLI is the verifier; we wrap it.

## Impact

- New repo `~/orca-validator`; new nginx vhost `orca.cyberiad.ai` on the shared droplet.
- Co-location risk is explicit and designed-for: dedicated Postgres/Redis + CPU/memory limits
  (see `design.md`). We just watched a busy process starve a shared connection pool — this
  service is built to not repeat that.
- No change to agent_framework; this only *emulates* its `revenue_cycle` patterns.
