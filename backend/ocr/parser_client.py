"""Dispatch document parsing to the ISOLATED parser service when configured, else parse
in-process (dev/tests). When PARSER_URL is set, the api never parses untrusted files itself —
the dangerous parsers run in a separate container with no secrets/DB/egress.
"""
import os

import httpx

from backend.app.config import get_settings
from backend.ocr.reader import read_document
from backend.ocr.result import OCRResult


async def parse_document(blob_path: str, dpi: int = 200) -> OCRResult:
    s = get_settings()
    if not s.PARSER_URL:
        return read_document(blob_path, dpi=dpi)  # in-process fallback (dev/tests)
    try:
        with open(blob_path, "rb") as f:
            data = f.read()
        async with httpx.AsyncClient(timeout=150) as client:
            r = await client.post(
                f"{s.PARSER_URL}/parse",
                files={"file": (os.path.basename(blob_path), data)},
            )
            r.raise_for_status()
            d = r.json()
    except Exception as e:  # noqa: BLE001 — visible failure, never a fabricated empty result
        return OCRResult(error=f"parser service error: {e}")
    return OCRResult(raw_text=d.get("raw_text", ""), pages=d.get("pages") or [], error=d.get("error"))
