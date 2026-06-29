# machine-verification Specification (NEW)

## Purpose

Guarantees that every ORCA validation machine the service runs has been formally topology-verified
first. This is the product's core promise: a document is "validated by a verified machine," not by
ad-hoc code.

## ADDED Requirements

### Requirement: Machines are topology-verified in CI

The build SHALL run the `@orcalang` verifier over every `machines/*.orca.md` file and SHALL fail
on any verification error (unreachable state, deadlock, non-deterministic guard, incompleteness,
cross-machine inconsistency). The service SHALL NOT vendor or reimplement the verifier; it invokes
the `@orcalang` CLI.

#### Scenario: A broken machine fails the build
- **WHEN** a machine contains an unreachable state or two overlapping guards on the same event
- **THEN** `make verify-machines` exits non-zero
- **AND** CI fails before any deploy

### Requirement: Unverified machines cannot run (boot gate)

At startup the service SHALL verify every registered machine and SHALL refuse to boot if any fails.
A machine's verified identity (id, version, content hash) SHALL be recorded so a run can be
attributed to an exact verified spec.

#### Scenario: Service refuses to boot on an unverified machine
- **WHEN** a registered machine fails verification at startup
- **THEN** the service does not begin serving requests
- **AND** the failure names the offending machine and reason

#### Scenario: A run is attributable to a verified spec
- **WHEN** a validation run completes
- **THEN** its result records the machine id, version, and content hash that produced it
