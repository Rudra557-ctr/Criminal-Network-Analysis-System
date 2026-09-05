FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Pre-install spacy model offline-capable; fallback to regex if unavailable
RUN python -m spacy download en_core_web_sm || echo "spaCy model download failed - will use regex fallback"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
