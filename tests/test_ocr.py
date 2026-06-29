"""OCR + extraction (§2.4): text PDF → fields, missing-field detection, fail-loud on garbage."""
import fitz  # PyMuPDF

from backend.ocr.extract import get_extractor
from backend.ocr.reader import read_document

CONTRACT = (
    "This Agreement is made by and between Acme Corp and Beta LLC.\n"
    "Effective Date: January 1, 2026.\n"
    "Term: twelve (12) months, unless terminated earlier.\n"
    "Governing Law: the laws of the State of Delaware.\n"
    "IN WITNESS WHEREOF, the parties have signed below.\n"
)


def _make_pdf(path: str, text: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), text)
    doc.save(path)
    doc.close()


def test_text_pdf_extracts_all_contract_fields(tmp_path):
    p = tmp_path / "contract.pdf"
    _make_pdf(str(p), CONTRACT)
    r = read_document(str(p))
    assert r.ok, r.error
    assert r.pages and r.pages[0]["method"] == "embedded"
    ext = get_extractor("contract").extract(r)
    assert ext["missing_count"] == 0, ext["missing_fields"]


def test_missing_fields_are_detected(tmp_path):
    p = tmp_path / "bad.pdf"
    _make_pdf(str(p), "Some unrelated text with no contract structure whatsoever.")
    r = read_document(str(p))
    assert r.ok
    ext = get_extractor("contract").extract(r)
    assert ext["missing_count"] > 0


def test_undecodable_input_fails_loudly(tmp_path):
    p = tmp_path / "garbage.pdf"
    p.write_bytes(b"this is definitely not a pdf")
    r = read_document(str(p))
    assert not r.ok
    assert r.error  # explicit failure, never a fabricated empty field set
