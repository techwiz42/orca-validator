# machine Ingestion

## context
| Field | Type | Default |
|---|---|---|
| document_id | string | |

## events
- EXTRACT
- OK
- FAIL

## state received [initial]
> Upload received (PDF, image, Word, text, or pasted text); awaiting extraction.
- ignore: *

## state extracting
> Extracting text — PyMuPDF / tesseract OCR / python-docx, in the isolated parser.
- ignore: *

## state extracted [final]
> Text extracted; ready for structural validation.

## state failed [final]
> Extraction failed (unreadable, over the page limit, or empty).

## transitions
| Source | Event | Guard | Target | Action |
|---|---|---|---|---|
| received | EXTRACT | | extracting | |
| extracting | OK | | extracted | |
| extracting | FAIL | | failed | |
