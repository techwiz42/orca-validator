# orca-validation Specification (NEW)

## Purpose

Runs a verified ORCA machine over a document's extracted fields and produces a verdict. Emulates
agent_framework `revenue_cycle/orca_bridge.py` + `machine_persistence.py` (durable, snapshotted
machine execution over PostgreSQL).

## ADDED Requirements

### Requirement: A verdict is the final state of a verified machine

The service SHALL drive the verified `OrcaMachine` for the document's type over the extracted
fields, and SHALL report the machine's final state and context as the verdict (pass / fail /
error), together with the reasons accumulated during execution. The validation rules are the
machine's transitions and guards — they SHALL NOT be duplicated as separate ad-hoc checks.

#### Scenario: A conforming document passes
- **WHEN** extracted fields satisfy the machine's guards to a pass-final-state
- **THEN** the verdict is `pass` and the reasons list is empty or informational

#### Scenario: A non-conforming document fails with reasons
- **WHEN** a guard rejects the fields (e.g., a required total is missing or inconsistent)
- **THEN** the verdict is `fail`
- **AND** the reasons name the failing rule(s)

### Requirement: Runs are durable and resumable

Machine state SHALL be snapshotted to PostgreSQL after each transition and SHALL be resumable, so
a run interrupted by a restart resumes from its persisted state rather than restarting from the
initial state.

#### Scenario: A run survives a restart
- **WHEN** the worker restarts while a run is mid-machine
- **THEN** the run resumes from its last persisted snapshot
- **AND** the document is not re-OCR'd or re-run from the beginning
