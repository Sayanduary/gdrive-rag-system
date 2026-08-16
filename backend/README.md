# Backend — Google Drive RAG System

FastAPI backend service for document ingestion, OCR parsing, vector embeddings storage in ChromaDB, and Retrieval-Augmented Generation (RAG) using Ollama.

## Architecture

```text
backend/
├── app/
│   ├── api/
│   │   ├── auth.py       # Google OAuth2 login & callback
│   │   ├── drive.py      # Google Drive folder traversal & sync
│   │   ├── query.py      # Question answering RAG endpoint
│   │   └── webhook.py    # Google Drive push notifications
│   │
│   ├── services/
│   │   ├── gdrive.py     # Google Drive API v3 operations
│   │   ├── parser.py     # Document text extraction & Tesseract OCR
│   │   ├── chunker.py    # Text chunking with overlap
│   │   ├── vectorstore.py# ChromaDB & FastEmbed integration
│   │   ├── ingestion.py  # Ingestion pipeline logic
│   │   └── rag.py        # Context retrieval & Ollama LLM integration
│   │
│   └── models/
│       └── schemas.py    # Pydantic request/response models
│
├── config.py             # Environment settings
├── main.py               # FastAPI application entrypoint
├── requirements.txt      # Python dependencies
└── Dockerfile            # Container definition (Python 3.11 + Tesseract OCR)
```

## Setup & Running

### Requirements
- Python 3.11+
- Tesseract OCR (`tesseract-ocr`, `libtesseract-dev`)
- Poppler utilities (`poppler-utils`)

### Run Locally
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn main:app --reload --port 8000
```

### Run with Docker
```bash
docker build -t gdrive-rag-backend .
docker run -p 8000:8000 gdrive-rag-backend
```
