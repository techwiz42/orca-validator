"""Computation-layer actions the ContractValidation machine invokes.

ORCA verifies the machine's *topology*; these action functions are the (unverified)
computation layer. Each is `async (context, payload) -> context` and returns the
(possibly updated) context. They record verdict-relevant facts; the verdict itself is
the machine's final state, not anything these functions decide.
"""
from typing import Any

Context = dict[str, Any]


async def record_extracted(context: Context, payload: Context | None) -> Context:
    """Extraction finished; fold the extracted field-presence flags into context so the
    EVALUATE guards (all_required_present / missing_required) can decide the verdict."""
    payload = payload or {}
    for key in (
        "missing_count", "has_parties", "has_effective_date",
        "has_term", "has_signatures", "has_governing_law",
    ):
        if key in payload:
            context[key] = payload[key]
    context["missing_fields"] = payload.get("missing_fields", [])
    return context


async def record_valid(context: Context, payload: Context | None) -> Context:
    context["verdict"] = "pass"
    context["reasons"] = []
    return context


async def record_invalid(context: Context, payload: Context | None) -> Context:
    context["verdict"] = "fail"
    missing = context.get("missing_fields") or (payload or {}).get("missing_fields") or []
    context["reasons"] = [f"missing required field: {m}" for m in missing] or ["required-field check failed"]
    return context


async def record_error(context: Context, payload: Context | None) -> Context:
    context["verdict"] = "error"
    context["reasons"] = [(payload or {}).get("error", "extraction or processing failed")]
    return context


def register_contract_actions(machine) -> None:
    machine.register_action("record_extracted", record_extracted)
    machine.register_action("record_valid", record_valid)
    machine.register_action("record_invalid", record_invalid)
    machine.register_action("record_error", record_error)
