FROM python:3.11-slim

# System deps: nodejs/npm for the @orcalang verifier (boot gate), tesseract for image OCR.
RUN apt-get update && apt-get install -y --no-install-recommends \
        nodejs npm tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -e . \
    && npm install --omit=dev

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
