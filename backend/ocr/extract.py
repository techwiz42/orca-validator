"""Structure OCR text into typed fields. Pluggable extractor interface.

The bootstrap uses a deterministic contract extractor (no LLM, fully reproducible). An
LLM-backed adapter is a later milestone behind the same `Extractor` interface.
"""
import re
from typing import Protocol

from backend.ocr.result import OCRResult

# Required contract fields (drive the machine's all_required_present / missing_required guards).
CONTRACT_REQUIRED = ["parties", "effective_date", "term", "signatures", "governing_law"]


class Extractor(Protocol):
    doc_type: str

    def extract(self, result: OCRResult) -> dict: ...


class DeterministicContractExtractor:
    """Heuristic presence detection for contract fields — deterministic, no external calls."""

    doc_type = "contract"

    _PATTERNS = {
        "parties": r"\b(between|by and between|part(y|ies))\b",
        "effective_date": r"\b(effective date|effective as of|dated as of|dated)\b",
        "term": r"\b(term|duration|expir|terminat)\w*\b",
        "signatures": r"(signature|signed by|in witness whereof|/s/)",
        "governing_law": r"\b(governing law|governed by|jurisdiction|laws of)\b",
    }

    def extract(self, result: OCRResult) -> dict:
        text = (result.raw_text or "").lower()
        present = {f: bool(re.search(p, text)) for f, p in self._PATTERNS.items()}
        missing = [f for f in CONTRACT_REQUIRED if not present[f]]
        return {
            "fields": {f: present[f] for f in CONTRACT_REQUIRED},
            "missing_fields": missing,
            "missing_count": len(missing),
            "has_parties": int(present["parties"]),
            "has_effective_date": int(present["effective_date"]),
            "has_term": int(present["term"]),
            "has_signatures": int(present["signatures"]),
            "has_governing_law": int(present["governing_law"]),
        }


_EXTRACTORS = {"contract": {"deterministic": DeterministicContractExtractor}}


# Document types that should always be held to the core contract fields, regardless of which
# context-specific fields the LLM happens to pick.
_CONTRACT_LIKE = (
    "agreement", "contract", "lease", "license", "nda", "non-disclosure",
    "terms of service", "terms and conditions", "memorandum of understanding", "mou", "addendum",
)


def is_contract_like(document_type: str) -> bool:
    dt = (document_type or "").lower()
    return any(k in dt for k in _CONTRACT_LIKE)


def merge_core_contract_fields(llm_fields: dict, result: OCRResult) -> dict:
    """Hybrid field set: keep the LLM's context-aware fields, but guarantee the 5 core contract
    fields are always checked. The LLM's own assessment wins where it picked a core field; any core
    field it dropped is filled deterministically (regex presence) — so e.g. a missing signature
    block is always caught on a contract."""
    core_presence = DeterministicContractExtractor().extract(result)["fields"]
    merged = dict(llm_fields)
    for field in CONTRACT_REQUIRED:
        if field not in merged:
            merged[field] = core_presence.get(field, False)
    return merged


def get_extractor(doc_type: str, kind: str = "deterministic") -> Extractor:
    by_kind = _EXTRACTORS.get(doc_type)
    if not by_kind:
        raise ValueError(f"no extractor registered for doc_type {doc_type!r}")
    impl = by_kind.get(kind)
    if not impl:
        raise ValueError(f"unknown extractor {kind!r} for {doc_type!r} (llm adapter is a later milestone)")
    return impl()
