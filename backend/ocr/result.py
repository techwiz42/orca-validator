"""OCR result container (emulates revenue_cycle eob_ocr.OCRResult)."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OCRResult:
    raw_text: str = ""
    pages: list[dict] = field(default_factory=list)   # per-page provenance: {page, method, chars}
    fields: dict[str, Any] = field(default_factory=dict)  # structured fields (set by an extractor)
    confidence: int = 0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.raw_text.strip())
