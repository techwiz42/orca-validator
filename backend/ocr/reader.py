"""PDF → text. Embedded-text-first (PyMuPDF), tesseract fallback for image-only pages.

Emulates revenue_cycle/sub_services/eob_ocr.py's fitz usage. Returns an OCRResult with
per-page provenance; on undecodable input it sets `error` (the caller fails the run loudly
rather than passing an empty field set downstream).
"""
import io
import logging

from backend.ocr.result import OCRResult

logger = logging.getLogger(__name__)

# below this many embedded chars, a page is treated as image-only and sent to OCR
_MIN_EMBEDDED_CHARS = 20


def read_pdf(file_path: str, dpi: int = 200) -> OCRResult:
    try:
        import fitz  # PyMuPDF
    except ImportError as e:
        return OCRResult(error=f"PyMuPDF (fitz) not available: {e}")

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        return OCRResult(error=f"could not open PDF: {e}")

    pages: list[dict] = []
    texts: list[str] = []
    try:
        for i, page in enumerate(doc):
            text = page.get_text() or ""
            method = "embedded"
            if len(text.strip()) < _MIN_EMBEDDED_CHARS:
                ocr_text = _ocr_page_image(page, dpi)
                if ocr_text is not None:
                    text, method = ocr_text, "tesseract"
            pages.append({"page": i, "method": method, "chars": len(text)})
            texts.append(text)
    finally:
        doc.close()

    raw = "\n\n".join(texts).strip()
    if not raw:
        return OCRResult(pages=pages, error="no text could be extracted (embedded or OCR)")
    return OCRResult(raw_text=raw, pages=pages)


def _ocr_page_image(page, dpi: int) -> str | None:
    """Render a page to PNG and OCR it with tesseract. None if tesseract is unavailable."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return None
    try:
        pix = page.get_pixmap(dpi=dpi)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        return pytesseract.image_to_string(img)
    except Exception as e:
        logger.warning("tesseract OCR failed for a page: %s", e)
        return None
