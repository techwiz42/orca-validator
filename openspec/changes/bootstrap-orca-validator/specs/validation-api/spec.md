# validation-api Specification (NEW)

## Purpose

The HTTP surface served at `orca.cyberiad.ai`: submit a document, track its run, fetch the verdict,
and browse the registry of verified machines. Slow work runs off-request on a bounded worker.

## ADDED Requirements

### Requirement: Submission is accepted and processed off-request

`POST /documents` SHALL accept a PDF plus a target doc type, persist it, enqueue a validation run,
and return a run identifier without performing OCR or machine execution in the request. Heavy work
SHALL run on a bounded worker pool so the API cannot be starved by ingestion load.

#### Scenario: Upload returns quickly with a run id
- **WHEN** a client POSTs a PDF
- **THEN** the response returns a run id with status `queued`
- **AND** OCR/validation happen on the worker, not in the request

### Requirement: Status and result are retrievable

`GET /documents/{id}` SHALL return the run's status; `GET /documents/{id}/result` SHALL return the
verdict, reasons, and extracted fields once complete, and SHALL indicate "not ready" (not a fake
result) while still running.

#### Scenario: Result available after completion
- **WHEN** a run has finished
- **THEN** `GET /documents/{id}/result` returns verdict + reasons + extracted fields + the
  verified machine id/version/hash that produced it

### Requirement: The verified-machine registry is browsable

`GET /machines` SHALL list the verified machines; `GET /machines/{id}` SHALL return the machine's
verified topology and a Mermaid diagram (compiled via the `@orcalang` CLI).

#### Scenario: Inspect a machine's verified topology
- **WHEN** a client GETs a machine by id
- **THEN** the response includes its states/transitions and a renderable Mermaid diagram
