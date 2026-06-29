# document-ingestion Specification (NEW)

## Purpose

Turns an uploaded business-document PDF into typed fields that a validation machine can consume.
Emulates agent_framework `revenue_cycle/sub_services/eob_ocr.py` (PyMuPDF + fallback OCR +
structuring).

## ADDED Requirements

### Requirement: PDFs are OCR'd with an embedded-text-first strategy

The service SHALL extract text from a PDF using PyMuPDF for pages with embedded text, and SHALL
fall back to image OCR (tesseract) for pages that have no embedded text. The result SHALL capture
per-page provenance (which path produced each page's text).

#### Scenario: Digital PDF uses embedded text
- **WHEN** a PDF with an embedded text layer is uploaded
- **THEN** text is taken from the embedded layer (no image OCR needed)

#### Scenario: Scanned PDF uses image OCR
- **WHEN** a PDF whose pages are images-only is uploaded
- **THEN** the tesseract fallback produces the page text

### Requirement: Extraction is an interface, and undecodable input fails loudly

Structuring extracted text into typed fields SHALL go through a pluggable extractor interface (a
deterministic extractor for the bootstrap doc type; an LLM-backed extractor is an opt-in adapter
behind the same interface). The service SHALL NOT emit a fabricated or silently-empty field set
when a document cannot be decoded or structured — it SHALL fail the run with a clear reason.

#### Scenario: Undecodable document fails the run
- **WHEN** an upload cannot be decoded into text or structured into the expected fields
- **THEN** the validation run is marked failed with a diagnostic reason
- **AND** no empty/placeholder field set is passed downstream
