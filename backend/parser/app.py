"""Isolated document-parsing service.

Runs the untrusted-file parsers (PyMuPDF / tesseract / python-docx) in their own container
with NO secrets, NO database, and NO network egress (compose `internal` network). If a crafted
document achieves code execution here, there is nothing to steal and nowhere to exfiltrate it.

Run as: uvicorn backend.parser.app:app --host 0.0.0.0 --port 9000
"""
import os
import tempfile

from fastapi import FastAPI, File, UploadFile

from backend.ocr.reader import read_document

app = FastAPI(title="orca-parser")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/parse")
async def parse(file: UploadFile = File(...)):
    data = await file.read()
    suffix = os.path.splitext(file.filename or "")[1].lower() or ".bin"
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        r = read_document(path)
        return {"ok": r.ok, "raw_text": r.raw_text, "pages": r.pages, "error": r.error}
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
